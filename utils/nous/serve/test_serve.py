"""nous-serve spec handling and llama-speedcheck's probe and restart guards."""
import fcntl
import importlib.machinery
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def module(name):
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), str(HERE / name))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


serve = module("nous-serve")
speedcheck = module("llama-speedcheck")


@pytest.fixture
def rootfs(tmp_path):
    root = tmp_path / "engine"
    root.mkdir()
    (root / serve.SIDECAR).write_text(json.dumps({
        "image": "ghcr.io/x/vllm:1", "id": "sha256:abc", "entrypoint": ["/opt/entry.sh"],
        "env": ["PATH=/opt/vllm/bin:/usr/bin", "KNOB=image", "HOME=/nonexistent"]}))
    return root


def write_spec(tmp_path, rootfs, extra=""):
    (tmp_path / "models").mkdir(exist_ok=True)
    path = tmp_path / "spec.toml"
    path.write_text(f'rootfs = "{rootfs}"\nserved_model_name = "m"\nhome = "{tmp_path}"\n'
                    f'args = ["--model", "/models/w"]\n{extra}'
                    f'[mounts]\n"/models" = "{tmp_path / "models"}"\n[env]\nKNOB = "spec"\n')
    return path


def test_spec_env_overrides_the_image_and_mounts_precede_the_read_only_remount(tmp_path, rootfs):
    argv = serve.argv(serve.load(write_spec(tmp_path, rootfs)), port=18737)
    pairs = {argv[i + 1]: argv[i + 2] for i, a in enumerate(argv) if a == "--setenv"}
    assert pairs["KNOB"] == "spec" and pairs["HOME"] == "/root" and pairs["PATH"] == "/opt/vllm/bin:/usr/bin"
    sandbox = argv[:argv.index("--")]
    assert sandbox[-2:] == ["--remount-ro", "/"]
    assert sandbox.index("/models") < sandbox.index("--remount-ro")
    assert argv[argv.index("--") + 1:] == ["/opt/entry.sh", "--model", "/models/w", "--served-model-name", "m",
                                           "--host", "127.0.0.1", "--port", "18737"]


def test_a_json_spec_resolves_to_the_same_argv_as_its_toml(tmp_path, rootfs):
    spec = serve.load(write_spec(tmp_path, rootfs))
    as_json = tmp_path / "spec.json"
    as_json.write_text(json.dumps({**spec, "rootfs": str(spec["rootfs"]), "home": str(spec["home"])}))
    assert serve.argv(serve.load(as_json), port=1) == serve.argv(spec, port=1)


def test_unknown_spec_keys_are_rejected(tmp_path, rootfs):
    with pytest.raises(serve.SpecError, match="unknown"):
        serve.load(write_spec(tmp_path, rootfs, "unknown = 1\n"))


def test_flags_nous_serve_owns_cannot_come_from_the_spec(tmp_path, rootfs):
    path = write_spec(tmp_path, rootfs)
    path.write_text(path.read_text().replace('"/models/w"]', '"/models/w", "--port=9"]'))
    with pytest.raises(serve.SpecError, match="--port"):
        serve.load(path)


def test_a_rootfs_that_is_not_an_export_is_rejected(tmp_path, rootfs):
    (rootfs / serve.SIDECAR).unlink()
    with pytest.raises(serve.SpecError, match="not a nous-serve export"):
        serve.load(write_spec(tmp_path, rootfs))


def test_identity_changes_with_any_knob_but_not_with_the_port(tmp_path, rootfs):
    spec = serve.load(write_spec(tmp_path, rootfs))
    tuned = {**spec, "env": {**spec["env"], "KNOB": "other"}}
    assert serve.identity(spec)["argv_sha256"] != serve.identity(tuned)["argv_sha256"]
    assert serve.identity(spec)["image"] == "sha256:abc"


def test_jit_caches_go_to_the_writable_home_unless_the_spec_says_otherwise(tmp_path, rootfs):
    def env(spec):
        argv = serve.argv(spec, port=1)
        return {argv[i + 1]: argv[i + 2] for i, a in enumerate(argv) if a == "--setenv"}
    spec = serve.load(write_spec(tmp_path, rootfs))
    assert env(spec)["AITER_JIT_DIR"].startswith("/root/")
    assert env({**spec, "env": {"AITER_JIT_DIR": "/root/other"}})["AITER_JIT_DIR"] == "/root/other"


