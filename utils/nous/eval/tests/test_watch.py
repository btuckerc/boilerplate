import json
import os

from nevl import watch


def test_first_run_seeds_without_an_inbox_note(tmp_path, monkeypatch):
    monkeypatch.setattr(watch, "CONFIG", tmp_path / "watch.toml")
    monkeypatch.setattr(watch, "ARTIFACTS", tmp_path / "artifacts.json")
    monkeypatch.setattr(watch, "incumbent", lambda: {"spec": {"args": [], "mounts": {}, "rootfs": ""}})
    monkeypatch.setattr(watch, "production_unbound", lambda production: "not judged here")  # no live host
    monkeypatch.setattr(watch.store, "root", lambda: tmp_path / "root")
    watch.CONFIG.write_text('inbox = "' + str(tmp_path / "inbox") + '"\n')
    watch.ARTIFACTS.write_text('{"models": []}')
    monkeypatch.setattr(watch, "fetch_hf_author", lambda author: [])
    monkeypatch.setattr(watch, "fetch_github", lambda repo: {"tag_name": "v1", "html_url": "https://example/release"})
    monkeypatch.setattr(watch, "fetch_docker", lambda repo: {"results": []})
    assert watch.run() == 0
    assert (tmp_path / "root/watch/seen.json").exists()
    assert not (tmp_path / "inbox").exists()


def test_new_hf_id_reported_only_once():
    config = {}
    snapshot = {"authors": {"Qwen": [{"id": "Qwen/model", "createdAt": "today"}]}}
    items, seen = watch.findings(config, snapshot, {"hf": {"Qwen": []}, "github": {}, "docker": {}})
    assert [(item["kind"], item["url"]) for item in items] == [("new", "https://huggingface.co/Qwen/model")]
    items, _ = watch.findings(config, snapshot, seen)
    assert not any(item["kind"] == "new" for item in items)


def test_production_revision_is_open_until_recorded():
    config = {}
    snapshot = {"production": [{"repo": "Qwen/model", "recorded_revision": "old", "upstream_sha": "new"}]}
    seen = {"hf": {}, "github": {}, "docker": {}}
    for _ in range(2):
        items, seen = watch.findings(config, snapshot, seen)
        assert any(item["kind"] == "open" for item in items)
    snapshot["production"][0]["recorded_revision"] = "new"
    items, _ = watch.findings(config, snapshot, seen)
    assert not any(item["kind"] == "open" for item in items)


def test_fetch_failure_leaves_source_unadvanced_while_others_advance():
    seen = {"hf": {"Qwen": []}, "github": {"ok/repo": "old"}, "docker": {}}
    snapshot = {"errors": [{"source": "Qwen", "error": "offline"}],
                "github": {"ok/repo": {"tag": "new"}}}
    items, updated = watch.findings({}, snapshot, seen)
    assert updated["hf"]["Qwen"] == []
    assert updated["github"]["ok/repo"] == "new"
    assert any(item["kind"] == "error" and item["source"] == "Qwen" for item in items)


def test_canary_record_for_latest_release_is_reported():
    snapshot = {"github": {watch.RADIANCE_REPO: {"tag": "v2", "url": "https://example/v2"}},
                "canary": {"2": {"verdict": "pass", "run_id": "r1", "t3_run_id": "r2"}}}
    items, _ = watch.findings({}, snapshot, {"hf": {}, "github": {watch.RADIANCE_REPO: "v2"}, "docker": {}})
    assert any("verdict pass" in item["text"] and "r1" in item["text"] and "r2" in item["text"] for item in items)


