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


def test_resume_refuses_a_run_that_a_reboot_moved_to_another_kernel(make_run, fake_workload, fake_server):
    """Arms measured on two kernels are not compared (ledger M54)."""
    fake_workload.n_items = 2
    fake_workload.fail = {"i1"}
    run = make_run()
    execute(run)
    run.write_json("host.json", {"kernel": "7.0.0-38-generic"})
    fake_workload.fail = set()
    fake_workload.calls.clear()
    assert execute(run) == 1
    assert fake_workload.calls == []
    assert "kernel changed" in run.done()["reason"]


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


def test_only_rows_whose_attempt_passed_its_end_check_are_kept(make_run, fake_workload, fake_server, monkeypatch):
    """An engine found dead after writing its rows passed on resume (M59); then an earlier attempt's
    passing end check vouched for a later attempt's rows, and a retry's pass for rows of an attempt
    that had failed (release audits, M61). A row counts only if the attempt that wrote it passed its
    end check; every other row is measured again."""
    fake_workload.n_items = 2
    dead = set()

    def check_alive(self):
        if self.candidate["label"] in dead:
            raise RuntimeError("engine died")
    monkeypatch.setattr(fake_server, "check_alive", check_alive)

    def measured(run, fail=(), died=()):
        fake_workload.fail = set(fail)
        fake_workload.calls.clear()
        dead.clear()
        dead.update(died)
        status = execute(run)
        return status, sorted({(c[0], c[1]) for c in fake_workload.calls})

    run = make_run()
    assert measured(run, fail={"i1"}, died={"b"}) == (1, [("a", "i0"), ("a", "i1"), ("b", "i0"), ("b", "i1")])
    assert run.done()["failed_labels"] == ["a", "b"]
    # a's i0 passed its check and stays; b's whole attempt is measured again
    assert measured(run) == (0, [("a", "i1"), ("b", "i0"), ("b", "i1")])

    run = make_run()
    assert measured(run, fail={"i1"})[0] == 1  # i0 vouched, i1 errored
    assert measured(run, died={"b"}) == (1, [("a", "i1"), ("b", "i1")])  # b's retry of i1 then dies
    assert run.done()["failed_labels"] == ["b"]
    assert measured(run) == (0, [("b", "i1")])  # only the row the failed retry wrote


def test_a_run_from_before_attempts_resumes_by_measuring_its_rows_again(make_run, fake_workload, fake_server):
    """Its manifests hold one record per block and its rows name no attempt (release audit, M61)."""
    import json
    fake_workload.n_items = 1
    run = make_run()
    assert execute(run) == 0
    for label in ("a", "b"):
        manifest = run.read_json(f"manifest.{label}.json")
        manifest["blocks"] = {block: {"load_s": 1.0, "ended": 2.0} for block in manifest["blocks"]}
        run.write_json(f"manifest.{label}.json", manifest)
    legacy = [{k: v for k, v in r.items() if k != "attempt"} for r in run.rows()]
    (run.path / "rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in legacy))
    fake_workload.calls.clear()
    assert execute(run) == 0 and len(fake_workload.calls) == len(legacy)  # every row again


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
    argv = lease_argv(plan, "t0")
    assert argv[:1] == ["llama-yield"] and argv[argv.index("--slice") + 1] == "llama.slice"
    assert argv[-4:] == ["resume", plan["run_id"], "--lease-token", "t0"]
    plan["run_id"] = "bad\nid"
    with pytest.raises(PlanError):
        lease_argv(plan, "t0")


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


def test_a_candidate_model_production_does_not_use_is_checked_before_the_lease(make_run, monkeypatch, tmp_path, capsys):
    """The host guards see the run's plan, not only production (ledger M18, M49)."""
    from nevl import guards
    run = make_run()
    missing = {"kind": "serve", "label": "other", "spec": {"mounts": {"/models": str(tmp_path)},
                                                          "args": ["--model", "/models/absent"]}}
    run.write_json("plan.json", {**run.plan, "lease": True,
                                 "candidates": {**run.plan["candidates"], "other": missing}})
    leases = []
    monkeypatch.setattr(guards, "REGISTRY", {"G-models-readable": guards.REGISTRY["G-models-readable"]})
    monkeypatch.setattr(runner, "in_lease", lambda: False)
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: leases.append(a))
    assert runner.start(run) == 1
    assert leases == [] and "absent" in capsys.readouterr().out