METRICS = """# HELP vllm:num_requests_running x
vllm:num_requests_running{engine="0",model_name="m"} 0.0
vllm:num_requests_waiting{engine="0",model_name="m"} 1.0
vllm:request_success_total{engine="0",finished_reason="stop",model_name="m"} 3.0
vllm:request_success_total{engine="0",finished_reason="length",model_name="m"} 2.0
vllm:request_success_created{engine="0",finished_reason="stop",model_name="m"} 1.7e+09
"""


def test_metrics_sum_across_labels_and_waiting_requests_count_as_busy():
    assert speedcheck.metric(METRICS, "vllm:request_success_total") == 5
    assert speedcheck.busy(METRICS)
    assert not speedcheck.busy(METRICS.replace("} 1.0", "} 0.0"))


IDLE = METRICS.replace("} 1.0", "} 0.0")


def test_a_probe_counts_only_if_it_was_the_one_request_and_nothing_is_left_running():
    after = IDLE.replace('"stop",model_name="m"} 3.0', '"stop",model_name="m"} 4.0')
    assert speedcheck.uncontaminated(IDLE, after)
    two_finished = after.replace("} 2.0", "} 3.0")
    assert not speedcheck.uncontaminated(IDLE, two_finished)
    started_during_probe = after.replace('running{engine="0",model_name="m"} 0.0', 'running{engine="0",model_name="m"} 1.0')
    assert not speedcheck.uncontaminated(IDLE, started_during_probe)


PROBED = {"ActiveState": "active", "UnitFileState": "enabled", "InvocationID": "a1"}


@pytest.fixture
def host(tmp_path, monkeypatch):
    """llama.service as probed, no lease, no Bonsai; records systemctl restarts."""
    state = {"llama.service": dict(PROBED), "bonsai.service": {"ActiveState": "inactive"}, "leases": [], "calls": []}
    monkeypatch.setattr(speedcheck, "LEASE_LOCK", str(tmp_path / "lease.lock"))
    monkeypatch.setattr(speedcheck, "STATE", tmp_path / "state" / "restarts.json")
    monkeypatch.setattr(speedcheck, "unit", lambda name: state[name])
    monkeypatch.setattr(speedcheck, "leases", lambda: state["leases"])
    monkeypatch.setattr(speedcheck.subprocess, "run", lambda argv, check: state["calls"].append(argv))
    return state


def test_a_restart_targets_the_probed_invocation_and_is_recorded(host):
    assert speedcheck.restart(PROBED, "slow") == 0
    assert host["calls"] == [["systemctl", "--no-block", "try-restart", "llama.service"]]
    assert len(json.loads(speedcheck.STATE.read_text())) == 1


@pytest.mark.parametrize("change", [
    lambda h: h["llama.service"].update(InvocationID="b2"),
    lambda h: h["llama.service"].update(UnitFileState="disabled"),
    lambda h: h["leases"].append("llama-yield-gpu.service"),
    lambda h: h["bonsai.service"].update(ActiveState="activating"),
], ids=["restarted-meanwhile", "intentionally-stopped", "lease-without-caller", "bonsai"])
def test_no_restart_when_production_changed_or_the_gpu_is_claimed(host, change):
    change(host)
    assert speedcheck.restart(PROBED, "slow") == 0
    assert host["calls"] == [] and not speedcheck.STATE.exists()


def test_no_restart_while_a_lease_caller_holds_the_lock(host):
    with open(speedcheck.LEASE_LOCK, "w") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        assert speedcheck.restart(PROBED, "slow") == 0
    assert host["calls"] == []


def test_the_hourly_budget_survives_across_runs(host):
    assert speedcheck.restart(PROBED, "slow") == 0
    assert speedcheck.restart(PROBED, "slow") == 0
    assert speedcheck.restart(PROBED, "slow") == 1
    assert len(host["calls"]) == 2


def test_an_unreadable_budget_refuses_restarts_instead_of_resetting(host):
    speedcheck.STATE.parent.mkdir()
    speedcheck.STATE.write_text("[1.0, ")
    assert speedcheck.restart(PROBED, "slow") == 1
    assert host["calls"] == [] and speedcheck.STATE.read_text() == "[1.0, "