def test_a_started_run_that_went_quiet_without_finishing_is_open(tmp_path):
    runs = tmp_path / "runs"
    for name, rows, done, age in (("stalled", True, False, 7), ("live", True, False, 1),
                                  ("finished", True, True, 7), ("never-started", False, False, 7)):
        (runs / name).mkdir(parents=True)
        if rows:
            (runs / name / "rows.jsonl").write_text("{}\n")
            os.utime(runs / name / "rows.jsonl", (1e9 - age * 3600, 1e9 - age * 3600))
        if done:
            (runs / name / "done.json").write_text("{}")
    assert [run["run_id"] for run in watch.stalled_runs(runs, 1e9)] == ["stalled"]
    items, _ = watch.findings({}, {"stalled": watch.stalled_runs(runs, 1e9)}, {"hf": {}, "github": {}, "docker": {}})
    assert [(item["kind"], item["source"]) for item in items] == [("open", "stalled")]


def test_production_without_passing_t2_and_t3_evidence_is_open(tmp_path, monkeypatch):
    from nevl.store import Run

    def evidence(tier, measured, of, a, b, failed=None):
        """A finished run whose compare says arm b (label, serving id) is non-inferior to arm a;
        `failed` names the arms done.json lists as failed."""
        run = Run.create({"run_id": f"{tier}-{len(list(tmp_path.glob('runs/*')))}", "tier": tier, "created": 1,
                          "candidates": {a[0]: {}, b[0]: {}},
                          "workloads": [{"name": w} for w in measured], "tier_workloads": of}, tmp_path)
        for label, serving in (a, b):
            run.write_json(f"manifest.{label}.json", {"label": label, "id": serving, "kernel": "k1", "blocks": {}})
        run.finish("failed", failed_labels=failed) if failed else run.finish("ok")
        run.write_json(f"compare.{a[0]}.{b[0]}.json", {"a": a[0], "b": b[0], "verdict": "pass",
                                                       "evidence": run.evidence()})
        return run

    def missing(identity):
        return watch.production_qualification(identity)["missing"]

    monkeypatch.setattr(watch.store, "root", lambda: tmp_path)
    live = {"label": "incumbent", "id": "live", "kernel": "k1"}
    assert missing(live) == ["t2 or canary", "t3"]
    # a run in which production's own arm failed is no evidence, whatever its stored verdict
    evidence("t3", ["lcb"], ["lcb"], ("llamacpp", "old"), ("incumbent", "live"), failed=["incumbent"])
    assert missing(live) == ["t2 or canary", "t3"]
    # final-spec t3: llama.cpp as A, production as B; a third arm that crashed does not void it (council A-07)
    evidence("t3", ["lcb"], ["lcb"], ("llamacpp", "old"), ("incumbent", "live"), failed=["final-cactus05"])
    # canary path: the promoted candidate was B under its own label; a subset is not evidence
    evidence("canary", ["speed"], ["speed", "longctx"], ("incumbent", "old"), ("radiance-1.18", "live"))
    # production measured only as the baseline another arm matched says nothing about production
    evidence("t2", ["speed", "longctx"], ["speed", "longctx"], ("incumbent", "live"), ("other", "x"))
    assert missing(live) == ["t2 or canary"]
    canary = evidence("canary", ["speed", "longctx"], ["speed", "longctx"], ("incumbent", "old"),
                      ("radiance-1.18", "live"))
    assert missing(live) == []
    canary.finish("ok")  # resumed and finished again after its report: that pass is stale (release audit)
    assert missing(live) == ["t2 or canary"]
    canary.write_json("compare.incumbent.radiance-1.18.json", {"a": "incumbent", "b": "radiance-1.18",
                                                              "verdict": "pass", "evidence": canary.evidence()})
    assert missing(live) == []
    assert missing({**live, "id": "changed knob"}) == ["t2 or canary", "t3"]
    # a kernel update keeps the evidence, and says so without alerting
    rebooted = watch.production_qualification({**live, "kernel": "k2"})
    items, _ = watch.findings({}, {"production_qualification": rebooted}, {"hf": {}, "github": {}, "docker": {}})
    assert rebooted["missing"] == [] and [(i["kind"], "k1" in i["text"]) for i in items] == [("status", True)]


