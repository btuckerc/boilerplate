import json
import pytest
from pathlib import Path

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


@pytest.mark.parametrize("failed, refused", [(["final-cactus05"], False), (["cand"], True), (None, True)])
def test_promote_judges_a_run_by_its_two_arms(compared, capsys, failed, refused):
    """A crashed third arm (t3's Cactus arm) voided the incumbent-vs-candidate evidence of the
    whole run (council A-07, O-16); a failure of either compared arm, or an unlabelled one, still does."""
    runs = [compared({"incumbent": 1.0, "cand": 1.0}, tier=tier) for tier in ("t2", "t3")]
    runs[1].finish("failed", **({} if failed is None else {"failed_labels": failed}))
    write(runs[1], compare(runs[1], "incumbent", "cand"))  # a report of the run as it now stands
    assert build.promote("cand", [r.run_id for r in runs]) == 1
    out = capsys.readouterr().out
    assert ("did not finish ok" in out) == refused and ("cannot be promoted" in out) != refused


def test_promote_refuses_a_compare_older_than_the_rows(compared, capsys):
    """A resume measured rows again after the passing report was written, and power was lost
    before the new compare: the old pass stood as evidence (release audit, M61)."""
    runs = [compared({"incumbent": 1.0, "cand": 1.0}, tier=tier) for tier in ("t2", "t3")]
    runs[1].append({**runs[1].rows()[0], "ts": 0.0})
    assert build.promote("cand", [r.run_id for r in runs]) == 1
    assert "predates the run's current rows" in capsys.readouterr().out


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


def test_promote_rejects_inconclusive_t3_but_accepts_pass(compared, capsys):
    t2 = compared({"incumbent": 1.0, "cand": 1.0}, tier="t2")
    t3 = compared({"incumbent": 1.0, "cand": 1.0}, tier="t3")
    path = t3.path / "compare.incumbent.cand.json"
    report = t3.read_json(path.name)
    report["verdict"] = "inconclusive"
    t3.write_json(path.name, report)
    assert build.promote("cand", [t2.run_id, t3.run_id]) == 1
    assert "verdict inconclusive" in capsys.readouterr().out
    report["verdict"] = "pass"
    t3.write_json(path.name, report)
    assert build.promote("cand", [t2.run_id, t3.run_id]) == 1
    assert "cannot be promoted" in capsys.readouterr().out


def test_unstable_canary_retries_once_then_becomes_terminal(make_run, monkeypatch, tmp_path, capsys):
    from conftest import TIERS, command_candidate
    label = "radiance-retry"
    monkeypatch.setattr(build, "latest_radiance_release", lambda: {
        "version": "retry", "image_tag": "retry", "image_ref": "image:retry"})
    monkeypatch.setattr(build, "incumbent", lambda: {
        **command_candidate("incumbent"), "spec_source": "/spec.toml", "spec": spec("/old-radiance")})
    monkeypatch.setattr(build, "CANARY_HOME_ROOT", tmp_path / "cache")
    monkeypatch.setattr(build.subprocess, "run", lambda *a, **k: type("R", (), {"stdout": "/new\n"}))
    monkeypatch.setattr(build, "load", lambda path: command_candidate(label))
    made = []

    def plan(tier, candidates):
        assert tier == "canary"
        from nevl.runner import plan_run
        result = plan_run("tx", candidates, lease=False, port=18850, tiers=TIERS)
        result["run_id"] += f"-{len(made) + 1}"
        made.append(result["run_id"])
        return result

    monkeypatch.setattr(build, "plan_run", plan)
    monkeypatch.setattr(build, "start", lambda run, **kw: (run.finish("ok") or 0))
    calls = []
    monkeypatch.setattr(build, "compare", lambda *a: (calls.append(1) or
                        {"verdict": "inconclusive", "unstable": ["fake"]}))
    monkeypatch.setattr(build, "write", lambda *a: "unstable")
    assert build.canary() == 1
    record = tmp_path / "canary" / f"{label}.json"
    first = json.loads(record.read_text())
    assert not first.get("terminal") and first["attempts"] == 1
    assert build.canary() == 1
    second = json.loads(record.read_text())
    assert second["terminal"] and second["attempts"] == 2
    assert "inconclusive after 2 attempts" in capsys.readouterr().out
    assert len(calls) == 2


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