@pytest.mark.parametrize("results, taken", [(["success"], 1), (["timeout"] * 3, 3), (["timeout", "success"], 2),
                                            (["exit-code"], 1), (["stop-timeout"], 1)])
def test_only_a_lease_that_ran_out_is_followed_by_another(make_run, monkeypatch, results, taken):
    """Stopping the lease by hand, however close to its deadline, must not hand the GPU straight
    back to the run (council S-06; release audits): systemd's result decides, as systemd-run
    --wait prints it after the lease, with the child's own lines passed through. A stop that
    itself timed out (TimeoutStopSec) is also "timeout", but well before the lease's runtime."""
    from nevl import guards
    run = make_run()
    run.write_json("plan.json", {**run.plan, "lease": True})
    leases = []

    def lease_argv(plan, token):
        leases.append(plan)
        result = results[len(leases) - 1]
        runtime = "1d" if result == "timeout" else "41.5s"
        return ["sh", "-c", f"echo 'block 0: a, 1 items' >&2; "
                            f"echo '          Finished with result: {result.removeprefix('stop-')}' >&2; "
                            f"echo '               Service runtime: {runtime}' >&2; "
                            f"exit {0 if result == 'success' else 1}"]

    monkeypatch.setattr(runner, "in_lease", lambda: False)
    monkeypatch.setattr(guards, "run", lambda *args, **kwargs: [])
    monkeypatch.setattr(guards, "production_health", lambda: (True, "ok"))
    monkeypatch.setattr(runner, "lease_argv", lease_argv)
    assert runner.start(run) == 1
    assert len(leases) == taken


STARTED = "echo 'Running as unit: llama-yield-gpu.service' >&2"


@pytest.mark.parametrize("lease", [
    f"{STARTED}; exec sleep 30",  # ends on the first SIGTERM
    # sudo got it before it could relay it: the stop is repeated; the mark came first
    "trap '[ -f stopped.json ] && echo marked >> {seen}' TERM; sleep 2; trap - TERM; sleep 30 & wait",
    "sleep 1; exit 3"])  # never started (a guard refused)
def test_stopping_the_run_marks_it_then_ends_its_lease(make_run, monkeypatch, tmp_path, lease):
    """`systemctl --user stop` of a run's unit left its lease measuring without a client, and a power
    cut while the lease wound down left the run recoverable (release audits, M61). The run is
    marked stopped first, durably; then the lease command (sudo, relaying to llama-yield, which
    stops its own lease) gets SIGTERM until it ends."""
    import os
    import signal
    import threading
    from pathlib import Path
    run = make_run()
    pidfile, seen = tmp_path / "pid", tmp_path / "seen"
    command = f"echo $$ > {pidfile}; cd {run.path}; " + lease.format(seen=seen)
    monkeypatch.setattr(runner, "lease_argv", lambda plan, token: ["sh", "-c", command])
    threading.Timer(0.5, os.kill, (os.getpid(), signal.SIGTERM)).start()
    with pytest.raises(SystemExit) as exit:
        runner._lease(run.plan, run, "t0")
    assert exit.value.code == 128 + signal.SIGTERM
    assert run.read_json("stopped.json") and not Path(f"/proc/{int(pidfile.read_text())}").exists()
    assert seen.exists() == ("trap" in lease)


@pytest.mark.parametrize("when, lease, recoverable", [
    ("build", f"{STARTED}; exec sleep 30", False),  # SIGTERM to the client while it builds items
    ("preflight", f"{STARTED}; exec sleep 30", False),  # ... while the host guards run
    ("lease", f"{STARTED}; exec sleep 30", False),  # ... during the lease
    ("launch", f"{STARTED}; exec sleep 30", False),  # ... while the lease command launches
    (None, f"{STARTED}; echo '          Finished with result: success' >&2", False),  # the lease stopped by hand
    (None, f"{STARTED}; echo 'Finished with result: timeout' >&2; echo 'Service runtime: 45s' >&2",
     False),  # ... and its stop timed out
    (None, f"{STARTED}; echo 'Finished with result: timeout' >&2; echo 'Service runtime: 1d' >&2",
     True),  # every lease ran out
    (None, "echo 'llama-yield: another llama-yield caller is running' >&2; exit 2", True)])  # never leased
