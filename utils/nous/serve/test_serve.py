"""nous-serve spec handling and llama-speedcheck's probe and restart guards."""
import fcntl
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def module(name):
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), str(HERE / name))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def ran(argv):
    return subprocess.CompletedProcess(argv, 0, "", "")


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


def test_spec_args_replace_the_image_cmd_as_docker_run_does():
    assert serve.command({"Entrypoint": ["radiance"], "Cmd": ["--help"]}) == ["radiance"]
    assert serve.command({"Entrypoint": None, "Cmd": ["vllm", "serve"]}) == ["vllm", "serve"]


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


def test_run_records_the_spec_it_loaded_and_never_a_stale_one(tmp_path, rootfs, monkeypatch):
    """llama-speedcheck and nous-eval judge production by this record (ledger M60): it must be
    the bytes this run loaded, and a run that cannot start must not leave the last one behind."""
    spec = write_spec(tmp_path, rootfs)
    record = tmp_path / "run" / "serve.toml"
    record.parent.mkdir()
    monkeypatch.setattr(serve, "run", lambda cmd: 0)
    argv = ["run", str(spec), "--port", "8080", "--record", str(record)]
    assert serve.main(argv) == 0
    assert record.read_bytes() == spec.read_bytes()
    spec.write_text('rootfs = "/elsewhere"\n')
    assert serve.main(argv) == 2 and not record.exists()


ENGINE = """trap 'echo draining >> "$LOG"; sleep 1; echo drained >> "$LOG"; exit 0' TERM
echo up >> "$LOG"
while true; do sleep 0.1 & wait $!; done
"""
RUN = """import importlib.machinery, importlib.util, sys
loader = importlib.machinery.SourceFileLoader("nous_serve", sys.argv[1])
spec = importlib.util.spec_from_loader(loader.name, loader)
mod = importlib.util.module_from_spec(spec)
loader.exec_module(mod)
sys.exit(mod.run(sys.argv[2:]))
"""


@pytest.mark.skipif(not Path("/usr/bin/bwrap").exists(), reason="needs bubblewrap")
def test_sigterm_lets_the_engine_in_the_sandbox_drain(tmp_path):
    """Signalled directly, bwrap dies and --die-with-parent kills the sandbox within
    milliseconds: vLLM never drained, so every restart cut in-flight replies (ledger M57)."""
    import signal
    import subprocess
    import sys
    log = tmp_path / "log"
    (tmp_path / "engine.sh").write_text(ENGINE)
    sandbox = ["/usr/bin/bwrap", "--unshare-user", "--uid", "0", "--gid", "0", "--unshare-pid",
               "--die-with-parent", "--ro-bind", "/", "/", "--bind", str(tmp_path), str(tmp_path),
               "--dev", "/dev", "--proc", "/proc", "--setenv", "LOG", str(log),
               "--", "/bin/bash", str(tmp_path / "engine.sh")]
    proc = subprocess.Popen([sys.executable, "-c", RUN, str(HERE / "nous-serve"), *sandbox])
    deadline = time.monotonic() + 10
    while not (log.exists() and "up" in log.read_text()) and time.monotonic() < deadline:
        time.sleep(0.05)
    proc.send_signal(signal.SIGTERM)
    assert proc.wait(timeout=10) == 0
    assert log.read_text().split() == ["up", "draining", "drained"]


def test_a_stop_while_the_sandbox_starts_still_reaches_it(monkeypatch):
    """A SIGTERM before the child exists used to kill nous-serve outright; it is held and
    handed to the sandbox once it exists (council F-12)."""
    import signal
    sent = []

    class Child:
        pid = 4242

        def wait(self):
            return -signal.SIGTERM if sent else 0

    def popen(cmd):
        signal.raise_signal(signal.SIGTERM)
        return Child()

    previous = {s: signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGINT)}
    monkeypatch.setattr(serve.subprocess, "Popen", popen)
    monkeypatch.setattr(serve, "engine_pid", lambda pid: None)
    monkeypatch.setattr(serve.os, "kill", lambda pid, signum: sent.append((pid, signum)))
    try:
        assert serve.run(["sandbox"]) == 143
    finally:
        for s, handler in previous.items():
            signal.signal(s, handler)
    assert sent == [(4242, signal.SIGTERM)]


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