LABEL = "radiance-9.9"


def spec(rootfs: str) -> dict:
    return {"rootfs": rootfs, "served_model_name": "m", "home": "/h", "args": [], "env": {}, "mounts": {}}


@pytest.fixture
def release(monkeypatch, tmp_path):
    """A new radiance release over a command-candidate production; returns the planned run ids."""
    from conftest import TIERS, command_candidate
    from nevl.runner import plan_run
    monkeypatch.setattr(build, "latest_radiance_release", lambda: {
        "version": "9.9", "image_tag": "9.9-rocm", "image_ref": "ghcr.io/x/radiance:9.9-rocm"})
    monkeypatch.setattr(build, "incumbent", lambda: {**command_candidate("incumbent"), "spec_source": "/spec.toml",
                                                     "spec": spec("/engines/vllm-sly-radiance-1.0")})
    monkeypatch.setattr(build, "CANARY_HOME_ROOT", tmp_path / "cache")
    monkeypatch.setattr(build.subprocess, "run", lambda *a, **k: type("R", (), {"stdout": "/engines/new\n"}))
    monkeypatch.setattr(build, "load", lambda path: command_candidate(LABEL))
    planned = []

    def plan(tier, candidates):
        result = plan_run("tx", candidates, lease=False, port=18850, tiers=TIERS)
        result["run_id"] += f"-{len(planned)}-{tier}"
        planned.append(result["run_id"])
        return result
    monkeypatch.setattr(build, "plan_run", plan)
    monkeypatch.setattr(build, "start", lambda run, **kw: execute(run))
    return planned


def canary_record(tmp_path) -> dict:
    return json.loads((tmp_path / "canary" / f"{LABEL}.json").read_text())


@pytest.mark.parametrize("cand_ok, tiers_run, verdict", [(1.0, ["canary", "t3"], "pass"),
                                                          (0.2, ["canary", "canary"], "fail")])
def test_a_new_release_gets_t3_only_after_its_canary_passes(release, fake_workload, fake_server, tmp_path,
                                                            cand_ok, tiers_run, verdict):
    """A canary that does not pass is measured once more (ROCm's slow draw, council O-05), then terminal."""
    fake_workload.oks = {"incumbent": 1.0, LABEL: cand_ok}
    for _ in range(3):
        build.canary()
    assert [run_id.rsplit("-", 1)[1] for run_id in release] == tiers_run
    record = canary_record(tmp_path)
    assert record["terminal"] and record["verdict"] == verdict


def test_a_canary_resumes_after_a_power_loss_took_its_cache_home(release, fake_workload, monkeypatch, tmp_path):
    """The record survived but the new home directory did not; bwrap's --bind then failed on every
    later attempt (release audit, M61)."""
    monkeypatch.setattr(build, "start", lambda run, **kw: 1)  # the lease is cut
    build.canary()
    home = Path(canary_record(tmp_path)["home"])
    home.rmdir()
    build.canary()
    assert home.is_dir()


def test_a_canary_record_from_before_resumable_canaries_continues(release, fake_workload, monkeypatch, tmp_path):
    """Such a record has no home and no attempts, and its candidate used production's home
    (release audit: the upgrade raised KeyError on every timer run)."""
    candidate = tmp_path / "canary" / "candidates" / f"{LABEL}.toml"
    candidate.parent.mkdir(parents=True)
    candidate.write_text(f'kind = "serve"\nlabel = "{LABEL}"\nspec = "/spec.toml"\n\n[overrides]\nrootfs = "/x"\n')
    (tmp_path / "canary" / f"{LABEL}.json").write_text(json.dumps(
        {"image_ref": "ghcr.io/x/radiance:9.9-rocm", "run_id": None, "t3_run_id": None, "verdict": "pass",
         "candidate": str(candidate)}))
    monkeypatch.setattr(build, "start", lambda run, **kw: 1)  # the lease is cut
    assert build.canary() == 1
    assert canary_record(tmp_path)["run_id"] == release[0] and canary_record(tmp_path)["attempts"] == 1


