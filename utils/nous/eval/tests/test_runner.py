import pytest

from nevl import runner
from nevl.candidate import load
from nevl.runner import PlanError, blocks_for, execute, lease_argv, lease_runtime
from nevl.store import Run

from conftest import TIERS


def test_abba_blocks_and_duplicate_labels():
    assert blocks_for(["a", "b"], "abba") == ["a", "b", "b", "a"]
    assert blocks_for(["a"], "abba") == ["a", "a"]
    with pytest.raises(PlanError):
        blocks_for(["a", "a"], "ab")


def test_every_block_runs_every_item_and_rep(make_run, fake_workload, fake_server):
    fake_workload.n_items = 3
    run = make_run()
    assert execute(run) == 0
    rows = run.rows()
    assert len(rows) == 4 * 3 * 2  # blocks x items x reps
    assert {r["seed"] for r in rows} == {0, 1000}  # reps get distinct seeds, blocks share them
    assert run.done()["status"] == "ok"


def test_errors_fail_the_run_and_resume_retries_only_them(make_run, fake_workload, fake_server):
    fake_workload.n_items = 3
    fake_workload.fail = {"i1"}
    run = make_run()
    assert execute(run) == 1
    assert run.done()["status"] == "failed" and run.done()["error_count"] == 8
    fake_workload.fail = set()
    fake_workload.calls.clear()
    assert execute(run) == 0
    assert {c[1] for c in fake_workload.calls} == {"i1"}  # finished items are not rerun
    assert run.done()["status"] == "ok"


def test_resume_refuses_items_that_changed_since_the_run_started(make_run, fake_workload, fake_server):
    """A re-fetched dataset reuses item ids for other questions (council S-06)."""
    fake_workload.n_items = 3
    fake_workload.fail = {"i1"}
    run = make_run()
    execute(run)
    fake_workload.fail = set()
    fake_workload.n_items = 4
    fake_workload.calls.clear()
    assert execute(run) == 1
    assert "inputs changed" in run.done()["reason"] and not fake_workload.calls


def test_resume_refuses_a_data_file_that_changed_under_the_same_items(make_run, fake_workload, fake_server,
                                                                      monkeypatch, tmp_path):
    """Re-fetched filler or grading tests keep their item ids (council S-06, A-05)."""
    import nevl.runner
    monkeypatch.setattr(nevl.runner, "DATA_DIR", tmp_path)
    (tmp_path / "filler.txt").write_text("one")
    fake_workload.INPUTS = ("filler.txt",)
    fake_workload.n_items = 2
    fake_workload.fail = {"i1"}
    run = make_run()
    execute(run)
    (tmp_path / "filler.txt").write_text("two")
    fake_workload.fail = set()
    assert execute(run) == 1
    assert "inputs changed" in run.done()["reason"]


def test_resume_refuses_a_candidate_that_changed_since_the_run_started(make_run, fake_workload, fake_server):
    """A retagged image or rebuilt engine must not join the old rows (council A-05)."""
    fake_workload.n_items = 2
    fake_workload.fail = {"i1"}
    run = make_run()
    execute(run)
    recorded = run.read_json("manifest.a.json")
    run.write_json("manifest.a.json", {**recorded, "identity": "sha256:older-image"})
    fake_workload.fail = set()
    fake_workload.calls.clear()
    assert execute(run) == 1
    assert {c[0] for c in fake_workload.calls} == {"b"}
    assert any("candidate changed" in f for f in run.done()["block_failures"])


def test_reasoning_leak_fails_the_run(make_run, fake_workload, fake_server):
    fake_workload.n_items = 2
    fake_workload.leak = {"i0"}
    run = make_run()
    assert execute(run) == 1
    assert run.done()["leaks"]


def test_a_score_can_be_explained_from_the_run_directory(make_run, fake_workload, fake_server, monkeypatch):
    """A zero needs the reply that earned it, without a rerun (ledger M31)."""
    import io
    import json
    import nevl.ctx

    def urlopen(request, timeout):
        chunks = [{"choices": [{"delta": {"content": "no JSON here"}, "finish_reason": "stop"}]}]
        return io.BytesIO(b"".join(b"data: " + json.dumps(c).encode() + b"\n\n" for c in chunks)
                          + b"data: [DONE]\n\n")
    monkeypatch.setattr(nevl.ctx.urllib.request, "urlopen", urlopen)
    fake_workload.n_items = 1

    def run_item(ctx, item):
        reply = ctx.chat({})
        return {"tps": 50.0, "ok": float(reply.content.startswith("{"))}
    fake_workload.run_item = run_item
    run = make_run()
    execute(run)
    replies = [json.loads(line) for line in (run.path / "replies.jsonl").read_text().splitlines()]
    keys = {(r["block"], r["candidate"], r["workload"], r["item"], r["rep"]) for r in replies}
    assert keys == {(r["block"], r["candidate"], r["workload"], r["item"], r["rep"]) for r in run.rows()}
    assert {r["replies"][0]["content"] for r in replies} == {"no JSON here"}


def test_server_failure_is_recorded_not_fatal(make_run, fake_workload, fake_server, monkeypatch):
    fake_workload.n_items = 1

    def broken(self):
        raise RuntimeError("no GPU")

    monkeypatch.setattr(fake_server, "start", broken)
    run = make_run()
    assert execute(run) == 1
    assert len(run.done()["block_failures"]) == 4 and run.done()["missing"] == 8