def test_restart_skips_when_metrics_turn_busy_under_lock(host, monkeypatch, capsys):
    monkeypatch.setattr(speedcheck, "get", lambda path: METRICS)
    assert speedcheck.restart(PROBED, "slow state", "live") == 0
    assert "production busy" in capsys.readouterr().out
    assert host["calls"] == [] and not speedcheck.STATE.exists()


def test_a_request_that_starts_while_the_budget_is_written_stops_a_slow_restart(host, monkeypatch):
    """The last guard pass reads metrics again (release audit: it had kept the idle sample from
    before the budget's fsyncs). The written slot stays spent."""
    monkeypatch.setattr(speedcheck, "running_spec_sha256", lambda: "live")
    state = {"metrics": IDLE}
    monkeypatch.setattr(speedcheck, "get", lambda path: state["metrics"])
    publish = speedcheck.publish
    monkeypatch.setattr(speedcheck, "publish", lambda path, value: (publish(path, value), state.update(metrics=METRICS)))
    assert speedcheck.restart(PROBED, "slow", "live") == 0
    assert host["calls"] == [] and speedcheck.STATE.exists()


def run_slow_main(monkeypatch, tmp_path, digest, running="live"):
    monkeypatch.setattr(speedcheck, "unit", lambda name: {"ActiveState": "inactive"} if name == "bonsai.service" else {
        "ActiveState": "active", "UnitFileState": "enabled", "InvocationID": "a1",
        "ActiveEnterTimestampMonotonic": "0"})
    monkeypatch.setattr(speedcheck.time, "clock_gettime", lambda _: 1000)
    monkeypatch.setattr(speedcheck, "SETTLE_S", 1)
    monkeypatch.setattr(speedcheck, "get", lambda path: IDLE)
    monkeypatch.setattr(speedcheck, "SPEC", tmp_path / "spec.toml")
    monkeypatch.setattr(speedcheck, "RECORD", tmp_path / "record.toml")
    speedcheck.SPEC.write_text('served_model_name = "m"\n')
    speedcheck.RECORD.write_text('served_model_name = "m"\n')
    if running is not None:
        monkeypatch.setattr(speedcheck, "running_spec_sha256", lambda: running)
    monkeypatch.setattr(speedcheck, "CALIBRATION", tmp_path / "calibration.json")
    monkeypatch.setattr(speedcheck, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(speedcheck, "LEASE_LOCK", str(tmp_path / "lock"))
    monkeypatch.setattr(speedcheck, "leases", lambda: [])
    monkeypatch.setattr(speedcheck, "probe", lambda _: 10)
    calls = []
    monkeypatch.setattr(speedcheck.subprocess, "run", lambda argv, **kw: calls.append(argv) or ran(argv))
    speedcheck.CALIBRATION.write_text(json.dumps({"spec_sha256": digest, "slow_below_tps": 20}))
    return calls


def test_slow_restart_threshold_invalidated_when_spec_changes(tmp_path, monkeypatch, capsys):
    calls = run_slow_main(monkeypatch, tmp_path, "old")
    monkeypatch.setattr(speedcheck.sys, "argv", ["llama-speedcheck"])
    assert speedcheck.main() == 0
    assert calls == [] and "uncalibrated" in capsys.readouterr().out


def test_matching_calibration_sha_allows_slow_restart(tmp_path, monkeypatch):
    calls = run_slow_main(monkeypatch, tmp_path, "live")
    monkeypatch.setattr(speedcheck.sys, "argv", ["llama-speedcheck"])
    assert speedcheck.main() == 0
    assert calls == [["systemctl", "--no-block", "try-restart", "llama.service"]]


def test_slow_restarts_follow_the_spec_the_running_invocation_loaded(tmp_path, monkeypatch, capsys):
    """Calibrated for the file in /etc while the process had loaded another one (installed
    without a restart, by `cp -p`, through a symlink): inferring that from ctimes and clocks
    failed four ways (release audits; ledger M60). The record nous-serve left decides."""
    calls = run_slow_main(monkeypatch, tmp_path, "", running=None)
    digest = hashlib.sha256(speedcheck.SPEC.read_bytes()).hexdigest()
    speedcheck.CALIBRATION.write_text(json.dumps({"spec_sha256": digest, "slow_below_tps": 20}))
    monkeypatch.setattr(speedcheck.sys, "argv", ["llama-speedcheck"])
    speedcheck.RECORD.write_text('served_model_name = "older"\n')
    assert speedcheck.main() == 0
    assert calls == [] and "uncalibrated" in capsys.readouterr().out
    speedcheck.RECORD.unlink()  # stopped: no invocation, no record
    assert speedcheck.main() == 0
    assert calls == [] and "uncalibrated" in capsys.readouterr().out
    speedcheck.RECORD.write_bytes(speedcheck.SPEC.read_bytes())  # restarted: it loaded this spec
    assert speedcheck.main() == 0
    assert calls == [["systemctl", "--no-block", "try-restart", "llama.service"]]


def test_a_spec_changed_under_the_lock_skips_the_slow_restart(host, monkeypatch, capsys):
    monkeypatch.setattr(speedcheck, "get", lambda path: IDLE)
    monkeypatch.setattr(speedcheck, "running_spec_sha256", lambda: "new")
    assert speedcheck.restart(PROBED, "slow state", "live") == 0
    assert host["calls"] == [] and "changed" in capsys.readouterr().out


@pytest.mark.parametrize("failures, restarted", [(3, False), (4, True)])
def test_health_restarts_only_after_a_minute_of_failures(tmp_path, monkeypatch, failures, restarted):
    calls = run_slow_main(monkeypatch, tmp_path, "live")
    left = [failures]

    def get(path):
        if path == "/health" and left[0]:
            left[0] -= 1
            raise OSError("timed out")
        return IDLE

    monkeypatch.setattr(speedcheck, "get", get)
    monkeypatch.setattr(speedcheck, "probe", lambda _: 100)  # healthy speed
    monkeypatch.setattr(speedcheck.time, "sleep", lambda s: None)
    monkeypatch.setattr(speedcheck.sys, "argv", ["llama-speedcheck"])
    assert speedcheck.main() == 0
    assert bool(calls) == restarted


def test_calibrate_uses_six_clean_probe_results_and_atomic_replace(tmp_path, monkeypatch):
    monkeypatch.setattr(speedcheck.os, "geteuid", lambda: 0)
    monkeypatch.setattr(speedcheck, "unit", lambda _: {"ActiveState": "active", "ActiveEnterTimestampMonotonic": "0"})
    monkeypatch.setattr(speedcheck, "SETTLE_S", 1)
    monkeypatch.setattr(speedcheck.time, "clock_gettime", lambda _: 1000)
    monkeypatch.setattr(speedcheck, "get", lambda _: IDLE)
    monkeypatch.setattr(speedcheck, "SPEC", tmp_path / "spec.toml")
    monkeypatch.setattr(speedcheck, "RECORD", speedcheck.SPEC)
    speedcheck.SPEC.write_text('served_model_name = "m"\n')
    monkeypatch.setattr(speedcheck, "running_spec_sha256", lambda: "live")
    monkeypatch.setattr(speedcheck, "CALIBRATION", tmp_path / "calibration.json")
    values = iter([None, 100, 110, 120, 130, 140, 150])
    monkeypatch.setattr(speedcheck, "probe", lambda _: next(values))
    replaced = []
    replace = speedcheck.os.replace
    monkeypatch.setattr(speedcheck.os, "replace", lambda src, dst: (replaced.append((src, dst)), replace(src, dst)))
    monkeypatch.setattr(speedcheck.sys, "argv", ["llama-speedcheck", "--calibrate"])
    assert speedcheck.main() == 0
    result = json.loads(speedcheck.CALIBRATION.read_text())
    assert result["probes"] == [100, 110, 120, 130, 140, 150]
    assert result["slow_below_tps"] == round(0.89 * 125)
    assert result["spec_sha256"] == "live" and len(replaced) == 1


def test_calibration_measured_across_a_spec_change_is_not_written(tmp_path, monkeypatch):
    """Spec B installed during the probes of spec A: the probes measured A (release audit)."""
    monkeypatch.setattr(speedcheck.os, "geteuid", lambda: 0)
    monkeypatch.setattr(speedcheck, "unit", lambda _: {"ActiveState": "active", "ActiveEnterTimestampMonotonic": "0",
                                                       "InvocationID": "a1"})
    monkeypatch.setattr(speedcheck, "SETTLE_S", 1)
    monkeypatch.setattr(speedcheck.time, "clock_gettime", lambda _: 1000)
    monkeypatch.setattr(speedcheck, "get", lambda _: IDLE)
    monkeypatch.setattr(speedcheck, "SPEC", tmp_path / "spec.toml")
    monkeypatch.setattr(speedcheck, "RECORD", speedcheck.SPEC)
    speedcheck.SPEC.write_text('served_model_name = "m"\n')
    hashes = iter(["A", "B"])
    monkeypatch.setattr(speedcheck, "running_spec_sha256", lambda: next(hashes))
    monkeypatch.setattr(speedcheck, "CALIBRATION", tmp_path / "calibration.json")
    monkeypatch.setattr(speedcheck, "probe", lambda _: 140)
    monkeypatch.setattr(speedcheck.sys, "argv", ["llama-speedcheck", "--calibrate"])
    assert speedcheck.main() == 1
    assert not speedcheck.CALIBRATION.exists()


PROBED = {"ActiveState": "active", "UnitFileState": "enabled", "InvocationID": "a1"}


@pytest.fixture
def host(tmp_path, monkeypatch):
    """llama.service as probed, no lease, no Bonsai; records systemctl restarts."""
    state = {"llama.service": dict(PROBED), "bonsai.service": {"ActiveState": "inactive"}, "leases": [], "calls": []}
    monkeypatch.setattr(speedcheck, "LEASE_LOCK", str(tmp_path / "lease.lock"))
    monkeypatch.setattr(speedcheck, "STATE", tmp_path / "state" / "restarts.json")
    monkeypatch.setattr(speedcheck, "unit", lambda name: state[name])
    monkeypatch.setattr(speedcheck, "leases", lambda: state["leases"])
    monkeypatch.setattr(speedcheck.subprocess, "run", lambda argv, **kw: state["calls"].append(argv) or ran(argv))
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
@pytest.mark.parametrize("when", ["before", "while-metrics-waited", "while-the-budget-was-written"])
def test_no_restart_when_production_changed_or_the_gpu_is_claimed(host, monkeypatch, change, when):
    """A change during either blocking step (the slow-state metrics request, the budget's fsyncs)
    counts too (release audits: the guards had used a state from before it)."""
    monkeypatch.setattr(speedcheck, "running_spec_sha256", lambda: "live")
    if when == "while-metrics-waited":
        monkeypatch.setattr(speedcheck, "get", lambda path: change(host) or IDLE)
    elif when == "while-the-budget-was-written":
        monkeypatch.setattr(speedcheck, "get", lambda path: IDLE)
        publish = speedcheck.publish
        monkeypatch.setattr(speedcheck, "publish", lambda path, value: (publish(path, value), change(host)))
    else:
        change(host)
    assert speedcheck.restart(PROBED, "slow", None if when == "before" else "live") == 0
    assert host["calls"] == []
    assert speedcheck.STATE.exists() == (when == "while-the-budget-was-written")  # a written slot stays spent


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