def test_a_canary_run_from_before_resumable_canaries_is_its_first_attempt(release, fake_workload, fake_server,
                                                                          monkeypatch, tmp_path):
    """Such a record has a run but no attempt count; counting none bought a failing canary a
    third measurement (release audit, M61)."""
    fake_workload.oks = {"incumbent": 1.0, LABEL: 0.2}
    start = build.start
    monkeypatch.setattr(build, "start", lambda run, **kw: 1)  # the lease is cut
    build.canary()
    record = tmp_path / "canary" / f"{LABEL}.json"
    legacy = {key: value for key, value in canary_record(tmp_path).items() if key not in ("attempts", "home")}
    record.write_text(json.dumps(legacy))
    monkeypatch.setattr(build, "start", start)
    build.canary()
    build.canary()
    assert canary_record(tmp_path)["terminal"] and len(release) == 2


def test_a_canary_that_cannot_start_is_reported_as_stuck(release, fake_workload, fake_server, monkeypatch, tmp_path):
    """A failing preflight (an unbooted kernel) left no rows and no verdict: the watch saw nothing (council O-14)."""
    from nevl import watch
    fake_workload.oks = {"incumbent": 1.0, LABEL: 1.0}
    monkeypatch.setattr(build, "start", lambda run, **kw: 1)
    assert build.canary() == 1
    snapshot = {"github": {watch.RADIANCE_REPO: {"tag": "v9.9"}}, "canary": {"9.9": canary_record(tmp_path)}}
    items, _ = watch.findings({}, snapshot, {"hf": {}, "github": {watch.RADIANCE_REPO: "v9.9"}, "docker": {}})
    assert [item["kind"] for item in items] == ["status", "open"] and release[0] in items[1]["text"]
    monkeypatch.setattr(build, "start", lambda run, **kw: execute(run))
    assert build.canary() == 0
    assert canary_record(tmp_path)["blocked"] is None and len(release) == 2


def test_a_canary_cut_after_its_lease_is_graded_not_measured_again(release, fake_workload, fake_server,
                                                                    monkeypatch, tmp_path):
    """A reboot between a run's done.json and its grading: the next timer run grades it and goes
    on to t3; recovery skips finished runs, so nothing else would (release audit)."""
    fake_workload.oks = {"incumbent": 1.0, LABEL: 1.0}

    def reboot(*args):
        raise RuntimeError("power loss")

    monkeypatch.setattr(build, "compare", reboot)
    with pytest.raises(RuntimeError):
        build.canary()
    canary_run = release[0]
    graded = []
    from nevl import runner
    monkeypatch.setattr(build, "compare", compare)
    monkeypatch.setattr(runner, "grade", lambda run: graded.append(run.run_id) or 0)
    monkeypatch.setattr(runner, "_start", lambda run, max_leases: pytest.fail("measured a finished run again"))
    monkeypatch.setattr(build, "start", lambda run, **kw: (runner.start(run, **kw) if run.run_id == canary_run
                                                         else execute(run)))
    assert build.canary() == 0
    assert graded == [canary_run] and len(release) == 2


def test_the_canary_leaves_a_stopped_run_stopped(release, fake_workload, fake_server, monkeypatch, tmp_path):
    """Stopped by hand (nous-eval writes stopped.json): the next timer run must not resume it,
    only `nous-eval resume` does (release audit, M61)."""
    from nevl import runner, store
    fake_workload.oks = {"incumbent": 1.0, LABEL: 1.0}
    monkeypatch.setattr(build, "start", lambda run, **kw: 1)  # the lease is cut
    build.canary()
    run = store.Run.open(release[0])
    run.write_json("stopped.json", {"run_id": run.run_id})
    monkeypatch.setattr(build, "start", runner.start)
    assert build.canary() == 1
    assert not run.done() and (run.path / "stopped.json").exists()
    assert "was stopped" in canary_record(tmp_path)["blocked"]
    assert runner.start(run) == 0  # nous-eval resume
    assert build.canary() == 0 and len(release) == 2