def test_a_stopped_run_stays_stopped_whatever_its_lease_child_wrote(make_run, monkeypatch, tmp_path, when, lease,
                                                                    recoverable):
    """The lease's child can die before its SIGTERM handler exists (still building items), and
    then writes no stopped.json: boot recovery resumed a run stopped by hand (release audits,
    M61). The client marks it; a lease that never started, or ran out, leaves the run as it was."""
    import os
    import signal
    import threading
    import time
    from pathlib import Path
    from nevl import guards, store
    run = make_run()
    run.write_json("plan.json", {**run.plan, "lease": True})
    run.append({"block": 0})  # rows from before a power loss: recovery's candidate
    assert store.interrupted(time.time() + 1, run.path.parent.parent) == [run.run_id]
    pidfile = tmp_path / "pid"

    def signalled(phase, result):
        def step(*args, **kwargs):
            if when == phase:
                os.kill(os.getpid(), signal.SIGTERM)
                time.sleep(1)
            return result
        return step

    monkeypatch.setattr(runner, "build_items", signalled("build", {}))
    monkeypatch.setattr(runner, "in_lease", lambda: False)
    monkeypatch.setattr(guards, "run", signalled("preflight", []))
    monkeypatch.setattr(guards, "production_health", lambda: (True, "ok"))
    monkeypatch.setattr(runner, "lease_argv",
                        lambda plan, token: ["sh", "-c", f"echo $$ > {pidfile}; cd {run.path}; {lease}"])
    popen = runner.subprocess.Popen

    def launch(argv, *args, **kwargs):
        proc = popen(argv, *args, **kwargs)
        if when == "launch" and str(pidfile) in str(argv):
            os.kill(os.getpid(), signal.SIGTERM)  # before _lease has the process
        return proc
    monkeypatch.setattr(runner.subprocess, "Popen", launch)
    if when == "lease":
        threading.Timer(0.5, os.kill, (os.getpid(), signal.SIGTERM)).start()
    if when:
        with pytest.raises(SystemExit) as exit:
            runner.start(run)
        assert exit.value.code == 128 + signal.SIGTERM
    else:
        assert runner.start(run) == 1
    if pidfile.exists():
        assert not Path(f"/proc/{int(pidfile.read_text())}").exists()  # no lease left running
    assert store.interrupted(time.time() + 1, run.path.parent.parent) == ([run.run_id] if recoverable else [])


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
    """The runner's process-group kill terminates its foreground server (ledger M27) and marks
    the run stopped, so boot recovery leaves it alone (council F-05)."""
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
    assert len(list(tmp_path.glob("**/stopped.json"))) == 1


def test_sigterm_between_blocks_marks_the_run_stopped(make_run, fake_workload, fake_server, monkeypatch):
    """Stopped while checking the next block's candidate, no server running: still stopped,
    so boot recovery does not resume it (release audit)."""
    import signal

    class Exited(Exception):
        pass

    def exit_(code):
        raise Exited(code)

    real = runner._check_manifest
    seen = []

    def check(run_, label, recorded):
        seen.append(label)
        if len(seen) == 2:
            signal.raise_signal(signal.SIGTERM)
        return real(run_, label, recorded)

    fake_workload.n_items = 1
    run = make_run()
    monkeypatch.setattr(runner, "_check_manifest", check)
    monkeypatch.setattr(runner.os, "_exit", exit_)
    with pytest.raises(Exited):
        execute(run)
    assert run.read_json("stopped.json") and not run.done()


