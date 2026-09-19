"""Exercise the worker boundary without contacting nous or spending model tokens."""
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest


WORKER = Path(__file__).resolve().parents[3] / "home/dot_local/bin/executable_nous-worker"
HARNESS = """
import os, runpy, sys, urllib.request
from contextlib import nullcontext
from types import SimpleNamespace
def health(*args, **kwargs):
    if os.environ.get('OFFLINE'):
        raise OSError('test backend unavailable')
    return nullcontext(SimpleNamespace(status=200))
urllib.request.urlopen = health
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
"""
FAKE = """
import json, os, signal, subprocess, sys, time
from pathlib import Path
root = Path(os.environ['FIXTURE'])
(root/'invocation.json').write_text(json.dumps({'args':sys.argv[1:], 'config':json.loads(os.environ['OPENCODE_CONFIG_CONTENT'])}))
if os.environ.get('HANG'):
    child = subprocess.Popen([sys.executable, '-c', 'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)'])
    (root/'pids.json').write_text(json.dumps([os.getpid(), child.pid]))
    time.sleep(60)
else:
    print(json.dumps({'type':'tool_use', 'sessionID':'fixture-session', 'part':{'tool':'read', 'state':{'output':'X'*50000}}}))
    print(json.dumps({'type':'text', 'sessionID':'fixture-session', 'part':{'text':'checked '+('Y'*7000)}}))
    print(json.dumps({'type':'text', 'sessionID':'fixture-session', 'part':{'text':'hidden system reminder', 'synthetic':True}}))
"""


@pytest.fixture
def fixture(tmp_path):
    binary = tmp_path / "opencode-baseline"
    binary.write_text(f"#!{sys.executable}\n" + FAKE)
    binary.chmod(0o700)
    env = dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ["PATH"],
               XDG_STATE_HOME=str(tmp_path / "state"), FIXTURE=str(tmp_path))
    command = [sys.executable, "-c", HARNESS, str(WORKER), "--dir", str(tmp_path)]
    return tmp_path, command, env


def test_compact_result_preserves_full_trace_and_scoped_invocation(fixture):
    root, command, env = fixture
    env["OPENCODE_CONFIG_CONTENT"] = json.dumps({"small_model":"openai/paid", "enabled_providers":["openai"], "agent":{"compaction":{"model":"openai/paid"}}})
    result = subprocess.run(command + ["--read-only", "--steps", "5", "--session", "old-session", "Read input"], env=env, capture_output=True, text=True, timeout=10, check=True)
    summary = json.loads(result.stdout)
    assert len(result.stdout) < 8000
    assert summary["status"] == "completed" and summary["verified"] is False
    assert summary["session"] == "fixture-session" and summary["tool_calls"] == 1
    assert summary["result"].startswith("checked ") and summary["result_truncated"]
    evidence = Path(summary["evidence"])
    assert (evidence / "events.jsonl").stat().st_size > 57000
    assert evidence.stat().st_mode & 0o077 == 0
    invocation = json.loads((root / "invocation.json").read_text())
    config = invocation["config"]
    assert config["enabled_providers"] == ["nous"]
    assert config["small_model"] == config["model"] == config["agent"]["compaction"]["model"] == "nous/Ornith-1.5-9B-Q5_K_M"
    assert invocation["args"][-3:] == ["old-session", "--", "Read input"]
    worker = invocation["config"]["agent"]["nous-worker"]
    assert worker["steps"] == 5 and worker["model"] == "nous/Ornith-1.5-9B-Q5_K_M"
    assert worker["permission"].get("edit", "deny") == "deny"
    assert worker["permission"]["*"] == "deny"


def test_busy_and_offline_do_not_start_a_worker(fixture):
    root, command, env = fixture
    state = root / "state/nous-workers"
    state.mkdir(parents=True)
    with (state / "worker.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = subprocess.run(command + ["Task"], env=env, capture_output=True, text=True, timeout=5)
        assert result.returncode == 75 and json.loads(result.stdout)["status"] == "busy"
    result = subprocess.run(command + ["Task"], env=dict(env, OFFLINE="1"), capture_output=True, text=True, timeout=5)
    assert result.returncode == 69 and json.loads(result.stdout)["status"] == "unavailable"
    assert not (root / "invocation.json").exists()


@pytest.mark.parametrize("cancel", [False, True], ids=["deadline", "caller_sigterm"])
def test_deadline_and_cancellation_stop_children_and_release_slot(fixture, cancel):
    root, command, env = fixture
    process = subprocess.Popen(command + ["--timeout", "30" if cancel else "1", "Task"], env=dict(env, HANG="1"), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    pids = []
    try:
        deadline = time.monotonic() + 5
        while not (root / "pids.json").exists() and time.monotonic() < deadline:
            time.sleep(.02)
        pids = json.loads((root / "pids.json").read_text())
        if cancel:
            process.send_signal(signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=8)
        assert process.returncode == (143 if cancel else 124), stderr
        assert json.loads(stdout)["status"] == ("interrupted" if cancel else "timeout")
        # A killed descendant may briefly be a zombie awaiting OS reaping.
        for pid in pids:
            state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
            assert not state or state.startswith("Z"), (pid, state)
        resumed = subprocess.run(command + ["--format", "json", "Retry"], env=env, capture_output=True, text=True, timeout=5)
        assert resumed.returncode == 0
        assert json.loads(resumed.stdout.splitlines()[0])["type"] == "tool_use"
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