def test_the_canary_does_not_go_on_from_a_finished_run_that_was_stopped(release, fake_workload, fake_server,
                                                                         monkeypatch, tmp_path):
    """The canary run finished in its lease, then its client was stopped (while production came
    back, or while grading) and marked it: the next timer run must not compare it and go on to
    t3; only `nous-eval resume` does (release audit, M61)."""
    from nevl import runner, store
    fake_workload.oks = {"incumbent": 1.0, LABEL: 1.0}

    def stopped_while_grading(*args):
        raise SystemExit(143)

    monkeypatch.setattr(build, "start", lambda run, **kw: execute(run))
    monkeypatch.setattr(build, "compare", stopped_while_grading)
    with pytest.raises(SystemExit):
        build.canary()
    run = store.Run.open(release[0])
    run.write_json("stopped.json", {"run_id": run.run_id})
    assert run.done()
    monkeypatch.setattr(build, "compare", compare)
    monkeypatch.setattr(build, "start", runner.start)
    assert build.canary() == 1
    assert "was stopped" in canary_record(tmp_path)["blocked"] and len(release) == 1
    assert runner.start(run) == 0  # nous-eval resume
    assert build.canary() == 0 and len(release) == 2


def test_rollback_never_archives_over_its_source(tmp_path, monkeypatch, capsys):
    """The newest differing archive is from this very second (or the clock went back): the live
    spec's archive must get a later name, not overwrite the spec being restored (release audit)."""
    (tmp_path / "history").mkdir()
    source = tmp_path / "history/serve-20990101T000000Z.toml"
    source.write_text('rootfs = "/a"\n')
    (tmp_path / "serve.toml").write_text('rootfs = "/b"\n')
    monkeypatch.setattr(build, "SERVE_SPEC", tmp_path / "serve.toml")
    monkeypatch.setattr(build, "HISTORY_DIR", tmp_path / "history")
    assert build.rollback() == 0
    assert f"{tmp_path / 'serve.toml'} {tmp_path / 'history/serve-20990101T000001Z.toml'}" in capsys.readouterr().out


def test_rollback_uses_deployment_history_not_canary_records(tmp_path, monkeypatch, capsys):
    a = 'rootfs = "/a"\nserved_model_name = "qwen"\nhome = "/home/a"\nargs = []\n'
    b = a.replace("/a", "/b")
    (tmp_path / "history").mkdir()
    (tmp_path / "history/serve-20260101T000000Z.toml").write_text(a)
    (tmp_path / "history/serve-20260102T000000Z.toml").write_text(b)
    (tmp_path / "serve.toml").write_text(b)
    monkeypatch.setattr(build, "SERVE_SPEC", tmp_path / "serve.toml")
    monkeypatch.setattr(build, "HISTORY_DIR", tmp_path / "history")
    assert build.rollback() == 0
    text = capsys.readouterr().out
    assert 'rootfs = "/a"' in text
    assert str(tmp_path / "history/serve-20260101T000000Z.toml") in text


@pytest.mark.parametrize("archived", ["163840", "262144"])
def test_rollback_moves_the_clients_around_the_restart_by_what_the_server_reports(tmp_path, monkeypatch, capsys,
                                                                                   archived):
    """`rollback` printed a spec-only server downgrade: the client catalogs kept advertising 262,144
    tokens to a server holding 163,840 (release audit NousCtx256c). Read from spec files, the
    capacity was wrong whenever the files and the running server disagree (NousCtx256d-g): the
    clients go no higher than what the running server reports and the restored spec before the
    restart, and to what the restarted server reports after it, in either direction."""
    spec = 'rootfs = "/{}"\nargs = ["--model", "/models/m", "--max-model-len", "{}"]\n'
    (tmp_path / "history").mkdir()
    (tmp_path / "history/serve-20260101T000000Z.toml").write_text(spec.format("a", archived))
    (tmp_path / "serve.toml").write_text(spec.format("b", "196608"))
    monkeypatch.setattr(build, "SERVE_SPEC", tmp_path / "serve.toml")
    monkeypatch.setattr(build, "HISTORY_DIR", tmp_path / "history")
    assert build.rollback() == 0
    out = capsys.readouterr().out
    first, restart, last = (out.index(s) for s in ("First set the client catalogs", "systemctl restart llama.service",
                                                   "Last, set the client catalogs"))
    assert first < out.index("Rollback:") < restart < last
    assert "the running server reports" in out[first:restart] and "restarted server reports" in out[last:]