def test_evidence_is_judged_only_for_the_spec_production_runs(tmp_path):
    """A qualified spec installed without a restart cleared the open item while the old spec
    still served (release audit); the ctime and clock arithmetic that guarded it failed again on
    a read race and a clock step (ledger M60). Production is judged by the spec nous-serve
    recorded loading, and only if that is still the spec the judged snapshot came from."""
    from pathlib import Path
    rootfs = tmp_path / "rootfs"
    rootfs.mkdir()
    (rootfs / ".nous-serve-image.json").write_text("{}")
    spec, record = tmp_path / "serve.toml", tmp_path / "run" / "serve.toml"
    record.parent.mkdir()

    def write(path, model):
        path.write_text(f'rootfs = "{rootfs}"\nserved_model_name = "{model}"\nhome = "{tmp_path}"\nargs = []\n')

    def snapshot(path):  # what incumbent() resolved, as a run or the watch holds it
        loaded = watch._serve_module().load(path)
        return {"spec_source": str(path), "spec": {k: str(v) if isinstance(v, Path) else v for k, v in loaded.items()}}
    write(spec, "a")
    write(record, "a")
    running = snapshot(record)
    assert watch.production_unbound(running, spec) is None  # runs what is installed
    write(spec, "b")
    assert "restart" in watch.production_unbound(running, spec)  # installed without one
    write(record, "b")  # restarted onto b while the watch held a's snapshot
    assert "changed during this check" in watch.production_unbound(running, spec)
    assert watch.production_unbound(snapshot(record), spec) is None
    record.unlink()  # stopped mid-check
    assert "cannot compare" in watch.production_unbound(running, spec)
    # no record: a lease, so the file starts next; or a unit that does not record, so unknown
    assert watch.production_unbound(snapshot(spec), spec, active=False) is None
    assert "--record" in watch.production_unbound(snapshot(spec), spec, active=True)
    items, _ = watch.findings({}, {"production_qualification": {"unbound": "changed"}},
                              {"hf": {}, "github": {}, "docker": {}})
    assert [(i["kind"], i["source"]) for i in items] == [("open", "production-qualification")]


def test_top_level_failure_writes_error_to_inbox_before_returning(tmp_path, monkeypatch):
    monkeypatch.setattr(watch, "CONFIG", tmp_path / "watch.toml")
    monkeypatch.setattr(watch, "ARTIFACTS", tmp_path / "artifacts.json")
    inbox = tmp_path / "inbox"
    monkeypatch.setenv("NOUS_EVAL_INBOX", str(inbox))
    watch.CONFIG.write_text('inbox = "' + str(inbox) + '"\n')
    watch.ARTIFACTS.write_text('{"models": []}')
    monkeypatch.setattr(watch, "incumbent", lambda: (_ for _ in ()).throw(ValueError("not nous-serve")))
    assert watch.run() == 1
    assert "not nous-serve" in next(inbox.glob("*.md")).read_text()


def test_upstream_is_still_watched_after_a_rollback_to_llamacpp(tmp_path, monkeypatch):
    """Production that is not nous-serve skips the production checks, not the upstream ones (council O-07)."""
    from nevl.candidate import CandidateError
    monkeypatch.setattr(watch, "CONFIG", tmp_path / "watch.toml")
    monkeypatch.setattr(watch, "ARTIFACTS", tmp_path / "artifacts.json")
    inbox = tmp_path / "inbox"
    monkeypatch.setenv("NOUS_EVAL_INBOX", str(inbox))
    watch.CONFIG.write_text(f'inbox = "{inbox}"\n[[github_release]]\nrepo = "ggml-org/llama.cpp"\nwhy = "engine"\n')
    watch.ARTIFACTS.write_text('{"models": []}')
    monkeypatch.setattr(watch, "incumbent", lambda: (_ for _ in ()).throw(CandidateError("llama.service is not nous-serve")))
    tags = iter(["b1", "b2"])
    monkeypatch.setattr(watch, "fetch_github", lambda repo: {"tag_name": next(tags)})
    assert watch.run() == 0 and watch.run() == 0
    note = next(inbox.glob("*.md")).read_text()
    assert "New release: ggml-org/llama.cpp b2" in note and "not nous-serve; production checks skipped" in note
