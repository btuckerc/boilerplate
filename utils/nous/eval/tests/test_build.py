import pytest

from nevl import build
from nevl.compare import compare, write
from nevl.runner import execute


@pytest.fixture
def compared(make_run, fake_workload, fake_server, monkeypatch):
    """Runs of incumbent vs cand; production is the incumbent they measured."""
    def make(oks, tier="tx"):
        fake_workload.oks = oks
        run = make_run(labels=("incumbent", "cand"))
        plan = run.plan
        plan["tier"] = tier
        run.write_json("plan.json", plan)
        execute(run)
        write(run, compare(run))
        monkeypatch.setattr(build, "production_identity",
                            lambda: build._identity(run.read_json("manifest.incumbent.json")))
        monkeypatch.setattr(build, "manifest", lambda c: {"label": c["label"]})  # as recorded by the fake runner
        return run
    return make


def test_promote_requires_a_same_session_compare(compared, capsys):
    """Vendor numbers or another day's run are not evidence (ledger M19)."""
    run = compared({"incumbent": 1.0, "cand": 1.0}, tier="t2")
    assert build.promote("other", [run.run_id]) == 1
    assert "no compare" in capsys.readouterr().out


def test_promote_refuses_failing_evidence(compared, capsys):
    run = compared({"incumbent": 1.0, "cand": 0.2}, tier="t2")
    assert build.promote("cand", [run.run_id]) == 1
    assert "verdict fail" in capsys.readouterr().out


def test_promote_needs_speed_and_accuracy_evidence(compared, capsys):
    """A speed tier alone let accuracy regressions through (ledger M11, council S-02)."""
    run = compared({"incumbent": 1.0, "cand": 1.0}, tier="t2")
    assert build.promote("cand", [run.run_id]) == 1
    assert "t3 (accuracy)" in capsys.readouterr().out


def test_promote_refuses_a_workload_subset(compared, capsys):
    run = compared({"incumbent": 1.0, "cand": 1.0}, tier="t2")
    plan = run.plan
    plan["tier_workloads"] = ["fake", "longctx"]
    run.write_json("plan.json", plan)
    assert build.promote("cand", [run.run_id]) == 1
    assert "measured ['fake'] of tier t2" in capsys.readouterr().out


def test_promote_refuses_evidence_against_an_older_production(compared, capsys, monkeypatch):
    run = compared({"incumbent": 1.0, "cand": 1.0}, tier="t2")
    monkeypatch.setattr(build, "production_identity", lambda: {"engine_sha256": "promoted since"})
    assert build.promote("cand", [run.run_id]) == 1
    assert "production has changed" in capsys.readouterr().out


def test_promote_does_not_automate_engine_changes(compared, capsys):
    runs = [compared({"incumbent": 1.0, "cand": 1.0}, tier=tier).run_id for tier in ("t2", "t3")]
    assert build.promote("cand", runs) == 1
    assert "cannot be promoted" in capsys.readouterr().out


def test_promote_refuses_a_candidate_rebuilt_after_it_was_measured(compared, capsys):
    """Same path, new bytes: the evidence is about a binary that no longer exists (council S-08)."""
    runs = [compared({"incumbent": 1.0, "cand": 1.0}, tier=tier) for tier in ("t2", "t3")]
    runs[1].write_json("manifest.cand.json", {"label": "cand", "engine_sha256": "rebuilt"})
    assert build.promote("cand", [r.run_id for r in runs]) == 1
    assert "differs between the runs" in capsys.readouterr().out


def test_an_edited_patch_is_a_different_build(tmp_path):
    patch = tmp_path / "fix.patch"
    patch.write_text("one")
    first = build.build_name("a" * 40, "vulkan", patch)
    patch.write_text("two")
    assert build.build_name("a" * 40, "vulkan", patch) != first


def test_build_unit_uses_the_unit_path(monkeypatch):
    seen = []
    monkeypatch.setattr(build.subprocess, "run", lambda argv, check: seen.append(argv))
    build.build_in_unit("origin/master", "vulkan", None)
    argv = seen[0]
    assert argv[:2] == ["systemd-run", "--user"]
    assert argv[argv.index("-E") + 1] == f"PATH={build.UNIT_PATH}"
    assert argv[-3:] == ["--backend", "vulkan", "--here"]


def test_latest_radiance_release_derives_documented_image_tag():
    payload = {"tag_name": "v1.9.1",
               "body": "Published image `ghcr.io/slybase/vllm-sly-radiance:1.9.1-rocm10.1`."}
    assert build.latest_radiance_release(payload) == {
        "version": "1.9.1", "image_tag": "1.9.1-rocm10.1",
        "image_ref": "ghcr.io/slybase/vllm-sly-radiance:1.9.1-rocm10.1"}