def test_written_promote_toml_round_trips_through_nous_serve(tmp_path):
    from nevl.candidate import _serve_module
    rootfs = tmp_path / "rootfs"
    rootfs.mkdir()
    (rootfs / ".nous-serve-image.json").write_text("{}")
    spec = {"rootfs": str(rootfs), "served_model_name": "qwen-😀 \"q\"", "home": str(tmp_path),
            "args": ["--model", "qwen", "tab\there"], "env": {"A": "B", "DEL": "\x7f"}, "mounts": {}}  # surrogates, DEL broke it
    path = tmp_path / "candidate.toml"
    path.write_text(build._toml_spec(spec))
    loaded = _serve_module().load(path)
    assert {key: str(value) if isinstance(value, Path) else value for key, value in loaded.items()} == spec


@pytest.mark.parametrize("change, kept, gone", [
    ({"rootfs": "/srv/models/engines/vllm-sly-radiance-9.9"}, ["ledger M43", "ROCm/ROCm#6347", "upstream #164"], []),
    ({"env": {"RADIANCE_CACTUS_DELTA": "0.5", "NEW_KNOB": "1"}, "drop": ["GPU_MAX_HW_QUEUES", "RADIANCE_RUN_BWTEST"]},
     ["upstream #164", "ledger M43"], ["ROCm/ROCm#6347", "startup bandwidth sweep"]),
    ({"args_extra": ["--seed", "0"]}, ["ROCm/ROCm#6347", "upstream #164", "ledger M43", "ledger M57"], []),
    ({"args_set": {"--speculative-config.num_speculative_tokens": "7"}},
     ['  # 9 drafts (2026-11-06 tune sweeps', '\n  "--speculative-config.num_speculative_tokens", "7",\n',
      "ledger M43", "ledger M57"], []),
    ({"args_drop": ["--enable-prompt-tokens-details"]}, ["--enable-prefix-caching", "ledger M43"],
     ["usage.cached_tokens"]),
])
def test_promote_keeps_the_reasons_written_in_the_production_spec(change, kept, gone):
    """Promote rewrote production.toml without its comments, the only record of why each knob is
    set; now only changed values are rewritten, comments inside args included, and a removed
    knob goes with its reason (council F-09)."""
    import tomllib
    old_text = (build.REPO / "utils/nous/serve/production.toml").read_text()
    new = tomllib.loads(old_text)
    new["rootfs"] = change.get("rootfs", new["rootfs"])
    args = list(new["args"])
    for flag, value in change.get("args_set", {}).items():
        args[args.index(flag) + 1] = value
    new["args"] = [a for a in args if a not in change.get("args_drop", [])] + change.get("args_extra", [])
    new["env"] = {k: v for k, v in {**new["env"], **change.get("env", {})}.items() if k not in change.get("drop", [])}
    text = build._annotated_spec(old_text, new)
    assert tomllib.loads(text) == tomllib.loads(build._toml_spec(new))
    assert text.startswith(old_text.split("rootfs")[0])  # the header survives
    assert all(reason in text for reason in kept) and not any(reason in text for reason in gone)


def test_promote_reads_a_spec_however_its_values_are_wrapped():
    """An array wrapped after its first element is valid TOML that nous-serve loads; the
    merge aborted promote on it (release audit)."""
    import tomllib
    old = ('rootfs = "/engines/a"  # why this engine\nserved_model_name = "m"\nhome = "/h"\n'
           'args = ["--model",\n  "/models/w",\n]\n\n[env]\nA = "1"\n\n[mounts]\n')
    spec = {"rootfs": "/engines/b", "served_model_name": "m", "home": "/h",
            "args": ["--model", "/models/w"], "env": {"A": "1"}, "mounts": {}}
    text = build._annotated_spec(old, spec)
    assert "# why this engine" in text and tomllib.loads(text) == tomllib.loads(build._toml_spec(spec))