def test_an_engine_that_dies_mid_block_fails_the_block_and_names_its_log(make_run, fake_workload, monkeypatch):
    """vLLM's engine died on one screenshot; every later item failed in milliseconds and
    only a search of the server log explained 264 row errors (ledger M42)."""
    import io
    import subprocess
    import urllib.error

    import nevl.ctx
    from nevl.server import Server

    dead = []

    def start(self):
        self.proc = subprocess.Popen(["sleep", "60"], start_new_session=True)  # still running
        return 0.0

    def urlopen(request, timeout):
        if dead:
            raise urllib.error.HTTPError(request.full_url, 500, "dead", {}, io.BytesIO(b"EngineDeadError"))
        return io.BytesIO(b'data: {"choices": [{"delta": {"content": "OK"}, "finish_reason": "stop"}]}\n\n'
                          b"data: [DONE]\n\n")

    def run_item(ctx, item):
        if item["id"] == "i1":
            dead.append(True)
        if dead:
            raise RuntimeError("HTTP 500")
        return {"tps": 50.0, "ok": 1.0}

    monkeypatch.setattr(Server, "start", start)
    monkeypatch.setattr(nevl.ctx.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(runner, "manifest", lambda c: {"label": c["label"]})
    monkeypatch.setattr(fake_workload, "run_item", run_item)
    fake_workload.n_items = 3
    run = make_run(labels=("a",))
    assert execute(run) == 1
    failures = run.done()["block_failures"]
    assert len(failures) == 2 and all("stopped answering" in f and "a.server.log" in f for f in failures)


def test_plan_snapshot_survives_candidate_edits(tmp_path, make_run, fake_workload, fake_server):
    preset = tmp_path / "models.ini"
    preset.write_text("[*]\nctx-size = 1\n[m]\nmodel = /x.gguf\nload-on-startup = true\n")
    toml = tmp_path / "c.toml"
    toml.write_text(f'label = "c"\nengine = "/bin/true"\npreset = "{preset}"\n')
    plan = runner.plan_run("tx", [load(toml)], lease=False, port=18850, tiers=TIERS)
    run = Run.create(plan, tmp_path)
    preset.write_text("[*]\nctx-size = 999\n[m]\nmodel = /y.gguf\nload-on-startup = true\n")
    fake_workload.n_items = 1
    execute(run)
    assert all("ctx-size = 1\n" in c["preset_text"] for c in fake_server.started)


def test_lease_argv_is_an_argv_in_llama_slice(make_run):
    plan = make_run().plan
    argv = lease_argv(plan)
    assert argv[:1] == ["llama-yield"] and argv[argv.index("--slice") + 1] == "llama.slice"
    assert argv[-2:] == ["resume", plan["run_id"]]
    plan["run_id"] = "bad\nid"
    with pytest.raises(PlanError):
        lease_argv(plan)


def test_lease_runtime_covers_every_block(make_run):
    plan = make_run().plan
    need = sum(plan["budget_s"] + plan["candidates"][x]["ready_timeout_s"] for x in plan["blocks"])
    assert lease_runtime(plan) >= need


def test_missing_data_fails_before_taking_the_gpu(make_run, fake_workload, monkeypatch):
    run = make_run()
    run.write_json("plan.json", {**run.plan, "lease": True})

    def no_data(tier, opts, data_dir):
        raise FileNotFoundError("questions.jsonl")

    leases = []
    monkeypatch.setattr(fake_workload, "items", no_data)
    monkeypatch.setattr(runner, "in_lease", lambda: False)
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: leases.append(a))
    assert runner.start(run) == 1
    assert leases == []


CHILD = """
import subprocess, sys, time, types
from pathlib import Path
sys.path[:0] = [sys.argv[1], sys.argv[1] + "/tests"]
from conftest import TIERS, command_candidate
from nevl import runner, workloads
from nevl.server import Server
from nevl.store import Run
def start(self):
    self.proc = subprocess.Popen(["sleep", "60"], start_new_session=True)
    Path(sys.argv[2]).write_text(str(self.proc.pid))
    print("ready", flush=True)
    return 0.0
Server.start = start
workloads.REGISTRY["fake"] = types.SimpleNamespace(
    NAME="fake", VERSION="1", METRICS={}, MUST_PASS=(), REPORTED=(), NEEDS_GRADE=False,
    items=lambda tier, opts, data_dir: [{"id": "i0"}],
    run_item=lambda ctx, item: time.sleep(60), summarize=lambda rows: {})
plan = runner.plan_run("tx", [command_candidate("a")], lease=False, port=18850, tiers=TIERS)
runner.execute(Run.create(plan, Path(sys.argv[3])))
"""


def test_sigterm_kills_a_command_candidate_before_exiting(tmp_path):
    """The runner's process-group kill terminates its foreground server (ledger M27)."""
    import subprocess
    import sys
    import time
    from pathlib import Path
    marker = tmp_path / "server-pid"
    package = str(Path(__file__).resolve().parents[1])
    child = subprocess.Popen([sys.executable, "-c", CHILD, package, str(marker), str(tmp_path)],
                             stdout=subprocess.PIPE, text=True)
    assert child.stdout.readline().strip().endswith("items")
    assert child.stdout.readline().strip() == "ready"
    server_pid = int(marker.read_text())
    child.terminate()
    assert child.wait(timeout=20) == 143
    deadline = time.monotonic() + 5
    while Path(f"/proc/{server_pid}").exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not Path(f"/proc/{server_pid}").exists()