def test_a_run_marked_stopped_starts_no_further_block(make_run, fake_workload, fake_server, monkeypatch):
    """The client marks the run before it ends the lease; the child must not start another block
    meanwhile (release audits, M61)."""
    fake_workload.n_items = 1
    run = make_run()
    measure = fake_workload.run_item

    def stopped_meanwhile(ctx, item):
        run.write_json("stopped.json", {"run_id": run.run_id})
        return measure(ctx, item)
    monkeypatch.setattr(fake_workload, "run_item", stopped_meanwhile)
    assert execute(run) == 1 and not run.done()
    assert {row["block"] for row in run.rows()} == {0}


def test_a_lease_that_ran_out_leaves_its_run_recoverable(make_run, monkeypatch):
    """systemd's SIGTERM at RuntimeMaxSec: the child marked the run stopped, so a power cut before
    the next lease left it out of boot recovery (release audits, M61). Only the client marks."""
    import time
    from nevl import store

    class Exited(Exception):
        pass

    def exit_(code):
        raise Exited(code)
    run = make_run()
    run.append({"block": 0})
    monkeypatch.setattr(runner, "in_lease", lambda: True)
    monkeypatch.setattr(runner.os, "_exit", exit_)
    with pytest.raises(Exited):
        runner._killed(None, run)
    assert store.interrupted(time.time() + 1, run.path.parent.parent) == [run.run_id]


def test_boot_recovery_leaves_a_run_stopped_after_it_was_chosen(make_run, fake_workload, fake_server, monkeypatch):
    """Stopped by hand while recovery waited for production: resuming it anyway undid the stop
    (release audit, M61)."""
    from nevl import cli
    fake_workload.n_items = 1
    run = make_run()
    monkeypatch.setattr(cli.store, "interrupted", lambda boot: [run.run_id])

    def health(timeout_s):
        run.write_json("stopped.json", {"run_id": run.run_id})  # nous-eval stopped meanwhile
        return True, ""
    monkeypatch.setattr(cli.guards, "production_health", health)
    assert cli.cmd_recover(None) == 1
    assert not run.done() and (run.path / "stopped.json").exists()


def test_one_process_runs_a_run_at_a_time(make_run, fake_workload, fake_server):
    """A second resume (or recovery) while the run is running: refused, and the run is not
    marked stopped by the process that never ran it (release audit, M61)."""
    import fcntl
    fake_workload.n_items = 1
    run = make_run()
    with open(run.path / "lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        assert runner.start(run) == 1
    assert not run.done() and not (run.path / "stopped.json").exists()
    assert runner.start(run) == 0 and run.done()["status"] == "ok"


def test_inside_a_lease_only_the_command_its_client_launched_runs_the_run(make_run, fake_workload, fake_server,
                                                                          monkeypatch):
    """`nous-eval canary`, or a second resume, inside a lease skipped the run's lock and cleared a
    stopped mark (release audits, M61)."""
    import fcntl
    fake_workload.n_items = 1
    run = make_run()
    claim, stopped = run.path / runner.LEASE_CLAIM, run.path / "stopped.json"
    monkeypatch.setattr(runner, "in_lease", lambda: True)
    assert runner.start(run, lease_token="t0") == 1  # no client leased it
    claim.write_text("t0\n")
    assert runner.start(run, lease_token="t0") == 1  # its client is gone (the lock is free)
    with open(run.path / "lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # the client
        claim.write_text("t0\n")
        assert runner.start(run, automatic=True) == 1  # the canary or recovery
        assert runner.start(run) == 1 and runner.start(run, lease_token="t1") == 1  # no or another token
        with open(run.path / "exec.lock", "a") as running:
            fcntl.flock(running, fcntl.LOCK_EX)
            assert runner.start(run, lease_token="t0") == 1  # another one runs it
        claim.write_text("t0\n")
        run.write_json("stopped.json", {"run_id": run.run_id})
        assert runner.start(run, lease_token="t0") == 1 and stopped.exists()  # its client was stopped meanwhile
        stopped.unlink()
        claim.write_text("t0\n")
        assert not run.done() and runner.start(run, lease_token="t0") == 0 and run.done()["status"] == "ok"
        assert runner.start(run, lease_token="t0") == 1  # a second one: the claim is taken
