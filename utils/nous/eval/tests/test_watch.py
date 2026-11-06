import json
import os

from nevl import watch


def test_first_run_seeds_without_an_inbox_note(tmp_path, monkeypatch):
    monkeypatch.setattr(watch, "CONFIG", tmp_path / "watch.toml")
    monkeypatch.setattr(watch, "ARTIFACTS", tmp_path / "artifacts.json")
    monkeypatch.setattr(watch, "incumbent", lambda: {"spec": {"args": [], "mounts": {}, "rootfs": ""}})
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
