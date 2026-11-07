import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

import pytest


ROOT = Path(__file__).resolve().parents[3]
BIN = ROOT / "home/dot_local/bin"
RUN = BIN / "executable_agent-run"
QUOTA = BIN / "executable_agent-quota"
STATUS = BIN / "executable_claude-statusline"


def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


runner = load("agent_run", RUN)
quota = load("agent_quota", QUOTA)


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE)


@pytest.fixture
def repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Test")
    (repo / "keep.txt").write_text("original\n")
    (repo / "delete.txt").write_text("delete me\n")
    (repo / "blob.bin").write_bytes(b"\x00old\xff")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "fixture")
    return repo


FAKE_CLI = r'''#!/usr/bin/env python3
import json, os, pathlib, signal, sys, time
args = sys.argv[1:]
mode = os.environ.get("FAKE_MODE", "ok")
prompt = sys.stdin.read()
local_child = pathlib.Path(args[args.index("--session-dir") + 1]).parent if pathlib.Path(sys.argv[0]).name == "omp-local" else None
called = local_child / "called.json" if local_child else pathlib.Path(os.environ["FAKE_CALLED"])
environment_receipt = local_child / "env.json" if local_child else pathlib.Path(os.environ["FAKE_ENV"])
called.write_text(json.dumps({"args": args, "prompt": prompt,
                             "tmp": {key: os.environ.get(key) for key in ("TMPDIR", "TMP", "TEMP")},
                             "child": os.environ.get("AGENT_RUN_CHILD")}))
check = {k: k in os.environ for k in ("HERDR_ENV", "HERDR_PANE_ID", "HERDR_SOCKET_PATH", "ANTHROPIC_API_KEY", "CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "OPENAI_API_KEY", "PI_SESSION_FILE", "OMPCODE", "CODEX_THREAD_ID")}
environment_receipt.write_text(json.dumps(check))
if "-C" in args:
    os.chdir(args[args.index("-C") + 1])
if mode in {"filter-edit", "local-filter-edit"}:
    pathlib.Path("filter.sh").write_text("printf attacked > " + __import__("shlex").quote(os.environ["FAKE_FILTER_MARKER"]) + "\ncat\n")
    pathlib.Path(".gitattributes").write_text("*.txt filter=x diff=x\n")
    pathlib.Path("keep.txt").write_text("unfiltered worker edit\n")
if mode == "sleep":
    time.sleep(60)
if pathlib.Path(sys.argv[0]).name == "claude":
    session = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    projects = pathlib.Path(os.environ["CLAUDE_CONFIG_DIR"]) / "projects" / "fake-project"
    projects.mkdir(parents=True, exist_ok=True)
    model = "claude-fable-5-5" if args[args.index("--model") + 1] == "fable" else "claude-opus-5-5"
    records = [
        {"type": "api-request", "params": {"model": model, "output_config": {"effort": "high"}}},
        {"type": "attachment", "attachment": {"type": "prompt_snapshot", "tools": [
            {"name": name, "schema": {}} for name in ("Read", "Grep", "Glob", "WebSearch", "WebFetch", "StructuredOutput")]}},
        {"type": "assistant", "message": {"model": model, "content": [{"type": "tool_use", "name": "Read", "input": {}}]}}]
    (projects / (session + ".jsonl")).write_text("".join(json.dumps(r) + "\n" for r in records))
    result = {"paths": [], "checks_run": [], "summary": "fake Claude consult", "blockers": []}
    print(json.dumps({"is_error": False, "session_id": session, "structured_output": result, "modelUsage": {model: {"inputTokens": 1}}}))
    sys.exit(0)
if pathlib.Path(sys.argv[0]).name == "omp-local":
    pathlib.Path("keep.txt").write_text("local worker edit\n")
    session = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    folder = pathlib.Path(args[args.index("--session-dir") + 1])
    folder.mkdir()
    print(json.dumps({"type": "session", "id": session}))
    print(json.dumps({"type": "message_end", "message": {"role": "assistant", "provider": "vllm", "model": "test-local",
        "content": [{"type": "text", "text": "I will read the brief."}], "stopReason": "toolUse", "usage": {"totalTokens": 2}}}))
    result = {"paths": ["keep.txt"], "checks_run": [], "summary": "fake local", "blockers": []}
    print(json.dumps({"type": "message_end", "message": {"role": "assistant", "provider": "vllm", "model": "test-local",
        "content": [{"type": "text", "text": json.dumps(result)}], "stopReason": "stop", "usage": {"totalTokens": 3}}}))
    transcript = [
        {"type": "model_change", "model": "vllm/test-local", "resolvedModelIsFallback": False},
        {"type": "thinking_level_change", "thinkingLevel": "medium"},
        {"type": "message", "message": {"role": "assistant", "provider": "vllm", "model": "test-local",
         "content": [{"type": "toolCall", "name": "read", "arguments": {}}]}},
        {"type": "message", "message": {"role": "assistant", "provider": "vllm", "model": "test-local",
         "content": [{"type": "text", "text": json.dumps(result)}]}}]
    transcript_path = folder / ("2026-11-07_" + session + ".jsonl")
    if mode == "fifo-transcript":
        os.mkfifo(transcript_path)
    else:
        transcript_path.write_text("".join(json.dumps(r) + "\n" for r in transcript))
    sys.exit(0)
thread = "11111111-2222-3333-4444-555555555555"
print(json.dumps({"type": "thread.started", "thread_id": thread}), flush=True)
print(json.dumps({"type": "env_check", "stripped": not any(check.values())}), flush=True)
cwd = pathlib.Path(args[args.index("-C") + 1])
model = args[args.index("-m") + 1]
effort = next(a.split("=", 1)[1].strip('"') for a in args if a.startswith("model_reasoning_effort="))
sandbox = args[args.index("-s") + 1]
network = "sandbox_workspace_write.network_access=true" in args
if mode == "edit":
    (cwd / "delete.txt").unlink()
    (cwd / "keep.txt").write_text("worker\n")
    (cwd / "untracked.txt").write_text("new file\n")
    (cwd / "new.bin").write_bytes(b"\x00new\xff")
    (cwd / "worker.ignored").write_text("ignored worker output")
    (cwd / "blob.bin").write_bytes(b"\x00changed\xff")
    index = pathlib.Path(subprocess_output := __import__('subprocess').check_output(["git", "-C", str(cwd), "rev-parse", "--git-path", "index"]).decode().strip())
    if not index.is_absolute(): index = cwd / index
    pathlib.Path(os.environ["FAKE_INDEX"]).write_bytes(index.read_bytes())
context = {"type": "turn_context", "payload": {"model": model, "effort": effort, "sandbox_policy": {"type": sandbox, "network_access": network}}}
if sandbox == "workspace-write":
    context["payload"]["sandbox_policy"].update({
        flag: ("sandbox_workspace_write." + flag + "=true") in args
        for flag in ("exclude_slash_tmp", "exclude_tmpdir_env_var")})
    context["payload"]["sandbox_policy"]["writable_roots"] = [str(cwd), os.environ["TMPDIR"]] if "TMPDIR" in os.environ else [str(cwd)]
if mode == "missing-tmp-flags":
    context["payload"]["sandbox_policy"].pop("exclude_slash_tmp", None)
    context["payload"]["sandbox_policy"].pop("exclude_tmpdir_env_var", None)
if mode == "tmp-policy":
    context["payload"]["sandbox_policy"].update(exclude_slash_tmp=True, exclude_tmpdir_env_var=False)
records = [context]
if mode == "wrong-turn":
    records.append({"type": "turn_context", "payload": {"model": "wrong-model", "effort": "low", "sandbox_policy": {"type": sandbox}}})
if mode == "spawn":
    records.append({"type": "response_item", "payload": {"type": "agent_message", "content": [{"type": "input_text", "text": "Message Type: NEW_TASK\nchild"}]}})
if mode == "mcp":
    records.append({"type": "response_item", "payload": {"type": "function_call", "name": "mcp__server__tool", "arguments": "{}"}})
records.append({"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": {"input_tokens": 7}}, "rate_limits": {"secondary": {"window_minutes": 10080, "used_percent": 12, "resets_at": time.time() + 1000}}}})
rollout = pathlib.Path(os.environ["CODEX_HOME"]) / "sessions/2026/11/07" / ("rollout-2026-11-07T00-00-00-" + thread + ".jsonl")
rollout.parent.mkdir(parents=True, exist_ok=True)
if mode == "fifo-transcript":
    (cwd / "keep.txt").write_text("partial FIFO worker edit\n")
    os.mkfifo(rollout)
else:
    rollout.write_text("".join(json.dumps(r) + "\n" for r in records))
if mode in {"sparse-transcript", "huge-line"}:
    (cwd / "keep.txt").write_text("partial oversized worker edit\n")
    with rollout.open("ab") as output:
        output.truncate(1 << 40 if mode == "sparse-transcript" else 17 * 1024 * 1024)
result = {"paths": [], "checks_run": [], "summary": "fake worker", "blockers": ["blocked"] if mode == "blockers" else []}
if "Candidate: " in prompt:
    candidate = prompt.split("Candidate: ")[1].splitlines()[0]
    result = {"verdict": "PASS", "candidate": candidate, "findings": [], "missing_evidence": [], "summary": "synthetic audit"}
if mode == "turn-failed":
    print(json.dumps({"type": "turn.failed", "error": {"message": "invalid_json_schema: provider detail"}}))
    sys.exit(1)
if mode == "swap-ancestor":
    # Resolve the FD-backed output path first, so the fake can find the run's
    # original display path while still writing its result through the fd.
    output = pathlib.Path(args[args.index("-o") + 1])
    run = output.resolve().parent.parent
    state = run.parent
    state.rename(state.with_name(state.name + "-moved"))
    state.mkdir()
    (state / run.name).symlink_to(os.environ["FAKE_CALLER"])
pathlib.Path(args[args.index("-o") + 1]).write_text(json.dumps(result))
if mode == "sparse-result":
    (cwd / "keep.txt").write_text("partial oversized worker edit\n")
    with pathlib.Path(args[args.index("-o") + 1]).open("ab") as output:
        output.truncate(1 << 40)
'''


@pytest.fixture
def environment(tmp_path):
    fake = tmp_path / "bin"
    fake.mkdir()
    for name in ("codex", "claude", "omp-local"):
        path = fake / name
        path.write_text(FAKE_CLI)
        path.chmod(0o755)
    env = dict(os.environ)
    env.update(PATH=str(fake) + os.pathsep + env["PATH"], AGENT_RUN_HOME=str(tmp_path / "runs"),
               AGENT_RUN_WORKTREE_ROOT=str(tmp_path / "worktrees"), CODEX_HOME=str(tmp_path / "codex"),
               CLAUDE_CONFIG_DIR=str(tmp_path / "claude"), AGENT_QUOTA_HOME=str(tmp_path / "quota"),
               FAKE_CALLED=str(tmp_path / "called.json"), FAKE_ENV=str(tmp_path / "env.json"),
               FAKE_INDEX=str(tmp_path / "index.snapshot"), HERDR_ENV="1", HERDR_PANE_ID="director",
               HERDR_SOCKET_PATH="/tmp/fake-herdr", ANTHROPIC_API_KEY="test-not-a-key", CLAUDECODE="1",
               CLAUDE_CODE_SESSION_ID="parent-session", PI_SESSION_FILE="parent-omp", OPENAI_API_KEY="test-not-a-key",
               OMPCODE="1", CODEX_THREAD_ID="parent-thread")
    env["AGENT_RUN_TMP_ROOTS"] = str(tmp_path / "not-the-caller")
    env.pop("AGENT_LOCAL_ONLY", None)
    brief = tmp_path / "brief.md"
    brief.write_text("Stay in scope. Return the result.\n")
    return env, brief


def invoke(environment, *args, timeout=15):
    env, _ = environment
    return subprocess.run([sys.executable, str(RUN), *map(str, args)], env=env, capture_output=True,
                          text=True, timeout=timeout)


def last_run(environment):
    env, _ = environment
    paths = list(Path(env["AGENT_RUN_HOME"]).glob("*/meta.json"))
    assert len(paths) == 1
    return paths[0].parent, json.loads(paths[0].read_text())


def test_patch_has_untracked_deleted_binary_and_preserves_both_indexes(repo, environment):
    env, brief = environment
    (repo / "keep.txt").write_text("user staged\n")
    git(repo, "add", "keep.txt")
    original_index = (repo / ".git/index").read_bytes()
    env["FAKE_MODE"] = "edit"
    p = invoke(environment, "sol", "--brief", brief, "--repo", repo)
    assert p.returncode == 0, p.stdout + p.stderr
    run, meta = last_run(environment)
    patch = (run / "result.patch").read_bytes()
    assert b"deleted file mode" in patch
    assert b"GIT binary patch" in patch
    for name in ("delete.txt", "untracked.txt", "blob.bin", "new.bin"):
        assert name.encode() in patch
        assert name in meta["changed_paths"]
    assert b"user staged" not in patch
    assert (repo / ".git/index").read_bytes() == original_index
    worktree = Path(meta["worktree"])
    index = Path(git(worktree, "rev-parse", "--git-path", "index").decode().strip())
    assert index.read_bytes() == Path(env["FAKE_INDEX"]).read_bytes()
    assert meta["base"] == git(repo, "rev-parse", "HEAD").decode().strip()
    assert meta["parent"] == {"harness": "claude", "session_id": "parent-session"}
    assert not any(json.loads(Path(env["FAKE_ENV"]).read_text()).values())
    starts_ends = [json.loads(line) for line in (run.parent / "index.jsonl").read_text().splitlines()]
    assert [r["state"] for r in starts_ends] == ["running", "ok"]
    assert starts_ends[-1]["child_session_id"] == meta["child"]["session_id"]
    assert invoke(environment, "gc", meta["run"]).returncode == 0
    assert not worktree.exists() and run.is_dir()


@pytest.mark.parametrize("mode, field", [("wrong-turn", "model_ok"), ("spawn", "spawned_subagents"), ("mcp", "mcp_calls")])
def test_rollout_verifies_every_turn_and_disallows_delegation(repo, environment, mode, field):
    env, brief = environment
    env["FAKE_MODE"] = mode
    p = invoke(environment, "ask", "--model", "sol", "--brief", brief, "--repo", repo)
    assert p.returncode == 1, p.stdout + p.stderr
    _, meta = last_run(environment)
    assert meta["state"] == "unverified"
    if mode == "wrong-turn":
        assert meta["verification"][field] is False
        assert meta["verification"]["effort_ok"] is False
    else:
        assert meta["verification"][field] > 0
    assert meta["verification"]["issues"]
    assert meta["tokens"] == {"input_tokens": 7}


def test_slot_exhaustion_returns_75_without_starting_child(environment):
    env, brief = environment
    root = Path(env["AGENT_RUN_HOME"])
    locks = [runner.acquire_slot(root) for _ in range(3)]
    try:
        start = time.monotonic()
        p = invoke(environment, "ask", "--model", "luna", "--brief", brief)
        assert p.returncode == 75
        assert time.monotonic() - start < 2
        assert not Path(env["FAKE_CALLED"]).exists()
        assert not list(root.glob("*/meta.json"))
    finally:
        for lock in locks:
            lock.close()
    # The local pool is independent and has four slots.
    local = [runner.acquire_slot(root, True) for _ in range(4)]
    try:
        assert all(local)
        assert runner.acquire_slot(root, True) is None
        with runner.acquire_slot(root):
            pass
    finally:
        for lock in local:
            lock.close()


def test_local_only_refuses_cloud_before_child_or_run(environment):
    env, brief = environment
    env["AGENT_LOCAL_ONLY"] = "1"
    p = invoke(environment, "ask", "--model", "luna", "--brief", brief)
    assert p.returncode == 3
    assert "AGENT_LOCAL_ONLY" in p.stderr
    assert not Path(env["FAKE_CALLED"]).exists()
    assert invoke(environment, "list").returncode == 0


@pytest.mark.parametrize("model", ["opus", "fable"])
def test_claude_subscription_env_and_persisted_transcript(environment, model):
    env, brief = environment
    p = invoke(environment, "ask", "--model", model, "--brief", brief)
    assert p.returncode == 0, p.stdout + p.stderr
    _, meta = last_run(environment)
    assert not any(json.loads(Path(env["FAKE_ENV"]).read_text()).values())
    assert meta["model"] == f"claude-{model}-5-5"
    assert Path(meta["child"]["transcript_path"]).is_file()
    args = json.loads(Path(env["FAKE_CALLED"]).read_text())["args"]
    assert "--safe-mode" in args and "--bare" not in args
    assert "--no-session-persistence" not in args


def test_audit_receipt_matches_publish_jq_predicate(repo, environment):
    env, _ = environment
    candidate = git(repo, "rev-parse", "HEAD").decode().strip()
    packet = repo.parent / "packet.md"
    packet.write_text(f"Audited-Range: {candidate}..{candidate}\nContract and synthetic evidence\n")
    p = invoke(environment, "audit", "--packet", packet, "--candidate", candidate, "--repo", repo)
    assert p.returncode == 0, p.stdout + p.stderr
    run, meta = last_run(environment)
    source = (BIN / "executable_decent-angl-sync").read_text()
    predicate = re.search(r"jq -e '(type == \"object\" and \.accepted.*?packet_sha256.*?)'", source, re.S).group(1)
    checked = subprocess.run(["jq", "-e", predicate, str(run / "result.json")], capture_output=True, text=True)
    assert checked.returncode == 0, checked.stderr
    result = json.loads((run / "result.json").read_text())
    assert result["packet_sha256"] == runner.hashlib.sha256(packet.read_bytes()).hexdigest()
    assert result["candidate"] == candidate and result["release"] is True
    assert meta["verification"]["sandbox_ok"] is True
    assert not (run / "tree/keep.txt").stat().st_mode & 0o222
    assert not (run / "packet.md").stat().st_mode & 0o222


@pytest.mark.parametrize("change", ["candidate", "findings", "missing", "packet", "block"])
def test_audit_fails_closed_on_inconsistency(tmp_path, change):
    candidate = "a" * 40
    packet = tmp_path / "packet"
    packet.write_text("evidence")
    digest = runner.hashlib.sha256(packet.read_bytes()).hexdigest()
    result = {"verdict": "PASS", "candidate": candidate, "findings": [], "missing_evidence": [], "summary": "ok"}
    if change == "candidate":
        result["candidate"] = "b" * 40
    elif change == "findings":
        result["findings"] = [{"severity": "major", "location": "a.py:1", "claim": "bad", "counterexample": "input"}]
    elif change == "missing":
        result["missing_evidence"] = ["required check"]
    elif change == "packet":
        packet.write_text("changed")
    else:
        result["verdict"] = "BLOCK"
    verification = runner.blank_verification()
    receipt = runner.audit_receipt(result, candidate, digest, "run", verification, packet, True)
    assert receipt["accepted"] is False
    assert verification["issues"]


def test_audit_requires_positive_attestation(tmp_path):
    packet = tmp_path / "packet"
    packet.write_text("evidence")
    digest = runner.hashlib.sha256(packet.read_bytes()).hexdigest()
    result = {"verdict": "PASS", "candidate": "a" * 40, "findings": [], "missing_evidence": [], "summary": "ok"}
    verification = runner.blank_verification()
    receipt = runner.audit_receipt(result, "a" * 40, digest, "run", verification, packet, True)
    assert receipt["accepted"] is False


def test_timeout_keeps_partial_patch_and_releases_slot(repo, environment):
    env, brief = environment
    env["FAKE_MODE"] = "sleep"
    p = invoke(environment, "sol", "--brief", brief, "--repo", repo, "--timeout", "0.3")
    assert p.returncode == 1
    run, meta = last_run(environment)
    assert meta["state"] == "timeout"
    assert (run / "result.patch").exists()
    assert meta["ended_at"] is not None
    lock = runner.acquire_slot(Path(env["AGENT_RUN_HOME"]))
    assert lock is not None
    lock.close()


def test_setup_failure_still_snapshots_patch(repo, environment):
    env, brief = environment
    p = invoke(environment, "sol", "--brief", brief, "--repo", repo,
               "--setup", "printf 'from setup\\n' > new.txt; exit 9")
    assert p.returncode == 1
    run, meta = last_run(environment)
    assert meta["state"] == "failed" and meta["exit_code"] == 9
    assert b"new.txt" in (run / "result.patch").read_bytes()
    assert not Path(env["FAKE_CALLED"]).exists()


@pytest.mark.parametrize("method", ["command", "signal"])
def test_cancel_preserves_patch_and_marks_cancelled(repo, environment, method):
    env, brief = environment
    env["FAKE_MODE"] = "sleep"
    proc = subprocess.Popen([sys.executable, str(RUN), "sol", "--brief", str(brief), "--repo", str(repo)],
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 5
        while not Path(env["FAKE_CALLED"]).exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert Path(env["FAKE_CALLED"]).exists()
        run, meta = last_run(environment)
        if method == "command":
            cancelled = invoke(environment, "cancel", meta["run"])
            assert cancelled.returncode == 0, cancelled.stderr
        else:
            proc.send_signal(signal.SIGTERM)
        stdout, stderr = proc.communicate(timeout=12)
        assert proc.returncode == 1, stdout + stderr
        meta = json.loads((run / "meta.json").read_text())
        assert meta["state"] == "cancelled"
        assert (run / "result.patch").exists()
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.communicate(timeout=12)


def test_local_missing_profile_refuses_without_dispatch(repo, environment):
    env, brief = environment
    env["HOME"] = str(brief.parent)
    p = invoke(environment, "local", "--brief", brief, "--repo", repo)
    assert p.returncode == 1
    _, meta = last_run(environment)
    assert meta["state"] == "failed"
    assert "local vLLM endpoint/model absent" in meta["error"]
    assert not Path(env["FAKE_CALLED"]).exists()


@pytest.mark.parametrize("director_activity", [False, True])
def test_local_edit_isolated_with_patch_final_json_and_transcript(repo, environment, monkeypatch, director_activity):
    env, brief = environment
    import shutil
    if not shutil.which("bwrap"):
        pytest.skip("bwrap unavailable")
    # Private /tmp deliberately hides sibling fixtures. Put the fake binary
    # and its receipts inside the explicitly writable cache instead.
    cache = brief.parent / ".cache"
    cache.mkdir()
    fake_bin = cache / "bin"
    shutil.copytree(Path(env["FAKE_CALLED"]).parent / "bin", fake_bin)
    env.update(HOME=str(brief.parent), PATH=str(fake_bin) + os.pathsep + os.environ["PATH"],
               FAKE_CALLED=str(cache / "called.json"), FAKE_ENV=str(cache / "env.json"))
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("AGENT_LOCAL_ONLY", "1")
    monkeypatch.setattr(runner, "local_configuration", lambda: "test-local")
    original_head = git(repo, "rev-parse", "HEAD").decode().strip()
    if director_activity:
        execute = runner.execute

        def concurrent_director(*args, **kwargs):
            outcome = execute(*args, **kwargs)
            (repo / "director.txt").write_text("concurrent director change")
            git(repo, "add", "director.txt")
            git(repo, "commit", "-qm", "director")
            git(repo, "status", "--short")
            return outcome

        monkeypatch.setattr(runner, "execute", concurrent_director)
    assert runner.main(["local", "--brief", str(brief), "--repo", str(repo), "--base", "HEAD",
                        "--name", "local-edit"]) == 0
    run, meta = last_run(environment)
    assert meta["model"] == "test-local"
    assert meta["state"] == "ok" and meta["tokens"] == 5
    assert Path(meta["child"]["transcript_path"]).is_file()
    assert json.loads((run / "result.json").read_text())["summary"] == "fake local"
    args = json.loads((run / "child/called.json").read_text())["args"]
    assert args[args.index("--model") + 1] == "vllm/test-local"
    assert args[args.index("--thinking") + 1] == "medium"
    assert all(meta["verification"][key] is True for key in ("model_ok", "effort_ok", "sandbox_ok"))
    assert "--no-extensions" in args and "--no-title" in args
    worktree = Path(meta["worktree"])
    assert worktree != repo and worktree.parent == Path(env["AGENT_RUN_WORKTREE_ROOT"])
    assert meta["run"].endswith("-local-local-edit")
    assert meta["base"] == original_head
    assert (repo / "keep.txt").read_text() == "original\n"
    assert (worktree / "keep.txt").read_text() == "local worker edit\n"
    assert b"+local worker edit" in (run / "result.patch").read_bytes()
    assert meta["changed_paths"] == ["keep.txt"] and "keep.txt" in meta["diffstat"]
    assert runner.main(["gc", meta["run"]]) == 0
    assert not worktree.exists() and (run / "result.patch").is_file()


def test_local_requires_repo(environment):
    _, brief = environment
    p = invoke(environment, "local", "--brief", brief)
    assert p.returncode == 2 and "--repo" in p.stderr


def test_nonrepo_consult_json_output_and_network_default(environment, monkeypatch):
    env, brief = environment
    monkeypatch.chdir(brief.parent)
    p = invoke(environment, "ask", "--model", "luna", "--name", "demo-sol-r1", "--brief", brief, "--json")
    assert p.returncode == 0, p.stdout + p.stderr
    output = json.loads(p.stdout)
    assert output["meta"]["network"] is False
    assert output["meta"]["state"] == "ok"
    assert output["meta"]["run"].endswith("-ask-demo-sol-r1")
    args = json.loads(Path(env["FAKE_CALLED"]).read_text())["args"]
    assert "--skip-git-repo-check" in args
    assert "sandbox_workspace_write.network_access=true" not in args


def test_sandbox_and_network_checked_in_later_turn(tmp_path):
    path = tmp_path / "rollout.jsonl"
    contexts = [
        {"type": "turn_context", "payload": {"model": "sol", "effort": "high",
                                            "sandbox_policy": {"type": "workspace-write", "network_access": False,
                                                               "exclude_slash_tmp": True, "exclude_tmpdir_env_var": True}}},
        {"type": "turn_context", "payload": {"model": "sol", "effort": "high",
                                            "sandbox_policy": {"type": "workspace-write", "network_access": True,
                                                               "exclude_slash_tmp": True, "exclude_tmpdir_env_var": True}}},
    ]
    path.write_text("".join(json.dumps(r) + "\n" for r in contexts))
    verification, _, _ = runner.verify_rollout(path, "sol", "high", "workspace-write", False)
    assert verification["sandbox_ok"] is False
    assert verification["issues"]


def test_quota_missing_stale_and_reset(tmp_path):
    now = 2_000_000_000
    assert quota.claude_snapshot(tmp_path, now)["five_hour"] is None
    assert quota.codex_snapshot(tmp_path, now)["seven_day"] is None
    assert quota.stale(now - 6 * 3600 - 1, now + 10, now)
    assert quota.stale(now - 10, now - 1, now)
    assert not quota.stale(now - 10, now + 1, now)
    (tmp_path / "claude.json").write_text(json.dumps({"captured_at": now - 1, "rate_limits": {
        "five_hour": {"used_percentage": 25, "resets_at": now + 1},
        "seven_day": {"used_percentage": 40, "resets_at": now + 1}}}))
    snapshot = quota.claude_snapshot(tmp_path, now)
    assert snapshot["five_hour"] == 75 and snapshot["seven_day"] == 60
    assert snapshot["stale"] is False
    sessions = tmp_path / "sessions/2026/11/07"
    sessions.mkdir(parents=True)
    path = sessions / "rollout-test.jsonl"
    path.write_text(json.dumps({"type": "event_msg", "timestamp": now - 7 * 3600, "payload": {
        "type": "token_count", "rate_limits": {
            "primary": {"window_minutes": 300, "used_percent": 99},
            "secondary": {"window_minutes": 10080, "used_percent": 12, "resets_at": now + 100}}}}) + "\n")
    snapshot = quota.codex_snapshot(tmp_path, now)
    assert snapshot["seven_day"] == 88 and snapshot["stale"] is True


def test_quota_scans_at_most_twenty_newest_files(tmp_path):
    sessions = tmp_path / "sessions/2026/11/07"
    sessions.mkdir(parents=True)
    for i in range(21):
        path = sessions / f"rollout-{i}.jsonl"
        path.write_text(json.dumps({"type": "event_msg", "payload": {"type": "token_count", "rate_limits": {
            "primary": {"window_minutes": 10080, "used_percent": 20}}}}) + "\n" if i == 0 else "{}\n")
        os.utime(path, (1000 + i, 1000 + i))
    assert quota.codex_snapshot(tmp_path, 1100)["seven_day"] is None


def test_statusline_snapshot_omission_and_bad_input(environment):
    env, _ = environment
    data = {"model": {"display_name": "Opus 5.5"}, "workspace": {"current_dir": "/tmp/project"},
            "session_id": "test", "rate_limits": {"five_hour": {"used_percentage": 25}, "seven_day": {"used_percentage": 40}}}
    p = subprocess.run([sys.executable, str(STATUS)], input=json.dumps(data), env=env, capture_output=True, text=True)
    assert p.returncode == 0
    path = Path(env["AGENT_QUOTA_HOME"]) / "claude.json"
    previous = path.read_bytes()
    for value in ('{"model":{"display_name":"Opus"}}', "invalid"):
        p = subprocess.run([sys.executable, str(STATUS)], input=value, env=env, capture_output=True, text=True)
        assert p.returncode == 0
        assert path.read_bytes() == previous
    p = subprocess.run([sys.executable, str(QUOTA)], env=env, capture_output=True, text=True)
    assert p.returncode == 0
    assert p.stdout.strip() == "claude 5h 75% 7d 60% | codex 7d unknown remaining"


def test_validator_rejects_extra_keys_and_invalid_custom_schema():
    with pytest.raises(ValueError):
        runner.validate({"paths": [], "checks_run": [], "summary": "ok", "blockers": [], "extra": 1}, runner.RESULT_SCHEMA)
    runner.validate({"count": 1}, {"type": "object", "properties": {"count": {"type": "integer", "minimum": 0}}, "required": ["count"], "additionalProperties": False})
    with pytest.raises(ValueError, match="unsupported schema"):
        runner.validate("x", {"type": "string", "format": "email"})


def write_records(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record) + "\n" for record in records))


@pytest.mark.parametrize("bad", ["missing", "empty", "zero", "later-model", "Task", "mcp__x", None])
def test_claude_transcript_is_authority(tmp_path, monkeypatch, bad):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude"))
    run = tmp_path / "run"
    run.mkdir()
    model = "claude-opus-5-5"
    transcript = tmp_path / "claude/projects/test/session.jsonl"
    records = [{"type": "assistant", "message": {"model": model, "content": [
        {"type": "tool_use", "name": "Read", "input": {"file_path": "packet.md"}}]}}]
    records[:0] = [
        {"type": "api-request", "params": {"model": model, "output_config": {"effort": "high"}}},
        {"type": "attachment", "attachment": {"type": "prompt_snapshot", "tools": [{"name": "Read"}]}}]
    if bad == "later-model":
        records.append({"type": "assistant", "message": {"model": "wrong", "content": []}})
    elif bad in {"Task", "mcp__x"}:
        records[-1]["message"]["content"][0]["name"] = bad
    elif bad == "empty":
        records = []
    elif bad == "zero":
        records = [{}]
    if bad != "missing":
        write_records(transcript, records)
    (run / "events.jsonl").write_text(json.dumps({
        "is_error": False, "session_id": "session", "modelUsage": {model: {}},
        "structured_output": {"summary": "ok"}}))
    meta = {"model": model, "effort": "high", "child": {}, "schema": True}
    verification = runner.verify_claude(run, meta, tmp_path)
    assert bool(verification["issues"]) == (bad is not None)
    assert verification["effort_ok"] == (bad not in {"missing", "empty", "zero"})
    assert verification["sandbox_ok"] == (bad not in {"Task", "mcp__x", "missing", "empty", "zero"})
    assert verification["tools_ok"] == (bad not in {"Task", "mcp__x", "missing", "empty", "zero"})


@pytest.mark.parametrize("name,args,bad", [
    ("exec_command", '{"cmd":"rg mcp__mac"}', False),
    ("apply_patch", "*** Add File: a.py\n+def spawn_agent(): pass", False),
    ("spawn_agent", "{}", True), ("mcp__x", "{}", True),
    ("exec", "tools.spawn_agent({})", True), ("exec", "tools.mcp__x({})", True),
    ("exec", "await tools['spawn_agent']({})", True), ("exec", 'tools["mcp__x"]({})', True),
    ("exec", "const f = tools?.spawn_agent; await f({})", True),
])
def test_rollout_dispatch_not_argument_mentions(tmp_path, name, args, bad):
    path = tmp_path / "rollout"
    write_records(path, [
        {"type": "turn_context", "payload": {"model": "model", "effort": "high",
         "sandbox_policy": {"type": "workspace-write", "writable_roots": [], "network_access": False,
                            "exclude_slash_tmp": True, "exclude_tmpdir_env_var": True}}},
        {"type": "response_item", "payload": {"type": "function_call", "name": name, "arguments": args}}])
    verification, _, _ = runner.verify_rollout(path, "model", "high", "workspace-write", False)
    assert bool(verification["issues"]) == bad


def test_codex_rejects_external_writable_root(tmp_path):
    path = tmp_path / "rollout"
    write_records(path, [{"type": "turn_context", "payload": {"model": "m", "effort": "high",
        "sandbox_policy": {"type": "workspace-write", "writable_roots": [str(tmp_path / "caller")],
                           "exclude_slash_tmp": True, "exclude_tmpdir_env_var": True}}}])
    verification, _, _ = runner.verify_rollout(path, "m", "high", "workspace-write", False)
    assert verification["sandbox_ok"] is False


def test_nonstrict_schema_rejected_before_run(environment):
    env, brief = environment
    schema = brief.parent / "schema.json"
    schema.write_text('{"type":"object","properties":{"x":{"type":"string"}}}')
    p = invoke(environment, "ask", "--model", "luna", "--brief", brief, "--schema", schema)
    assert p.returncode == 2
    assert "strict" in p.stderr and "additionalProperties" in p.stderr
    assert not list(Path(env["AGENT_RUN_HOME"]).glob("*/meta.json"))


def test_council_schemas_are_strict():
    text = (ROOT / "home/dot_local/share/decent-angl/skills/council/SKILL.md").read_text()
    schemas = [json.loads(s) for s in re.findall(r'(?<![^\s`])(\{"type":"object".*?\})(?=`|\n)', text)]
    assert len(schemas) == 2
    for schema in schemas:
        runner.strict_schema(schema)


@pytest.mark.parametrize("model", ["luna", "opus"])
def test_ask_add_dir_and_packet_access(environment, model):
    env, brief = environment
    extra = brief.parent / "extra"
    extra.mkdir()
    p = invoke(environment, "ask", "--model", model, "--brief", brief, "--add-dir", extra)
    assert p.returncode == 0, p.stdout + p.stderr
    called = json.loads(Path(env["FAKE_CALLED"]).read_text())
    args = called["args"]
    assert str(extra) in [args[i + 1] for i, arg in enumerate(args) if arg == "--add-dir"]
    if model == "opus":
        assert str(brief.parent) in args
        assert args[args.index("--allowedTools") + 1] == "Read,Grep,Glob,WebSearch,WebFetch"
        assert "No network unless" not in called["prompt"]
    else:
        assert "--ignore-user-config" in args and "--ignore-rules" in args


def test_codex_failure_message_survives(environment):
    env, brief = environment
    env["FAKE_MODE"] = "turn-failed"
    p = invoke(environment, "ask", "--model", "luna", "--brief", brief)
    assert p.returncode == 1
    _, meta = last_run(environment)
    assert "invalid_json_schema: provider detail" in meta["error"]


@pytest.mark.parametrize("holder", [False, True])
def test_abandoned_lock_and_gc(repo, environment, holder):
    env, brief = environment
    p = invoke(environment, "sol", "--repo", repo, "--brief", brief)
    assert p.returncode == 0, p.stdout + p.stderr
    run, meta = last_run(environment)
    meta.update(state="running", ended_at=None, pid=None, pgid=None)
    runner.atomic_json(run / "meta.json", meta)
    with (run / "runner.lock").open("a+") as lock:
        if holder:
            runner.fcntl.flock(lock, runner.fcntl.LOCK_EX)
        shown = invoke(environment, "show", meta["run"], "--json")
        assert json.loads(shown.stdout)["meta"]["state"] == ("running" if holder else "abandoned")
        gc = invoke(environment, "gc", meta["run"])
        assert gc.returncode == (1 if holder else 0)
    assert Path(meta["worktree"]).exists() == holder


def test_gc_prunes_audit_copy(repo, environment):
    _, brief = environment
    candidate = git(repo, "rev-parse", "HEAD").decode().strip()
    brief.write_text(f"Audited-Range: {candidate}..{candidate}\n")
    p = invoke(environment, "audit", "--packet", brief, "--repo", repo, "--candidate", candidate)
    assert p.returncode == 0, p.stdout + p.stderr
    run, meta = last_run(environment)
    assert invoke(environment, "gc", meta["run"]).returncode == 0
    assert not (run / "tree").exists()
    assert (run / "result.json").exists()


def test_setup_baseline_and_new_ignored_files(repo, environment):
    env, brief = environment
    (repo / ".gitignore").write_text("*.ignored\n")
    git(repo, "add", ".gitignore")
    git(repo, "commit", "-qm", "ignore fixture")
    env["FAKE_MODE"] = "edit"
    p = invoke(environment, "sol", "--brief", brief, "--repo", repo,
               "--setup", "printf setup > setup.txt; printf baseline > setup.ignored")
    assert p.returncode == 0, p.stdout + p.stderr
    run, meta = last_run(environment)
    assert b"setup.txt" in (run / "result.patch").read_bytes()
    assert meta["setup_changed_paths"] == ["setup.txt"]
    assert meta["ignored_new_files"] == ["worker.ignored"]


def test_quota_explicit_no_snapshot(environment):
    env, _ = environment
    p = subprocess.run([sys.executable, str(QUOTA)], env=env, capture_output=True, text=True)
    assert p.returncode == 0
    assert p.stdout.startswith("claude no-snapshot |")


def test_real_local_bwrap_isolation(repo, environment, tmp_path, monkeypatch):
    import shutil
    if not shutil.which("bwrap"):
        pytest.skip("bwrap unavailable")
    env, _ = environment
    home = tmp_path / "home"
    agent = home / ".omp/profiles/local/agent"
    agent.mkdir(parents=True)
    (agent / "config.yml").write_text("profile: local\n")
    (home / ".omp/agent").mkdir()
    (home / ".omp/agent/config.yml").write_text("profile: default\n")
    (agent / "skills").symlink_to(home / ".omp/agent")
    monkeypatch.setenv("HOME", str(home))
    worktree = Path(env["AGENT_RUN_WORKTREE_ROOT"]) / "sandbox"
    worktree.parent.mkdir()
    git(repo, "worktree", "add", "--detach", str(worktree), "HEAD")
    run = Path(env["AGENT_RUN_HOME"]) / "sandbox"
    run.mkdir(parents=True)
    # Pass every path through a symlinked parent, as ~/src -> /srv on nous.
    linked = tmp_path / "linked"
    linked.symlink_to(tmp_path)
    command = runner.local_sandbox(*(linked / p.relative_to(tmp_path) for p in (worktree, run, repo)))
    def git_snapshot():
        return {
            "head": git(repo, "rev-parse", "HEAD"),
            "refs": git(repo, "for-each-ref", "--format=%(refname) %(objectname)"),
            "caller_index": (repo / ".git/index").read_bytes(),
            "worktree_index": Path(git(worktree, "rev-parse", "--git-path", "index").decode().strip()).read_bytes()}
    before = git_snapshot()
    profile_before = runner.profile_snapshot()
    fake = run / "child.py"
    fake.write_text(
        "import pathlib, subprocess, sys\n"
        f"denied = [pathlib.Path({str(repo)!r}) / 'keep.txt', pathlib.Path({str(agent)!r}) / 'config.yml',\n"
        f"          pathlib.Path({str(home)!r}) / '.omp/agent/config.yml']\n"
        "for path in denied:\n"
        " try: path.write_text('bad')\n"
        " except OSError: pass\n"
        " else: sys.exit('wrote ' + str(path))\n"
        f"pathlib.Path({str(agent)!r}, 'agent.db').write_text('state')\n"
        "pathlib.Path('new.txt').write_text('good')\n"
        "assert subprocess.run(['git', 'add', 'new.txt'], capture_output=True).returncode != 0\n")
    probe = subprocess.run(command + ["true"], capture_output=True, text=True)
    if probe.returncode:
        pytest.fail("real bwrap probe failed: " + probe.stderr)
    child = subprocess.run(command + [sys.executable, str(fake)], cwd=worktree, env=runner.child_env(env),
                           capture_output=True, text=True)
    assert child.returncode == 0, child.stderr
    assert (worktree / "new.txt").read_text() == "good"
    assert not (agent / "agent.db").exists()  # Runtime profile writes are private.
    assert git_snapshot() == before
    assert runner.profile_snapshot() == profile_before
    (agent / "skills").unlink()
    (agent / "skills").symlink_to(tmp_path)
    assert runner.profile_snapshot() != profile_before


@pytest.mark.parametrize("bad", ["missing", "empty", "wrong-model", "task", None])
def test_local_transcript_model_tools_and_sandbox(tmp_path, bad):
    run = tmp_path
    model = "local-model"
    result = {"paths": [], "checks_run": [], "summary": "ok", "blockers": []}
    message = {"role": "assistant", "provider": "vllm", "model": model,
               "content": [{"type": "text", "text": json.dumps(result)}], "stopReason": "stop"}
    records = [
        {"type": "model_change", "model": "vllm/" + model, "resolvedModelIsFallback": False},
        {"type": "thinking_level_change", "thinkingLevel": "medium"},
        {"type": "message", "message": dict(message)}]
    if bad == "wrong-model":
        records.insert(0, {"type": "message", "message": dict(message, model="wrong")})
    elif bad == "task":
        records.insert(0, {"type": "message", "message": dict(message, content=[{"type": "toolCall", "name": "task"}])})
    elif bad == "empty":
        records = []
    if bad != "missing":
        write_records(run / "child/sessions/time_session.jsonl", records)
    write_records(run / "events.jsonl", [{"type": "session", "id": "session"},
                                       {"type": "message_end", "message": message}])
    meta = {"model": model, "effort": "medium", "sandbox": "bwrap", "sandbox_probe_ok": True,
            "sandbox_argv": ["/usr/bin/bwrap", "--ro-bind", "/", "/", "omp-local"],
            "child": {"transcript_path": None}}
    verification = runner.verify_local(run, meta)
    assert bool(verification["issues"]) == (bad is not None)
    assert verification["effort_ok"] == (bad not in {"missing", "empty"})
    assert verification["sandbox_ok"] is True


def test_long_full_council_run_name(environment):
    _, brief = environment
    name = "2026-11-08-" + "long-council-" * 4 + "astra-r10-bounce"
    p = invoke(environment, "ask", "--model", "luna", "--name", name, "--brief", brief)
    assert p.returncode == 0, p.stdout + p.stderr


@pytest.mark.parametrize("terminal", ["ok", "blockers", "failed", "timeout", "cancelled"])
def test_local_profile_integrity_preserves_failure_states(repo, environment, monkeypatch, terminal):
    env, brief = environment
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(runner, "local_configuration", lambda: "test-local")
    monkeypatch.setattr(runner, "local_sandbox", lambda *args: ["bwrap", "--ro-bind", "/", "/"])
    snapshots = iter([{"local_profile_inputs": "before"}, {"local_profile_inputs": "after"}])
    monkeypatch.setattr(runner, "profile_snapshot", lambda: next(snapshots))
    monkeypatch.setattr(runner, "verify_local", lambda *args: dict(
        model_ok=True, effort_ok=True, sandbox_ok=True, issues=[]))

    def finish(command, cwd, run, *args, **kwargs):
        runner.atomic_json(run / "result.json", {"paths": [], "checks_run": [], "summary": "ok",
                                               "blockers": ["blocked"] if terminal == "blockers" else []})
        return (1 if terminal == "failed" else 0), (terminal if terminal in {"timeout", "cancelled", "failed"} else None)

    monkeypatch.setattr(runner, "execute", finish)
    assert runner.main(["local", "--repo", str(repo), "--brief", str(brief)]) == 1
    _, meta = last_run(environment)
    assert meta["state"] == ("unverified" if terminal in {"ok", "blockers"} else terminal)
    assert any("profile integrity" in issue for issue in meta["verification"]["issues"])


@pytest.mark.parametrize("missing", [True, False])
def test_local_never_falls_back_without_bwrap(tmp_path, monkeypatch, missing):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(runner.shutil, "which", lambda _: None if missing else "/fake/bwrap")
    monkeypatch.setattr(runner, "git", lambda *args: str(tmp_path / ".git").encode())
    monkeypatch.setattr(runner.subprocess, "run",
                        lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, "", "probe denied"))
    (tmp_path / "run").mkdir()
    with pytest.raises(RuntimeError, match="refusing unsandboxed"):
        runner.local_sandbox(tmp_path / "worktree", tmp_path / "run", tmp_path / "repo")


@pytest.mark.parametrize("nested", [
    {"type": "array", "items": {"type": "object", "properties": {}}},
    {"anyOf": [{"type": "null"}, {"type": "object", "properties": {}}]},
    {"type": "object", "additionalProperties": False, "required": [], "properties": {"x": {"type": "string"}}},
])
def test_strict_schema_checks_recursive_objects(nested):
    with pytest.raises(ValueError, match="strict schema"):
        runner.strict_schema(nested)


@pytest.mark.parametrize("kind", ["mcp_tool_call", "mcp_tool_call_begin"])
def test_mcp_record_types_are_prohibited(tmp_path, kind):
    path = tmp_path / "rollout"
    write_records(path, [
        {"type": "turn_context", "payload": {"model": "m", "effort": "high",
         "sandbox_policy": {"type": "read-only"}}},
        {"type": "event_msg" if kind.endswith("begin") else "response_item", "payload": {"type": kind}}])
    verification, _, _ = runner.verify_rollout(path, "m", "high", "read-only", False)
    assert verification["mcp_calls"] > 0


def claude_attestation_fixture(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude"))
    run = tmp_path / "run"
    run.mkdir()
    model = "claude-opus-5-5"
    records = [
        {"type": "api-request", "params": {"model": model, "output_config": {"effort": "high"}}},
        {"type": "attachment", "attachment": {"type": "prompt_snapshot", "tools": [
            {"name": "Read", "schema": {}}, {"name": "StructuredOutput", "schema": {}}]}},
        {"type": "assistant", "message": {"model": model, "content": [{"type": "tool_use", "name": "Read"}]}}]
    transcript = tmp_path / "claude/projects/test/session.jsonl"
    (run / "events.jsonl").write_text(json.dumps({
        "is_error": False, "session_id": "session", "structured_output": {}}))
    return run, transcript, records, {"model": model, "effort": "high", "child": {}, "schema": True}


@pytest.mark.parametrize("bad", [None, "missing-effort", "later-effort", "missing-request",
                               "request-model", "missing-snapshot", "malformed-snapshot", "Bash", "mcp__x"])
def test_r2_claude_attestations(tmp_path, monkeypatch, bad):
    run, transcript, records, meta = claude_attestation_fixture(tmp_path, monkeypatch)
    if bad == "missing-effort":
        records[0]["params"].pop("output_config")
    elif bad == "later-effort":
        records.append({"type": "api-request", "params": {
            "model": meta["model"], "output_config": {"effort": "low"}}})
    elif bad == "request-model":
        records[0]["params"]["model"] = "wrong"
    elif bad == "missing-request":
        records.pop(0)
    elif bad == "missing-snapshot":
        records.pop(1)
    elif bad == "malformed-snapshot":
        records[1]["attachment"]["tools"] = None
    elif bad in {"Bash", "mcp__x"}:
        records[1]["attachment"]["tools"].append({"name": bad})
    # Claude emits a startup system-prompt snapshot before the snapshot that
    # actually declares tools. It is not itself tool-offer evidence.
    records.insert(0, {"type": "attachment", "attachment": {
        "type": "prompt_snapshot", "systemPrompt": [], "contextRendering": "announced"}})
    write_records(transcript, records)
    verification = runner.verify_claude(run, meta, tmp_path)
    assert all(verification[k] is True for k in ("model_ok", "effort_ok", "sandbox_ok")) == (bad is None)
    assert bool(verification["issues"]) == (bad is not None)
    assert verification["sandbox_evidence"] == "transcript-tools"


@pytest.mark.parametrize("bad", [None, "later-thinking", "missing-thinking", "fallback", "model-change",
                               "missing-model-change", "unwrapped"])
def test_r2_local_attestations(tmp_path, bad):
    message = {"role": "assistant", "provider": "vllm", "model": "local",
               "content": [{"type": "text", "text": "{}"}], "stopReason": "stop"}
    records = [
        {"type": "model_change", "model": "vllm/local", "resolvedModelIsFallback": False},
        {"type": "thinking_level_change", "thinkingLevel": "medium"},
        {"type": "message", "message": message}]
    if bad == "later-thinking":
        records.append({"type": "thinking_level_change", "thinkingLevel": "low"})
    elif bad == "missing-thinking":
        records.pop(1)
    elif bad == "fallback":
        records[0]["resolvedModelIsFallback"] = True
    elif bad == "model-change":
        records[0]["model"] = "vllm/wrong"
    elif bad == "missing-model-change":
        records.pop(0)
    write_records(tmp_path / "child/sessions/time_session.jsonl", records)
    write_records(tmp_path / "events.jsonl", [
        {"type": "session", "id": "session"}, {"type": "message_end", "message": message}])
    meta = {"model": "local", "effort": "medium", "sandbox": "bwrap", "sandbox_probe_ok": True,
            "sandbox_argv": ["/usr/bin/bwrap", "--ro-bind", "/", "/", "omp-local"],
            "child": {"transcript_path": None}}
    if bad == "unwrapped":
        meta["sandbox_argv"] = ["omp-local"]
    verification = runner.verify_local(tmp_path, meta)
    assert all(verification[k] is True for k in ("model_ok", "effort_ok", "sandbox_ok")) == (bad is None)
    assert bool(verification["issues"]) == (bad is not None)
    assert verification["sandbox_evidence"] == "runner-bwrap"


def test_r2_orphan_never_signals_unrelated_process(tmp_path):
    unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
    try:
        meta = {"state": "running", "pid": unrelated.pid, "pgid": unrelated.pid}
        runner.atomic_json(tmp_path / "meta.json", meta)
        settled = runner.settle_abandoned(tmp_path, meta)
        assert settled["state"] == "abandoned"
        # Waiting for a short timeout distinguishes alive from a just-signalled child.
        with pytest.raises(subprocess.TimeoutExpired):
            unrelated.wait(timeout=0.1)
    finally:
        if unrelated.poll() is None:
            unrelated.terminate()
        unrelated.wait(timeout=5)


def test_r2_child_inherits_runner_lock_after_runner_death(repo, environment):
    env, brief = environment
    env["FAKE_MODE"] = "sleep"
    proc = subprocess.Popen([sys.executable, str(RUN), "sol", "--repo", str(repo), "--brief", str(brief)],
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    child = None
    try:
        deadline = time.monotonic() + 5
        while not Path(env["FAKE_CALLED"]).exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert Path(env["FAKE_CALLED"]).exists()
        run, meta = last_run(environment)
        child = meta["pgid"]
        proc.kill()
        proc.wait(timeout=5)
        gc = invoke(environment, "gc", meta["run"])
        assert gc.returncode == 1 and "running" in gc.stderr
        assert json.loads((run / "meta.json").read_text())["state"] == "running"
    finally:
        if child:
            runner.kill_group(child, signal.SIGKILL, meta["child_start"])
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=5)


@pytest.mark.parametrize("lane", ["sol", "local"])
@pytest.mark.parametrize("target", ["toplevel", "common"])
def test_r2_refuses_real_tmp_repo_before_dispatch(repo, environment, lane, target):
    env, brief = environment
    env.pop("AGENT_RUN_TMP_ROOTS", None)
    if target == "common":
        # The checkout can be outside the dangerous root while its Git common
        # directory remains inside it.
        env["TMPDIR"] = str(repo / ".git")
        env["AGENT_RUN_TMP_ROOTS"] = str(repo / ".git")
    p = invoke(environment, lane, "--repo", repo, "--brief", brief)
    assert p.returncode == 2, p.stdout + p.stderr
    assert "temporary" in p.stderr
    assert not list(Path(env["AGENT_RUN_HOME"]).glob("*/meta.json"))
    assert not Path(env["AGENT_RUN_WORKTREE_ROOT"]).exists()


@pytest.mark.parametrize("code", [
    "console.log('spawn_agent(')",
    "const patch = 'def spawn_agent(';",
    "console.log('mcp__x(')",
])
def test_r2_exec_bare_text_is_not_dispatch(tmp_path, code):
    path = tmp_path / "rollout"
    write_records(path, [
        {"type": "turn_context", "payload": {"model": "m", "effort": "high",
         "sandbox_policy": {"type": "read-only"}}},
        {"type": "response_item", "payload": {"type": "function_call", "name": "exec", "arguments": code}}])
    verification, _, _ = runner.verify_rollout(path, "m", "high", "read-only", False)
    assert not verification["issues"]


def test_codex_spawn_events_are_dispatch(tmp_path):
    path = tmp_path / "rollout"
    write_records(path, [
        {"type": "turn_context", "payload": {"model": "m", "effort": "high",
         "sandbox_policy": {"type": "read-only"}}},
        {"type": "response_item", "payload": {"type": "function_call", "name": "exec",
                                              "arguments": "const {spawn_agent: s} = tools; await s({})"}},
        {"type": "event_msg", "payload": {"type": "collab_agent_spawn_begin", "call_id": "c1"}},
        {"type": "event_msg", "payload": {"type": "collab_agent_spawn_end", "call_id": "c1",
                                          "new_thread_id": "t2"}}])
    verification, _, _ = runner.verify_rollout(path, "m", "high", "read-only", False)
    assert verification["spawned_subagents"] == 1
    assert verification["issues"]


def test_r2_setup_patch_applies_to_advertised_base(repo, environment):
    env, brief = environment
    env["FAKE_MODE"] = "edit"
    p = invoke(environment, "sol", "--repo", repo, "--brief", brief,
               "--setup", "printf setup > keep.txt")
    assert p.returncode == 0, p.stdout + p.stderr
    run, meta = last_run(environment)
    fresh = repo.parent / "fresh"
    git(repo, "worktree", "add", "--detach", str(fresh), meta["base"])
    git(fresh, "apply", str(run / "result.patch"))
    assert (fresh / "keep.txt").read_text() == (Path(meta["worktree"]) / "keep.txt").read_text() == "worker\n"
    assert meta["setup_changed_paths"] == ["keep.txt"]


@pytest.mark.parametrize("action", ["list", "show"])
def test_r2_inspection_is_read_only(environment, action):
    env, _ = environment
    run = Path(env["AGENT_RUN_HOME"]) / "orphan"
    run.mkdir(parents=True)
    meta = {"state": "running", "run": "orphan", "lane": "ask", "model": "m", "verification": {"issues": []}}
    runner.atomic_json(run / "meta.json", meta)
    before = {p.relative_to(run): (p.read_bytes(), p.stat().st_mtime_ns) for p in run.iterdir()}
    p = invoke(environment, action, *(["orphan"] if action == "show" else []), "--json")
    assert p.returncode == 0, p.stderr
    displayed = json.loads(p.stdout)
    assert (displayed["meta"] if action == "show" else displayed[0])["state"] == "abandoned"
    assert {p.relative_to(run): (p.read_bytes(), p.stat().st_mtime_ns) for p in run.iterdir()} == before


@pytest.mark.parametrize("target", ["toplevel", "common", "tmp-in-toplevel", "tmp-in-common"])
def test_r2_custom_tmpdir_default_guard(monkeypatch, target):
    root = {"tmp-in-toplevel": Path("/safe/checkout/src"),
            "tmp-in-common": Path("/safe/git/tmp")}.get(target, Path("/var/agent-r2-test-tmp"))
    monkeypatch.delenv("AGENT_RUN_TMP_ROOTS", raising=False)
    monkeypatch.setenv("TMPDIR", str(root))
    paths = iter([root / "checkout" if target == "toplevel" else Path("/safe/checkout"),
                  root / "git" if target == "common" else Path("/safe/git")])
    monkeypatch.setattr(runner, "git", lambda *args: str(next(paths)).encode())
    with pytest.raises(ValueError, match="temporary root"):
        runner.refuse_temporary_repo(Path("/safe/checkout"))


def test_r2_records_codex_tmp_exclusions(environment):
    env, brief = environment
    env["FAKE_MODE"] = "tmp-policy"
    p = invoke(environment, "ask", "--model", "luna", "--brief", brief)
    assert p.returncode == 0, p.stdout + p.stderr
    _, meta = last_run(environment)
    assert meta["sandbox_policies"] == [{"exclude_slash_tmp": True, "exclude_tmpdir_env_var": False}]
    assert meta["verification"]["sandbox_evidence"] == "transcript"


@pytest.fixture
def audit_sandbox(repo, tmp_path, monkeypatch):
    import shutil
    if not shutil.which("bwrap"):
        pytest.skip("bwrap unavailable")
    home = tmp_path / "audit-home"
    cache = home / ".cache"
    cache.mkdir(parents=True)
    caller = cache / "caller"
    git(repo, "clone", "-q", str(repo), str(caller))
    (caller / "subdir").mkdir()
    agent = home / ".omp/profiles/local/agent"
    agent.mkdir(parents=True)
    (agent / "config.yml").write_text("profile: local\n")
    skills = cache / "skills"
    skills.mkdir()
    (skills / "input").write_text("original skills")
    (agent / "skills").symlink_to(skills)
    monkeypatch.setenv("HOME", str(home))
    worktree = cache / "worker"
    git(caller, "worktree", "add", "--detach", str(worktree), "HEAD")
    run = cache / "runs/audit"
    (run / "child").mkdir(parents=True)
    return caller, worktree, run, agent


def sandbox_child(sandbox, source, *, repo=None):
    caller, worktree, run, _ = sandbox
    script = run / "child/fake.py"
    script.write_text(source)
    command = runner.local_sandbox(worktree, run, repo or caller)
    result = subprocess.run(command + [sys.executable, str(script)], cwd=worktree,
                            env=runner.child_env(), capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr


def test_audit_local_cannot_plant_runner_output_symlink(audit_sandbox):
    caller, worktree, run, _ = audit_sandbox
    before = (caller / "keep.txt").read_bytes()
    sandbox_child(audit_sandbox,
                  "from pathlib import Path\n"
                  f"run = Path({str(run)!r})\n"
                  "for name in ('result.patch', 'meta.json', 'result.json', 'events.jsonl', 'stderr.log', 'prompt.md'):\n"
                  f" try: (run / name).symlink_to({str(caller / 'keep.txt')!r})\n"
                  " except OSError: pass\n"
                  f"(run / 'child/forged-result.json').symlink_to({str(caller / 'keep.txt')!r})\n"
                  "Path('keep.txt').write_text('worker edit')\n")
    runner.capture_patch(worktree, git(caller, "rev-parse", "HEAD").decode().strip(), run)
    assert (caller / "keep.txt").read_bytes() == before
    assert not (run / "result.patch").is_symlink()
    assert not any((run / name).is_symlink() for name in ("meta.json", "result.json", "events.jsonl",
                                                        "stderr.log", "prompt.md"))


def test_audit_real_profile_symlink_replacement_never_persists(audit_sandbox):
    _, _, run, agent = audit_sandbox
    original = os.readlink(agent / "skills")
    target = Path(original) / "input"
    sandbox_child(audit_sandbox,
                  "from pathlib import Path\n"
                  f"skills = Path({str(agent / 'skills')!r})\n"
                  "try: (skills / 'input').write_text('bad target')\n"
                  "except OSError: pass\n"
                  "try:\n skills.unlink()\n skills.symlink_to('/tmp/replacement')\n"
                  "except OSError: pass\n"
                  f"Path({str(run / 'child/profile-ok')!r}).write_text('ok')\n")
    assert os.readlink(agent / "skills") == original
    assert target.read_text() == "original skills"
    assert (run / "child/profile-ok").read_text() == "ok"


def test_audit_subdir_repo_protects_checkout_and_worktree_gitdir(audit_sandbox):
    caller, worktree, run, _ = audit_sandbox
    sandbox_child(audit_sandbox,
                  "from pathlib import Path\n"
                  f"try: Path({str(caller / 'keep.txt')!r}).write_text('bad sibling')\n"
                  "except OSError: pass\n"
                  "Path('keep.txt').write_text('worker edit')\n",
                  repo=caller / "subdir")
    assert (caller / "keep.txt").read_text() == "original\n"
    assert (worktree / "keep.txt").read_text() == "worker edit"


@pytest.mark.parametrize("events", [
    [{"type": "mcp_tool_call_end", "call_id": "one"}],
    [{"type": "mcp_tool_call_begin", "call_id": "one"},
     {"type": "mcp_tool_call_end", "call_id": "one"}],
])
def test_audit_mcp_end_event_is_counted_once(tmp_path, events):
    path = tmp_path / "rollout"
    write_records(path, [{"type": "turn_context", "payload": {
        "model": "m", "effort": "high", "sandbox_policy": {"type": "read-only"}}},
        *({"type": "event_msg", "payload": event} for event in events)])
    verification, _, _ = runner.verify_rollout(path, "m", "high", "read-only", False)
    assert verification["mcp_calls"] == 1
    assert "worker called MCP tools" in verification["issues"]


def test_audit_cloud_slot_survives_runner_sigkill(repo, environment):
    env, brief = environment
    env["FAKE_MODE"] = "sleep"
    root = Path(env["AGENT_RUN_HOME"])
    held = [runner.acquire_slot(root) for _ in range(2)]
    proc = subprocess.Popen([sys.executable, str(RUN), "sol", "--repo", str(repo), "--brief", str(brief)],
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    child = None
    try:
        deadline = time.monotonic() + 5
        while not Path(env["FAKE_CALLED"]).exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert Path(env["FAKE_CALLED"]).exists()
        _, meta = last_run(environment)
        child = meta["pgid"]
        proc.kill()
        proc.wait(timeout=5)
        env["FAKE_MODE"] = "ok"
        assert invoke(environment, "ask", "--model", "luna", "--brief", brief).returncode == 75
        runner.kill_group(child, signal.SIGKILL, meta["child_start"])
        deadline = time.monotonic() + 5
        free = None
        while free is None and time.monotonic() < deadline:
            free = runner.acquire_slot(root)
            if free is None:
                time.sleep(0.02)
        assert free is not None
        free.close()
    finally:
        if child:
            runner.kill_group(child, signal.SIGKILL, meta["child_start"])
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=5)
        for lock in held:
            lock.close()


@pytest.mark.parametrize("name", ["result.patch", "result.json", "meta.json", "brief.md", "schema.json"])
def test_audit_atomic_runner_outputs_never_follow_symlinks(repo, tmp_path, name):
    caller = tmp_path / "caller"
    caller.write_bytes(b"caller bytes")
    run = tmp_path / "run"
    run.mkdir()
    (run / name).symlink_to(caller)
    if name == "result.patch":
        runner.capture_patch(repo, git(repo, "rev-parse", "HEAD").decode().strip(), run)
    else:
        runner.atomic_bytes(run / name, b"new output")
    assert caller.read_bytes() == b"caller bytes"
    assert not (run / name).is_symlink()


def test_audit_child_transcript_symlink_is_not_read(tmp_path):
    outside = tmp_path / "outside"
    outside.write_text('{"type":"message","message":{"role":"assistant","model":"local","provider":"vllm"}}\n')
    child = tmp_path / "run/child"
    (child / "sessions").mkdir(parents=True)
    (child / "sessions/forged.jsonl").symlink_to(outside)
    issues = []
    assert list(runner.jsonl(child / "sessions/forged.jsonl", issues, root=child)) == []
    assert issues


def test_audit_real_bwrap_retains_both_locks_after_parent_closes_them(audit_sandbox):
    from concurrent.futures import ThreadPoolExecutor
    _, worktree, run, _ = audit_sandbox
    pool = run.parent / "pool"
    slots = [runner.acquire_slot(pool, local=True) for _ in range(4)]
    lifetime = runner.open_lock(run / "runner.lock")
    runner.fcntl.flock(lifetime, runner.fcntl.LOCK_EX)
    (run / "prompt.md").write_text("worker prompt")
    script = run / "child/lock-worker.py"
    script.write_text("from pathlib import Path\nimport time\n"
                      f"root = Path({str(run / 'child')!r})\n"
                      "(root / 'ready').write_text('ready')\n"
                      "while not (root / 'release').exists(): time.sleep(0.02)\n")
    command = runner.local_sandbox(worktree, run, audit_sandbox[0]) + [sys.executable, str(script)]
    meta = {"lane": "local", "run": "audit", "state": "running"}
    with ThreadPoolExecutor(max_workers=1) as workers:
        future = workers.submit(runner.execute, command, worktree, run, meta,
                                time.monotonic() + 10, [False], runner_lock=lifetime, slot_lock=slots[0])
        try:
            deadline = time.monotonic() + 5
            while not (run / "child/ready").exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            assert (run / "child/ready").exists()
            lifetime.close()
            slots[0].close()
            with runner.open_lock(run / "runner.lock") as probe_lock:
                with pytest.raises(BlockingIOError):
                    runner.fcntl.flock(probe_lock, runner.fcntl.LOCK_EX | runner.fcntl.LOCK_NB)
            assert runner.acquire_slot(pool, local=True) is None
        finally:
            (run / "child/release").touch()
            assert future.result(timeout=15) == (0, None)
            lifetime.close()
            for lock in slots:
                lock.close()
    with runner.acquire_slot(pool, local=True):
        pass


def test_a2_killing_local_guardian_kills_sandbox_and_frees_locks(audit_sandbox):
    from concurrent.futures import ThreadPoolExecutor
    _, worktree, run, _ = audit_sandbox
    pool = run.parent / "pool"
    slot = runner.acquire_slot(pool, local=True)
    lifetime = runner.open_lock(run / "runner.lock")
    runner.fcntl.flock(lifetime, runner.fcntl.LOCK_EX)
    (run / "prompt.md").write_text("worker prompt")
    beat = run / "child/beat"
    script = run / "child/beat-worker.py"
    script.write_text("from pathlib import Path\nimport time\n"
                      f"beat = Path({str(beat)!r})\n"
                      "n = 0\n"
                      "while True:\n    n += 1; beat.write_text(str(n)); time.sleep(0.02)\n")
    command = runner.local_sandbox(worktree, run, audit_sandbox[0]) + [sys.executable, str(script)]
    meta = {"lane": "local", "run": "audit", "state": "running"}
    with ThreadPoolExecutor(max_workers=1) as workers:
        future = workers.submit(runner.execute, command, worktree, run, meta,
                                time.monotonic() + 30, [False], runner_lock=lifetime, slot_lock=slot)
        deadline = time.monotonic() + 5
        while not beat.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert beat.exists() and meta.get("pid")
        lifetime.close()
        slot.close()
        os.kill(meta["pid"], signal.SIGKILL)
        future.result(timeout=15)
    time.sleep(0.3)
    first = beat.read_text()
    time.sleep(0.5)
    assert beat.read_text() == first, "sandboxed worker outlived its guardian"
    with runner.open_lock(run / "runner.lock") as probe_lock:
        runner.fcntl.flock(probe_lock, runner.fcntl.LOCK_EX | runner.fcntl.LOCK_NB)
    with runner.acquire_slot(pool, local=True):
        pass


def test_audit_linked_caller_checkout_and_its_index_are_read_only(audit_sandbox):
    caller, _, _, _ = audit_sandbox
    linked = caller.parent / "linked-caller"
    git(caller, "worktree", "add", "--detach", str(linked), "HEAD")
    (linked / "subdir").mkdir()
    gitdir = Path(git(linked, "rev-parse", "--absolute-git-dir").decode().strip())
    before = (gitdir / "index").read_bytes()
    sandbox_child(audit_sandbox,
                  "from pathlib import Path\n"
                  f"for path in (Path({str(linked / 'keep.txt')!r}), Path({str(gitdir / 'index')!r})):\n"
                  " try: path.write_bytes(b'bad caller write')\n"
                  " except OSError: pass\n",
                  repo=linked / "subdir")
    assert (linked / "keep.txt").read_text() == "original\n"
    assert (gitdir / "index").read_bytes() == before


@pytest.mark.parametrize("name", ["events.jsonl", "stderr.log"])
def test_audit_streaming_logs_refuse_existing_symlinks(repo, tmp_path, name):
    caller = tmp_path / "caller"
    caller.write_bytes(b"caller bytes")
    run = tmp_path / "run"
    run.mkdir()
    (run / "prompt.md").write_text("prompt")
    (run / name).symlink_to(caller)
    with pytest.raises(OSError):
        runner.execute([sys.executable, "-c", "print('child output')"], repo, run,
                       {"lane": "ask"}, time.monotonic() + 5, [False])
    assert caller.read_bytes() == b"caller bytes"


def test_audit_child_directory_symlink_is_not_traversed(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "forged.jsonl").write_text('{"private":"outside"}\n')
    child = tmp_path / "run/child"
    child.mkdir(parents=True)
    (child / "sessions").symlink_to(outside)
    issues = []
    assert list(runner.jsonl(child / "sessions/forged.jsonl", issues, root=child)) == []
    assert issues


@pytest.mark.parametrize("lane", ["sol", "ask", "audit"])
def test_a2_run_outputs_are_pinned_across_ancestor_swap(repo, environment, lane):
    env, brief = environment
    env.update(FAKE_MODE="swap-ancestor", FAKE_CALLER=str(repo))
    if lane == "audit":
        candidate = git(repo, "rev-parse", "HEAD").decode().strip()
        brief.write_text(f"Audited-Range: {candidate}..{candidate}\n")
        args = ["--packet", brief, "--candidate", candidate]
    else:
        args = ["--brief", brief, *(["--model", "luna"] if lane == "ask" else [])]
    p = invoke(environment, lane, "--repo", repo, *args)
    # Failure is safe too, but it must never redirect any runner artifact.
    assert p.returncode in (0, 1), p.stderr
    moved = Path(env["AGENT_RUN_HOME"] + "-moved")
    receipts = list(moved.glob("*/meta.json"))
    assert len(receipts) == 1
    meta = json.loads(receipts[0].read_text())
    assert meta["state"] != "running"
    if lane == "sol":
        assert (receipts[0].parent / "result.patch").is_file()
    else:
        assert (receipts[0].parent / "result.json").is_file()
    for name in ("meta.json", "result.json", "result.patch", "prompt.md", "schema.json", "child"):
        assert not (repo / name).exists(), name
    assert (repo / "keep.txt").read_text() == "original\n"


def test_a2_real_bwrap_persistent_surface_is_only_worker_and_child(audit_sandbox):
    caller, worktree, run, agent = audit_sandbox
    home = agent.parents[3]
    cache = home / ".cache"
    (home / "home-input").write_text("home original")
    (cache / "cache-input").write_text("cache original")
    (cache / "demo.md").write_text("nested original")
    skills = cache / "skills"
    (skills / "demo").mkdir()
    (skills / "demo/SKILL.md").symlink_to(cache / "demo.md")
    denied = [home / "home-input", cache / "cache-input", cache / "new-cache-file",
              home / ".omp/new-omp-file", run / "control-file", caller / "keep.txt", caller / ".git/config",
              agent / "skills/demo/SKILL.md"]
    originals = {path: path.read_bytes() for path in denied if path.exists()}
    sandbox_child(audit_sandbox,
                  "from pathlib import Path\n"
                  f"paths = {list(map(str, denied))!r}\n"
                  "for name in paths:\n"
                  " try: Path(name).write_text('worker mutation')\n"
                  " except OSError: pass\n"
                  "Path('persistent-worker-file').write_text('worker')\n"
                  f"Path({str(run / 'child/persistent-child-file')!r}).write_text('child')\n")
    for path in denied:
        if path in originals:
            assert path.read_bytes() == originals[path], path
        else:
            assert not path.exists(), path
    assert (cache / "demo.md").read_text() == "nested original"
    assert (worktree / "persistent-worker-file").read_text() == "worker"
    assert (run / "child/persistent-child-file").read_text() == "child"


@pytest.mark.parametrize("lane", ["sol", "local"])
@pytest.mark.parametrize("layout", ["worker-in-caller", "worker-over-caller", "state-in-caller",
                                  "state-in-worker", "worker-in-git"])
def test_a2_overlap_is_rejected_before_any_state_creation(repo, environment, lane, layout):
    env, brief = environment
    if layout == "worker-in-caller":
        env["AGENT_RUN_WORKTREE_ROOT"] = str(repo / "workers")
    elif layout == "worker-over-caller":
        env["AGENT_RUN_WORKTREE_ROOT"] = str(repo.parent)
    elif layout == "state-in-caller":
        env["AGENT_RUN_HOME"] = str(repo / "runs")
    elif layout == "state-in-worker":
        env["AGENT_RUN_HOME"] = str(Path(env["AGENT_RUN_WORKTREE_ROOT"]) / "runs")
    else:
        env["AGENT_RUN_WORKTREE_ROOT"] = str(repo / ".git/workers")
    p = invoke(environment, lane, "--repo", repo, "--brief", brief)
    assert p.returncode == 2, p.stdout + p.stderr
    assert "overlap" in p.stderr
    assert not Path(env["AGENT_RUN_HOME"]).exists()
    assert not list(repo.glob("**/*-sol-*"))


def test_a2_cancel_rejects_recycled_runner_and_child_identity(tmp_path, monkeypatch, capsys):
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
    run = tmp_path / "runs/stale"
    run.mkdir(parents=True)
    monkeypatch.setenv("AGENT_RUN_HOME", str(run.parent))
    meta = {"run": "stale", "state": "running", "runner_pid": proc.pid, "runner_start": "bogus",
            "pid": proc.pid, "pgid": proc.pid, "child_start": "bogus"}
    runner.atomic_json(run / "meta.json", meta)
    try:
        with runner.open_lock(run / "runner.lock") as lock:
            runner.fcntl.flock(lock, runner.fcntl.LOCK_EX)
            assert runner.main(["cancel", "stale"]) == 0
        assert (run / "cancel.requested").exists()
        assert "unverified" in capsys.readouterr().out
        with pytest.raises(subprocess.TimeoutExpired):
            proc.wait(timeout=0.1)
    finally:
        if proc.poll() is None:
            proc.terminate()
        proc.wait(timeout=5)


@pytest.mark.parametrize("action", ["show", "cancel", "gc"])
def test_a2_management_stays_on_open_run_after_ancestor_swap(tmp_path, monkeypatch, capsys, action):
    state = tmp_path / "state"
    run = state / "example"
    run.mkdir(parents=True)
    caller = tmp_path / "caller"
    caller.mkdir()
    (caller / "sentinel").write_text("unchanged")
    monkeypatch.setenv("AGENT_RUN_HOME", str(state))
    meta = {"run": "example", "state": "running", "lane": "ask", "model": "m",
            "verification": {"issues": []}, "runner_pid": 0, "runner_start": "bogus", "pid": 0}
    runner.atomic_json(run / "meta.json", meta)
    runner.atomic_json(run / "result.json", {"summary": "original"})
    moved = tmp_path / "state-moved"
    open_lock = runner.open_lock
    swapped = False

    def swap_after_open(path, **kwargs):
        nonlocal swapped
        lock = open_lock(path, **kwargs)
        if not swapped:
            state.rename(moved)
            state.mkdir()
            (state / "example").symlink_to(caller)
            swapped = True
        return lock

    with open_lock(run / "runner.lock") as holder:
        if action != "gc":
            runner.fcntl.flock(holder, runner.fcntl.LOCK_EX)
        monkeypatch.setattr(runner, "open_lock", swap_after_open)
        args = [action, "example", *(["--json"] if action == "show" else [])]
        assert runner.main(args) == 0
    assert swapped
    assert sorted(p.name for p in caller.iterdir()) == ["sentinel"]
    assert (caller / "sentinel").read_text() == "unchanged"
    if action == "show":
        assert json.loads(capsys.readouterr().out)["result"]["summary"] == "original"
    elif action == "cancel":
        assert (moved / "example/cancel.requested").exists()
    else:
        assert json.loads((moved / "example/meta.json").read_text())["gc_at"]


@pytest.mark.parametrize("group", [False, True])
@pytest.mark.parametrize("expected", [None, "old"])
def test_a2_all_signal_paths_fail_closed_without_identity(monkeypatch, group, expected):
    sent = []
    monkeypatch.setattr(runner, "process_start", lambda pid: "new")
    monkeypatch.setattr(runner.os, "kill", lambda *args: sent.append(args))
    monkeypatch.setattr(runner.os, "killpg", lambda *args: sent.append(args))
    assert runner.signal_checked(123, expected, signal.SIGTERM, group=group) is False
    assert not sent


def test_a2_darwin_start_identity_reader(monkeypatch):
    monkeypatch.setattr(runner.sys, "platform", "darwin")
    calls = []
    def ps(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "Sun Nov  8 01:00:00 2026\n", "")
    monkeypatch.setattr(runner.subprocess, "run", ps)
    assert runner.process_start(123) == "Sun Nov  8 01:00:00 2026"
    assert calls == [["ps", "-o", "lstart=", "-p", "123"]]


def test_a2_local_stdio_exposes_no_host_control_file_descriptors(audit_sandbox):
    caller, worktree, run, _ = audit_sandbox
    (run / "prompt.md").write_text("original prompt")
    source = run / "child/stdio-probe.py"
    source.write_text(
        "import json, os, pathlib, stat, sys\n"
        "sys.stdin.read()\n"
        "exposed = []\n"
        "for process in pathlib.Path('/proc').iterdir():\n"
        " if not process.name.isdigit(): continue\n"
        " try: descriptors = list((process / 'fd').iterdir())\n"
        " except OSError: continue\n"
        " for descriptor in descriptors:\n"
        "  try:\n"
        "   target = os.readlink(descriptor)\n"
        f"   control = target.startswith({str(run)!r}) and not target.startswith({str(run / 'child')!r})\n"
        "   if control and stat.S_ISREG(descriptor.stat().st_mode):\n"
        "    exposed.append(target)\n"
        "    try:\n"
        "     fd = os.open(descriptor, os.O_WRONLY | os.O_TRUNC)\n"
        "     os.write(fd, b'worker mutation')\n"
        "     os.close(fd)\n"
        "    except OSError: pass\n"
        "  except OSError: pass\n"
        f"pathlib.Path({str(run / 'child/exposed.json')!r}).write_text(json.dumps(exposed))\n")
    command = runner.local_sandbox(worktree, run, caller) + [sys.executable, str(source)]
    with runner.open_lock(run / "runner.lock") as lock:
        runner.fcntl.flock(lock, runner.fcntl.LOCK_EX)
        assert runner.execute(command, worktree, run, {"lane": "local"},
                              time.monotonic() + 10, [False], runner_lock=lock) == (0, None)
    assert json.loads((run / "child/exposed.json").read_text()) == []
    assert (run / "prompt.md").read_text() == "original prompt"


@pytest.mark.parametrize("lane", ["sol", "local", "ask", "audit"])
@pytest.mark.parametrize("layout", ["slash-tmp", "tmpdir", "tmpdir-in-state", "slots-in-tmpdir"])
def test_a3_state_temp_overlap_refused_without_state(repo, environment, lane, layout):
    env, brief = environment
    root = Path(env["AGENT_RUN_HOME"])
    dangerous = brief.parent / "worker-temp"
    if layout == "slash-tmp":
        env.pop("AGENT_RUN_TMP_ROOTS", None)
    else:
        env["TMPDIR"] = str(dangerous)
        env["AGENT_RUN_TMP_ROOTS"] = str(dangerous)
        if layout == "tmpdir":
            env["AGENT_RUN_HOME"] = str(dangerous / "state")
        elif layout == "tmpdir-in-state":
            env["TMPDIR"] = str(root / "temp")
            env["AGENT_RUN_TMP_ROOTS"] = env["TMPDIR"]
        else:
            root.mkdir()
            (root / ".slots").symlink_to(dangerous, target_is_directory=True)
    args = ["--repo", repo]
    if lane == "audit":
        candidate = git(repo, "rev-parse", "HEAD").decode().strip()
        brief.write_text(f"Audited-Range: {candidate}..{candidate}\n")
        args += ["--candidate", candidate, "--packet", brief]
    else:
        args += ["--brief", brief]
        if lane == "ask":
            args += ["--model", "luna"]
    p = invoke(environment, lane, *args)
    assert p.returncode == 2, p.stdout + p.stderr
    assert "run/state path" in p.stderr and "overlap" in p.stderr
    assert not Path(env["FAKE_CALLED"]).exists()
    assert not list(root.glob("*/meta.json"))
    assert not dangerous.exists()
    if layout != "slots-in-tmpdir":
        assert not Path(env["AGENT_RUN_HOME"]).exists()


@pytest.mark.parametrize("info_attributes", [False, True])
def test_a3_capture_never_executes_worker_filter_or_diff(repo, environment, info_attributes):
    env, brief = environment
    marker = brief.parent / "filter-executed"
    (repo / "filter.sh").write_text("cat\n")
    git(repo, "add", "filter.sh")
    git(repo, "commit", "-qm", "filter script")
    git(repo, "config", "filter.x.clean", "sh ./filter.sh")
    git(repo, "config", "filter.x.smudge", "cat")
    git(repo, "config", "filter.x.required", "true")
    git(repo, "config", "diff.x.command", "sh ./filter.sh")
    git(repo, "config", "diff.x.textconv", "sh ./filter.sh")
    if info_attributes:
        (repo / ".git/info/attributes").write_text("*.txt filter=x diff=x\n")
    env.update(FAKE_MODE="filter-edit", FAKE_FILTER_MARKER=str(marker))
    p = invoke(environment, "sol", "--repo", repo, "--brief", brief)
    assert p.returncode == 0, p.stdout + p.stderr
    run, meta = last_run(environment)
    assert not marker.exists()
    patch = (run / "result.patch").read_bytes()
    assert b"+unfiltered worker edit" in patch
    assert b"filter.sh" in patch and b".gitattributes" in patch
    assert {"keep.txt", "filter.sh", ".gitattributes"} <= set(meta["changed_paths"])


@pytest.mark.parametrize("lane", ["sol", "local"])
def test_a3_fifo_transcript_settles_with_patch(repo, environment, lane):
    env, brief = environment
    env["FAKE_MODE"] = "fifo-transcript"
    args = [lane, "--repo", str(repo), "--brief", str(brief)]
    if lane == "sol":
        command = [sys.executable, str(RUN), *args]
    else:
        # Exercise the complete local settlement without requiring a live vLLM
        # service or bwrap. Only dispatch is replaced, not file verification.
        source = (
            "import runpy,subprocess,sys\n"
            f"m=runpy.run_path({str(RUN)!r}); g=m['main'].__globals__\n"
            "g['local_configuration']=lambda:'test-local'\n"
            "g['local_sandbox']=lambda *a:[]\n"
            "def execute(command,cwd,run,meta,*a,**kw):\n"
            " p=subprocess.run(command,cwd=cwd,env=g['child_env'](),input=b'',capture_output=True)\n"
            " g['atomic_bytes'](run/'events.jsonl',p.stdout)\n"
            " return p.returncode,None\n"
            "g['execute']=execute\n"
            "sys.exit(g['main'](sys.argv[1:]))\n")
        command = [sys.executable, "-c", source, *args]
    start = time.monotonic()
    try:
        p = subprocess.run(command, env=env, capture_output=True, text=True, timeout=5)
    except subprocess.TimeoutExpired:
        pytest.fail("FIFO transcript blocked settlement for five seconds")
    assert time.monotonic() - start < 5
    assert p.returncode == 1, p.stdout + p.stderr
    run, meta = last_run(environment)
    assert meta["state"] == "unverified"
    assert any("regular file" in issue for issue in meta["verification"]["issues"])
    assert (run / "result.patch").is_file()
    assert b"keep.txt" in (run / "result.patch").read_bytes()


@pytest.mark.parametrize("kind", ["fifo", "directory"])
def test_a3_worker_reads_reject_nonregular_files(tmp_path, kind):
    path = tmp_path / "worker-output"
    if kind == "fifo":
        os.mkfifo(path)
    else:
        path.mkdir()
    # A separate process bounds the regression: O_RDONLY alone blocks on FIFO.
    source = (
        "import runpy,sys\n"
        f"m=runpy.run_path({str(RUN)!r})\n"
        "try:m['read_bytes'](sys.argv[1])\n"
        "except ValueError as e:\n"
        " assert 'regular file' in str(e);sys.exit(0)\n"
        "sys.exit(3)\n")
    try:
        p = subprocess.run([sys.executable, "-c", source, str(path)], capture_output=True, text=True, timeout=3)
    except subprocess.TimeoutExpired:
        pytest.fail("nonregular worker file blocked read")
    assert p.returncode == 0, p.stdout + p.stderr


@pytest.mark.parametrize("lane", ["sol", "local"])
def test_a3_patch_precedes_transcript_verification(repo, environment, monkeypatch, lane):
    env, brief = environment
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(runner, "local_configuration", lambda: "test-local")
    monkeypatch.setattr(runner, "local_sandbox", lambda *a: [])
    monkeypatch.setattr(runner, "profile_snapshot", lambda: {})

    def finish(command, cwd, run, *args, **kwargs):
        (Path(cwd) / "keep.txt").write_text("before verification\n")
        runner.atomic_json(run / "child/result.json", {"paths": [], "checks_run": [],
                                                      "summary": "ok", "blockers": []})
        return 0, None

    def verify(run, meta):
        assert b"+before verification" in runner.read_bytes(run / "result.patch")
        raise ValueError("stop after observing patch")

    monkeypatch.setattr(runner, "execute", finish)
    monkeypatch.setattr(runner, "verify_codex" if lane == "sol" else "verify_local", verify)
    assert runner.main([lane, "--repo", str(repo), "--brief", str(brief)]) == 1
    _, meta = last_run(environment)
    assert meta["error"] == "stop after observing patch"


def test_a3_git_reads_ignore_worktree_and_global_attributes(repo, tmp_path, monkeypatch):
    (repo / ".gitattributes").write_text("*.txt filter=worker diff=worker\n")
    attributes = tmp_path / "global-attributes"
    attributes.write_text("*.txt filter=global diff=global\n")
    config = tmp_path / "global-config"
    config.write_text(f"[core]\nattributesFile = {attributes}\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_ATTR_SOURCE", "HEAD")
    output = runner.git(repo, "check-attr", "filter", "diff", "--", "keep.txt")
    assert output == b"keep.txt: filter: unspecified\nkeep.txt: diff: unspecified\n"


@pytest.mark.parametrize("key", ["DBUS_SESSION_BUS_ADDRESS", "DBUS_SYSTEM_BUS_ADDRESS", "DBUS_STARTER_ADDRESS",
                                 "DBUS_STARTER_BUS_TYPE", "XDG_RUNTIME_DIR", "SSH_AUTH_SOCK", "SSH_AGENT_PID",
                                 "GPG_AGENT_INFO", "WAYLAND_DISPLAY", "DISPLAY"])
def test_r6_child_environment_strips_host_ipc(key):
    assert key not in runner.child_env({key: "host endpoint"})


@pytest.mark.parametrize("key", ["AGENT_RUN_CHILD", "CODEX_SANDBOX", "CODEX_SANDBOX_NETWORK_DISABLED"])
def test_r6_workers_cannot_launch_runner(monkeypatch, capsys, key):
    monkeypatch.setenv(key, "1")
    assert runner.main(["list"]) == 3
    assert "worker" in capsys.readouterr().err
    assert runner.child_env({})["AGENT_RUN_CHILD"] == "1"


def test_r6_local_tools_and_director_acceptance(repo, environment, monkeypatch):
    env, brief = environment
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(runner, "local_configuration", lambda: "test-local")
    monkeypatch.setattr(runner, "local_sandbox", lambda *args: [])
    monkeypatch.setattr(runner, "profile_snapshot", lambda: {})
    def inspect(command, cwd, run, *args, **kwargs):
        assert set(command[command.index("--tools") + 1].split(",")) == {"read", "edit", "write", "grep", "glob"}
        assert runner.LOCAL_TOOLS == {"read", "edit", "write", "grep", "glob"}
        prompt = runner.read_bytes(run / "prompt.md").decode()
        assert "director runs the acceptance check" in prompt
        assert "checks_run" in prompt and "could not run" in prompt
        raise ValueError("inspected command")
    monkeypatch.setattr(runner, "execute", inspect)
    assert runner.main(["local", "--repo", str(repo), "--brief", str(brief)]) == 1
    _, meta = last_run(environment)
    assert meta["error"] == "inspected command"


def test_r6_real_local_masks_systemd_ipc(audit_sandbox):
    if not runner.shutil.which("systemd-run"):
        pytest.skip("systemd-run unavailable")
    caller, _, run, _ = audit_sandbox
    marker = caller / "escaped"
    sandbox_child(audit_sandbox,
                  "import os,subprocess\nfrom pathlib import Path\n"
                  "import stat\n"
                  "bus=Path('/run/user')/str(os.getuid())/'bus'\n"
                  "assert not bus.exists() or not stat.S_ISSOCK(bus.stat().st_mode)\n"
                  "assert Path('/var/run').resolve() == Path('/run')\n"
                  f"p=subprocess.run(['systemd-run','--user','--wait','--collect','touch',{str(marker)!r}],timeout=5)\n"
                  "assert p.returncode != 0\n")
    assert not marker.exists()
    command = runner.local_sandbox(audit_sandbox[1], run, caller)
    assert "--unshare-ipc" in command


def test_r6_real_guardian_ignores_worktree_imports(audit_sandbox):
    caller, worktree, run, _ = audit_sandbox
    marker = caller / "import-escape"
    for name in ("argparse", "sitecustomize", "pkgutil"):
        (worktree / (name + ".py")).write_text(f"open({str(marker)!r},'w').write('escaped')\n")
    (run / "prompt.md").write_text("brief")
    script = run / "child/probe.py"
    script.write_text("from pathlib import Path\nPath('keep.txt').write_text('sandbox started')\n")
    command = runner.local_sandbox(worktree, run, caller) + [sys.executable, "-I", str(script)]
    meta = {"lane": "local"}
    code, terminal = runner.execute(command, worktree, run, meta, time.monotonic() + 5, [False])
    assert code == 0 and terminal is None
    assert not marker.exists()
    assert (worktree / "keep.txt").read_text() == "sandbox started"


def test_r6_patch_index_never_uses_shared_temp(repo, tmp_path, monkeypatch):
    import tempfile
    run = tmp_path / "run"
    run.mkdir()
    shared = tmp_path / "shared"
    shared.mkdir()
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(shared))
    before = (repo / ".git/index").read_bytes()
    original_git = runner.git
    def swap(tree, *args, **kwargs):
        if args[0] == "read-tree":
            for path in shared.glob("agent-index-*"):
                path.rmdir()
                path.symlink_to(repo / ".git", target_is_directory=True)
        return original_git(tree, *args, **kwargs)
    monkeypatch.setattr(runner, "git", swap)
    (repo / "keep.txt").write_text("worker edit")
    runner.capture_patch(repo, git(repo, "rev-parse", "HEAD").decode().strip(), run)
    assert (repo / ".git/index").read_bytes() == before
    assert list(shared.iterdir()) == []
    assert sorted(p.name for p in run.iterdir()) == ["result.patch"]


@pytest.mark.parametrize("mode", ["ok", "missing-tmp-flags"])
def test_r6_sol_tmp_policy_and_child_tmp(repo, environment, mode):
    env, brief = environment
    env["FAKE_MODE"] = mode
    p = invoke(environment, "sol", "--repo", repo, "--brief", brief)
    run, meta = last_run(environment)
    called = json.loads(Path(env["FAKE_CALLED"]).read_text())
    args = called["args"]
    assert called["tmp"] == {key: str(run / "child/tmp") for key in ("TMPDIR", "TMP", "TEMP")}
    assert called["child"] == "1"
    assert "sandbox_workspace_write.exclude_slash_tmp=true" in args
    assert "sandbox_workspace_write.exclude_tmpdir_env_var=true" in args
    assert args[args.index("--add-dir") + 1] == str(run / "child/tmp")
    assert meta["verification"]["sandbox_ok"] is (mode == "ok")
    assert meta["state"] == ("ok" if mode == "ok" else "unverified"), p.stdout + p.stderr
    assert meta["verification"]["attestation_evidence"] == "rollout"


@pytest.mark.parametrize("mode", ["sparse-transcript", "sparse-result", "huge-line"])
def test_r6_oversized_worker_file_settles_promptly_with_patch(repo, environment, mode):
    import resource
    env, brief = environment
    env["FAKE_MODE"] = mode
    def limit_memory():
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024,) * 2)
    start = time.monotonic()
    p = subprocess.run([sys.executable, str(RUN), "sol", "--repo", str(repo), "--brief", str(brief)],
                       env=env, capture_output=True, text=True, timeout=5, preexec_fn=limit_memory)
    assert time.monotonic() - start < 5
    assert p.returncode == 1, p.stdout + p.stderr
    run, meta = last_run(environment)
    assert meta["state"] == "unverified"
    assert any("limit" in issue for issue in meta["verification"]["issues"])
    assert b"+partial oversized worker edit" in (run / "result.patch").read_bytes()


@pytest.mark.parametrize("configured", [True, False])
def test_r6_git_preserves_trusted_global_excludes(repo, tmp_path, monkeypatch, configured):
    home = tmp_path / "home"
    ignore = home / ("custom-ignore" if configured else ".config/git/ignore")
    ignore.parent.mkdir(parents=True)
    ignore.write_text("*.personal\n")
    config = home / ".gitconfig"
    config.write_text(f"[core]\nexcludesFile = {ignore}\n" if configured else "")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    if hasattr(runner, "trusted_excludes_file"):
        runner.trusted_excludes_file.cache_clear()
    (repo / "worker.personal").write_text("private")
    try:
        assert "worker.personal" in runner.ignored_files(repo)
    finally:
        if hasattr(runner, "trusted_excludes_file"):
            runner.trusted_excludes_file.cache_clear()


def test_r6_worker_read_budget_is_shared_across_files(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "MAX_WORKER_BYTES", 1024, raising=False)
    path = tmp_path / "output"
    path.write_bytes(b"x" * 600)
    token = runner.WORKER_READ_BYTES.set(0)
    try:
        assert len(runner.read_bytes(path)) == 600
        with pytest.raises(ValueError, match="read limit exceeded"):
            runner.read_bytes(path)
    finally:
        runner.WORKER_READ_BYTES.reset(token)


@pytest.mark.parametrize("policy_change", ["missing", "false", "later", "descendant", "run-root"])
def test_r6_every_workspace_turn_requires_tight_temp_policy(tmp_path, policy_change):
    tree, child_tmp = tmp_path / "tree", tmp_path / "run/child/tmp"
    policy = {"type": "workspace-write", "exclude_slash_tmp": True, "exclude_tmpdir_env_var": True,
              "writable_roots": [str(tree), str(child_tmp)]}
    records = [{"type": "turn_context", "payload": {"model": "m", "effort": "high", "sandbox_policy": policy}}]
    if policy_change == "missing":
        policy.pop("exclude_slash_tmp")
    elif policy_change == "false":
        policy["exclude_tmpdir_env_var"] = False
    elif policy_change == "later":
        records.append({"type": "turn_context", "payload": {"model": "m", "effort": "high",
                        "sandbox_policy": dict(policy, exclude_tmpdir_env_var=False)}})
    else:
        policy["writable_roots"].append(str(tree / "subdir" if policy_change == "descendant" else tmp_path / "run"))
    path = tmp_path / "rollout"
    write_records(path, records)
    verification, _, _ = runner.verify_rollout(path, "m", "high", "workspace-write", False, [tree, child_tmp])
    assert verification["sandbox_ok"] is False


def test_r6_claude_receipt_labels_evidence(tmp_path, monkeypatch):
    run, transcript, records, meta = claude_attestation_fixture(tmp_path, monkeypatch)
    write_records(transcript, records)
    assert runner.verify_claude(run, meta, tmp_path)["attestation_evidence"] == "transcript"


def test_r6_local_receipt_labels_worker_writable_evidence_and_rejects_bash(tmp_path):
    message = {"role": "assistant", "provider": "vllm", "model": "local",
               "content": [{"type": "text", "text": "{}"}], "stopReason": "stop"}
    write_records(tmp_path / "events.jsonl", [
        {"type": "session", "id": "session"}, {"type": "message_end", "message": message}])
    write_records(tmp_path / "child/sessions/time_session.jsonl", [
        {"type": "model_change", "model": "vllm/local", "resolvedModelIsFallback": False},
        {"type": "thinking_level_change", "thinkingLevel": "medium"},
        {"type": "message", "message": dict(message, content=[{"type": "toolCall", "name": "bash"}])}])
    meta = {"model": "local", "effort": "medium", "sandbox": "bwrap", "sandbox_probe_ok": True,
            "sandbox_argv": ["/usr/bin/bwrap", "--ro-bind", "/", "/"], "child": {"transcript_path": None}}
    verification = runner.verify_local(tmp_path, meta)
    assert verification["tools_ok"] is False
    assert verification["attestation_evidence"] == "omp-session-worker-writable"


def test_r6_temp_repo_guard_runs_once(repo, environment, monkeypatch):
    env, brief = environment
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    calls = []
    original = runner.refuse_temporary_repo
    def guard(path):
        calls.append(path)
        return original(path)
    monkeypatch.setattr(runner, "refuse_temporary_repo", guard)
    assert runner.main(["sol", "--repo", str(repo), "--brief", str(brief)]) == 0
    assert calls == [repo]


def test_r7_patch_capture_absolute_fallback_is_applicable_and_preserves_indexes(repo, tmp_path, monkeypatch):
    worker = tmp_path / "worker"
    git(repo, "worktree", "add", "--detach", str(worker), "HEAD")
    run = tmp_path / "run"
    run.mkdir()
    caller_index = (repo / ".git/index").read_bytes()
    worker_index = Path(git(worker, "rev-parse", "--git-path", "index").decode().strip())
    before = worker_index.read_bytes()
    (worker / "delete.txt").unlink()
    (worker / "new.txt").write_text("new output\n")
    (worker / "blob.bin").write_bytes(b"\x00changed\xff")
    monkeypatch.setattr(runner, "fd_directory_paths_supported", lambda: False, raising=False)
    original = runner.git
    def inspect(tree, *args, **kwargs):
        if "GIT_INDEX_FILE" in kwargs.get("env", {}):
            assert Path(kwargs["env"]["GIT_INDEX_FILE"]).parent == run
        return original(tree, *args, **kwargs)
    monkeypatch.setattr(runner, "git", inspect)
    paths, _ = runner.capture_patch(worker, git(repo, "rev-parse", "HEAD").decode().strip(), run)
    patch = (run / "result.patch").read_bytes()
    assert sorted(paths) == ["blob.bin", "delete.txt", "new.txt"]
    assert b"deleted file mode" in patch and b"GIT binary patch" in patch
    assert (repo / ".git/index").read_bytes() == caller_index
    assert worker_index.read_bytes() == before
    git(repo, "apply", "--check", str(run / "result.patch"))
    assert sorted(p.name for p in run.iterdir()) == ["result.patch"]


@pytest.mark.parametrize("when", ["before", "after"])
def test_r7_absolute_capture_identity_mismatch_fails_closed(repo, tmp_path, monkeypatch, when):
    run = tmp_path / "run"
    run.mkdir()
    replacement = tmp_path / "replacement"
    replacement.mkdir()
    (repo / "keep.txt").write_text("worker edit\n")
    monkeypatch.setattr(runner, "fd_directory_paths_supported", lambda: False, raising=False)
    original_stat, original_git = runner.os.stat, runner.git
    calls = []
    def stat_path(path, *args, **kwargs):
        if str(path) == str(run) and (when == "before" or calls):
            return original_stat(replacement)
        return original_stat(path, *args, **kwargs)
    def record_git(tree, *args, **kwargs):
        if "GIT_INDEX_FILE" in kwargs.get("env", {}):
            calls.append(args)
        return original_git(tree, *args, **kwargs)
    monkeypatch.setattr(runner.os, "stat", stat_path)
    monkeypatch.setattr(runner, "git", record_git)
    meta = {"worktree": str(repo), "base": git(repo, "rev-parse", "HEAD").decode().strip(),
            "verification": runner.blank_verification()}
    runner.capture_worker_patch(meta, run)
    assert "identity" in meta.get("patch_error", "")
    assert not meta.get("patch_captured")
    assert not (run / "result.patch").exists()
    assert len(calls) == (0 if when == "before" else 1)


def test_r7_gc_removes_only_child_tmp_even_with_locked_directories(tmp_path):
    run = tmp_path / "run"
    nested = run / "child/tmp/locked/nested"
    nested.mkdir(parents=True)
    (nested / "output").write_text("temporary")
    (run / "child/sessions").mkdir()
    (run / "child/sessions/transcript.jsonl").write_text("{}\n")
    (run / "result.json").write_text("{}")
    (run / "result.patch").write_text("patch")
    (nested.parent).chmod(0)
    (run / "child/tmp").chmod(0)
    try:
        with runner.pin_directory(run) as pinned:
            runner.gc_run(pinned, {"state": "ok"})
        assert not (run / "child/tmp").exists()
        assert (run / "child/sessions/transcript.jsonl").read_text() == "{}\n"
        assert (run / "result.json").read_text() == "{}"
        assert (run / "result.patch").read_text() == "patch"
    finally:
        for path in (run / "child/tmp", nested.parent):
            if path.exists():
                path.chmod(0o700)


@pytest.mark.parametrize("lane,setup", [("sol", True), ("sol", False), ("ask", False), ("local", False)])
def test_r7_execute_environment_separates_setup_and_workers(tmp_path, monkeypatch, lane, setup):
    run = tmp_path / "run"
    (run / "child/tmp").mkdir(parents=True)
    (run / "prompt.md").write_text("brief")
    keys = ["HERDR_TEST", "CLAUDE_CODE_SESSION_ID", "CLAUDECODE", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
            "PI_SESSION_FILE", "OMPCODE", "CODEX_THREAD_ID", "SSH_AUTH_SOCK", "DBUS_SESSION_BUS_ADDRESS",
            "XDG_RUNTIME_DIR", "TMPDIR", "TMP", "TEMP"]
    for key in keys:
        monkeypatch.setenv(key, "director-" + key)
    monkeypatch.delenv("AGENT_RUN_CHILD", raising=False)
    # Use a tiny real subprocess to capture its environment. For local this
    # dispatch-only test bypasses the guardian; sandbox properties have real-bwrap tests.
    original_popen = runner.subprocess.Popen
    observed = []
    def record(command, **kwargs):
        observed.append(kwargs["env"])
        return original_popen([sys.executable, "-I", "-c", "import sys; sys.stdin.read()"], **kwargs)
    monkeypatch.setattr(runner.subprocess, "Popen", record)
    meta = {"lane": lane}
    code, reason = runner.execute(["test-worker"], tmp_path, run, meta, time.monotonic() + 5, [False], setup=setup)
    assert code == 0 and reason is None
    env = observed[0]
    assert all(key not in env for key in keys[:8])
    for key in ("SSH_AUTH_SOCK", "DBUS_SESSION_BUS_ADDRESS", "XDG_RUNTIME_DIR"):
        assert env.get(key) == ("director-" + key if setup else None)
    assert env.get("AGENT_RUN_CHILD") == (None if setup else "1")
    for key in ("TMPDIR", "TMP", "TEMP"):
        assert env[key] == (str(run / "child/tmp") if lane == "sol" and not setup else "director-" + key)


@pytest.mark.parametrize("kind", ["file", "directory", "socket", "outside-run"])
def test_r7_local_dns_only_restores_regular_resolver_under_run(tmp_path, monkeypatch, kind):
    monkeypatch.setenv("HOME", str(tmp_path))
    worker, run = tmp_path / "worker", tmp_path / "run"
    worker.mkdir()
    run.mkdir()
    resolver = Path("/etc/resolver-file" if kind == "outside-run" else "/run/systemd/resolve/stub-resolv.conf")
    original_realpath, original_is_file = runner.os.path.realpath, Path.is_file
    def realpath(path, *args, **kwargs):
        return str(resolver) if str(path) == "/etc/resolv.conf" else original_realpath(path, *args, **kwargs)
    monkeypatch.setattr(runner.os.path, "realpath", realpath)
    monkeypatch.setattr(Path, "is_file", lambda path: kind in {"file", "outside-run"} if path == resolver else original_is_file(path))
    monkeypatch.setattr(runner.shutil, "which", lambda name: "/usr/bin/bwrap")
    monkeypatch.setattr(runner, "git", lambda *args, **kwargs: str(tmp_path / ".git").encode())
    monkeypatch.setattr(runner.subprocess, "run", lambda *args, **kwargs: type("Result", (), {"returncode": 0})())
    command = runner.local_sandbox(worker, run, tmp_path)
    bindings = [command[i:i + 3] for i, token in enumerate(command) if token == "--ro-bind"]
    assert (["--ro-bind", str(resolver), str(resolver)] in bindings) is (kind == "file")
    if kind == "file":
        assert command.index(str(resolver)) > command.index("/run")


def test_r7_read_budget_accepts_long_rollouts_and_keeps_line_cap():
    assert runner.MAX_WORKER_BYTES == 512 * 1024 * 1024
    assert runner.MAX_JSONL_LINE == 16 * 1024 * 1024
    token = runner.WORKER_READ_BYTES.set(0)
    try:
        runner.consume_worker_bytes(70 * 1024 * 1024)
        assert runner.WORKER_READ_BYTES.get() == 70 * 1024 * 1024
        with pytest.raises(ValueError, match="read limit exceeded"):
            runner.consume_worker_bytes(443 * 1024 * 1024)
    finally:
        runner.WORKER_READ_BYTES.reset(token)


def test_r7_receipt_records_worker_bytes_read(repo, environment):
    _, brief = environment
    p = invoke(environment, "sol", "--repo", repo, "--brief", brief)
    assert p.returncode == 0, p.stdout + p.stderr
    run, meta = last_run(environment)
    sources = [run / "events.jsonl", Path(meta["child"]["transcript_path"]),
               run / "child/result.json", run / "result.json"]
    assert meta.get("worker_bytes_read") == sum(path.stat().st_size for path in sources)


@pytest.mark.parametrize("key", ["AGENT_RUN_CHILD", "CODEX_SANDBOX", "CODEX_SANDBOX_NETWORK_DISABLED"])
def test_r7_nested_guard_names_variable_and_recovery(monkeypatch, capsys, key):
    for name in ("AGENT_RUN_CHILD", "CODEX_SANDBOX", "CODEX_SANDBOX_NETWORK_DISABLED"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(key, "1")
    assert runner.main(["list"]) == 3
    message = capsys.readouterr().err
    assert key in message
    assert "Claude Code or a plain shell" in message


def test_r7_fd_directory_capability_is_checked_once_and_fails_closed(monkeypatch):
    original = runner.os.stat
    aliases = []
    def unavailable(path, *args, **kwargs):
        if str(path).startswith("/dev/fd/"):
            aliases.append(str(path))
            raise FileNotFoundError("no directory traversal")
        return original(path, *args, **kwargs)
    runner.fd_directory_paths_supported.cache_clear()
    monkeypatch.setattr(runner.os, "stat", unavailable)
    try:
        assert runner.fd_directory_paths_supported() is False
        assert runner.fd_directory_paths_supported() is False
        assert len(aliases) == 1
    finally:
        runner.fd_directory_paths_supported.cache_clear()


def test_r7_gc_tmp_symlink_never_traverses_outside_run(tmp_path):
    run = tmp_path / "run"
    (run / "child").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep").write_text("untouched")
    (run / "child/tmp").symlink_to(outside, target_is_directory=True)
    with runner.pin_directory(run) as pinned:
        runner.gc_run(pinned, {"state": "ok"})
    assert not (run / "child/tmp").is_symlink()
    assert (outside / "keep").read_text() == "untouched"


def test_r8_gc_retries_tmp_without_repeating_worktree_removal(repo, environment, monkeypatch):
    _, brief = environment
    p = invoke(environment, "sol", "--repo", repo, "--brief", brief)
    assert p.returncode == 0, p.stdout + p.stderr
    run, meta = last_run(environment)
    original_remove = getattr(runner, "remove_child_tmp", lambda run: None)
    original_git = runner.git
    removals, attempts = [], []
    def remove_tmp(directory):
        attempts.append(True)
        if len(attempts) == 1:
            raise OSError("temporary cleanup is busy")
        return original_remove(directory)
    def record_git(tree, *args, **kwargs):
        if args[:2] == ("worktree", "remove"):
            removals.append(args)
        return original_git(tree, *args, **kwargs)
    monkeypatch.setattr(runner, "remove_child_tmp", remove_tmp, raising=False)
    monkeypatch.setattr(runner, "git", record_git)
    with runner.pin_directory(run) as directory:
        with pytest.raises(RuntimeError, match="temporary cleanup"):
            runner.gc_run(directory, meta)
    persisted = json.loads((run / "meta.json").read_text())
    assert persisted.get("worktree_removed")
    assert "busy" in persisted.get("gc_tmp_error", "")
    assert not persisted.get("gc_at")
    assert not Path(meta["worktree"]).exists()
    with runner.pin_directory(run) as directory:
        runner.gc_run(directory, persisted)
    complete = json.loads((run / "meta.json").read_text())
    assert complete.get("gc_at") and complete.get("worktree_removed")
    assert "gc_tmp_error" not in complete
    assert not (run / "child/tmp").exists()
    assert len(removals) == 1 and len(attempts) == 2


def test_r8_gc_removes_3000_deep_tmp_tree_without_recursion(tmp_path):
    run = tmp_path / "run"
    child = run / "child"
    child.mkdir(parents=True)
    child_fd = os.open(child, os.O_RDONLY | os.O_DIRECTORY)
    os.mkdir("tmp", dir_fd=child_fd)
    fd = os.open("tmp", os.O_RDONLY | os.O_DIRECTORY, dir_fd=child_fd)
    try:
        for _ in range(3000):
            os.mkdir("d", dir_fd=fd)
            next_fd = os.open("d", os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        out = os.open("output", os.O_WRONLY | os.O_CREAT, 0o600, dir_fd=fd)
        os.close(out)
    finally:
        os.close(fd)
    try:
        with runner.pin_directory(run) as directory:
            runner.gc_run(directory, {"state": "ok"})
        assert not (child / "tmp").exists()
    finally:
        # Keep pytest's fixture cleanup shallow even against the old runner.
        if (child / "tmp").exists():
            for _, dirs, files, root_fd in os.fwalk("tmp", topdown=False, dir_fd=child_fd, follow_symlinks=False):
                for name in files:
                    os.unlink(name, dir_fd=root_fd)
                for name in dirs:
                    os.rmdir(name, dir_fd=root_fd)
            os.rmdir("tmp", dir_fd=child_fd)
        os.close(child_fd)


@pytest.mark.parametrize("present", [False, True])
def test_r8_gc_reconciles_only_absent_unregistered_worktree(repo, tmp_path, present):
    root = tmp_path / "workers"
    root.mkdir()
    worker = root / (repo.name + "-run")
    if present:
        worker.mkdir()
    run = tmp_path / "run"
    (run / "child/tmp").mkdir(parents=True)
    meta = {"state": "ok", "run": "run", "repo": str(repo),
            "worktree": str(worker), "worktree_root": str(root)}
    with runner.pin_directory(run) as directory:
        if present:
            with pytest.raises(ValueError, match="not registered"):
                runner.gc_run(directory, meta)
            assert worker.exists()
        else:
            runner.gc_run(directory, meta)
            assert meta.get("worktree_removed") and meta.get("gc_at")
            assert not (run / "child/tmp").exists()


@pytest.mark.parametrize("symlink", [False, True])
def test_r8_chmod_old_glibc_fallback_never_changes_symlink_target(tmp_path, monkeypatch, symlink):
    target = tmp_path / "target"
    target.mkdir()
    target.chmod(0o755)
    entry = tmp_path / "entry"
    if symlink:
        entry.symlink_to(target, target_is_directory=True)
    else:
        entry.mkdir()
        entry.chmod(0o755)
    original = runner.os.chmod
    calls = []
    def old_glibc(path, mode, **kwargs):
        calls.append(kwargs)
        if kwargs.get("follow_symlinks") is False:
            raise NotImplementedError("old glibc")
        return original(path, mode, **kwargs)
    monkeypatch.setattr(runner.os, "chmod", old_glibc)
    with runner.pin_directory(tmp_path) as directory:
        (directory / "entry").chmod(0o700)
    assert target.stat().st_mode & 0o777 == 0o755
    assert len(calls) == (1 if symlink else 2)
    if not symlink:
        assert entry.stat().st_mode & 0o777 == 0o700


def test_r8_gc_does_not_open_symlinks_inside_tmp(tmp_path, monkeypatch):
    run = tmp_path / "run"
    tmp = run / "child/tmp"
    tmp.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep").write_text("untouched")
    (tmp / "directory-link").symlink_to(outside, target_is_directory=True)
    (tmp / "file-link").symlink_to(outside / "keep")
    original = runner.os.open
    def no_link_open(path, *args, **kwargs):
        assert str(path) not in {str(outside), "directory-link", "file-link"}
        return original(path, *args, **kwargs)
    monkeypatch.setattr(runner.os, "open", no_link_open)
    with runner.pin_directory(run) as directory:
        runner.gc_run(directory, {"state": "ok"})
    assert not tmp.exists()
    assert (outside / "keep").read_text() == "untouched"


def test_r8_gc_clears_supported_bsd_flags_fd_relative(tmp_path, monkeypatch):
    run = tmp_path / "run"
    (run / "child/tmp/d").mkdir(parents=True)
    (run / "child/tmp/d/output").write_text("temporary")
    flags = []
    def chflags(name, value, *, dir_fd, follow_symlinks):
        assert isinstance(dir_fd, int) and follow_symlinks is False and value == 0
        flags.append(name)
    monkeypatch.setattr(runner.os, "chflags", chflags, raising=False)
    monkeypatch.setattr(runner.os, "supports_dir_fd", runner.os.supports_dir_fd | {chflags})
    with runner.pin_directory(run) as directory:
        runner.gc_run(directory, {"state": "ok"})
    assert {"tmp", "d", "output"} <= set(flags)
    assert not (run / "child/tmp").exists()


@pytest.mark.parametrize("flagged,identity,symlink", [
    (True, True, False), (True, False, False), (False, True, False), (True, True, True)])
def test_r8_gc_macos_lchflags_fallback_checks_flags_and_identity(tmp_path, monkeypatch, flagged, identity, symlink):
    from types import SimpleNamespace
    run = tmp_path / "run"
    parent = run / "child/tmp/nested"
    parent.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.write_text("untouched")
    entry = parent / "flagged"
    if symlink:
        entry.symlink_to(outside)
    else:
        entry.write_text("temporary")
    original_stat, original_lstat, original_unlink = runner.os.stat, runner.os.lstat, runner.os.unlink
    cleared = []
    checked = []
    def flagged_stat(path, *args, **kwargs):
        result = original_stat(path, *args, **kwargs)
        if str(path) == "flagged" and kwargs.get("dir_fd") is not None and kwargs.get("follow_symlinks") is False:
            fields = {key: getattr(result, key) for key in dir(result) if key.startswith("st_")}
            fields["st_flags"] = 2 if flagged and not cleared else 0
            return SimpleNamespace(**fields)
        return result
    def check_lstat(path, *args, **kwargs):
        if Path(path) == entry:
            checked.append(Path(path))
            if not identity:
                return original_lstat(outside)
        return original_lstat(path, *args, **kwargs)
    def unsupported_chflags(*args, **kwargs):
        raise TypeError("macOS has no chflagsat")
    def lchflags(path, value):
        assert Path(path) == entry and value == 0
        cleared.append(Path(path))
    def unlink(path, *args, **kwargs):
        if str(path) == "flagged" and flagged and not cleared:
            raise PermissionError("user-immutable flagged entry")
        return original_unlink(path, *args, **kwargs)
    monkeypatch.setattr(runner.os, "stat", flagged_stat)
    monkeypatch.setattr(runner.os, "lstat", check_lstat)
    monkeypatch.setattr(runner.os, "chflags", unsupported_chflags, raising=False)
    monkeypatch.setattr(runner.os, "lchflags", lchflags, raising=False)
    monkeypatch.setattr(runner.os, "unlink", unlink)
    with runner.pin_directory(run) as directory:
        if flagged and not identity:
            with pytest.raises(RuntimeError, match="temporary cleanup"):
                runner.gc_run(directory, {"state": "ok"})
            meta = json.loads((run / "meta.json").read_text())
            assert "user-immutable" in meta["gc_tmp_error"]
            assert not meta.get("gc_at")
            assert not cleared
        else:
            runner.gc_run(directory, {"state": "ok"})
            assert not (run / "child/tmp").exists()
            assert cleared == ([entry] if flagged else [])
    assert outside.read_text() == "untouched"
    assert bool(checked) is flagged


@pytest.mark.parametrize("age", ["0", "1e-9"])
def test_r9_gc_sweep_collects_missing_repo_and_later_healthy_run(repo, environment, tmp_path, age):
    _, brief = environment
    healthy_repo = tmp_path / "healthy-repo"
    git(repo, "clone", "-q", str(repo), str(healthy_repo))
    first = invoke(environment, "sol", "--repo", repo, "--brief", brief, "--name", "a-missing")
    assert first.returncode == 0, first.stdout + first.stderr
    missing_run, missing_meta = last_run(environment)
    second = invoke(environment, "sol", "--repo", healthy_repo, "--brief", brief, "--name", "b-healthy")
    assert second.returncode == 0, second.stdout + second.stderr
    healthy_run = next(path.parent for path in missing_run.parent.glob("*/meta.json") if path.parent != missing_run)
    healthy_meta = json.loads((healthy_run / "meta.json").read_text())
    runner.shutil.rmtree(repo)
    p = invoke(environment, "gc", "--older-than", age)
    assert p.returncode == 0, p.stdout + p.stderr
    for run, meta in ((missing_run, missing_meta), (healthy_run, healthy_meta)):
        receipt = json.loads((run / "meta.json").read_text())
        assert receipt.get("gc_at") and receipt.get("worktree_removed")
        assert f"gc {meta['run']}" in p.stdout
        assert not Path(meta["worktree"]).exists()
        assert not (run / "child/tmp").exists()
        assert (run / "result.patch").is_file()
    assert json.loads((missing_run / "meta.json").read_text())["worktree_removed_without_repo"] is True
    assert not json.loads((healthy_run / "meta.json").read_text()).get("worktree_removed_without_repo")


def test_r9_gc_sweep_reports_failure_and_continues(repo, environment):
    _, brief = environment
    first = invoke(environment, "sol", "--repo", repo, "--brief", brief, "--name", "a-bad")
    assert first.returncode == 0, first.stdout + first.stderr
    bad_run, bad_meta = last_run(environment)
    second = invoke(environment, "sol", "--repo", repo, "--brief", brief, "--name", "b-healthy")
    assert second.returncode == 0, second.stdout + second.stderr
    healthy_run = next(path.parent for path in bad_run.parent.glob("*/meta.json") if path.parent != bad_run)
    bad_worker = Path(bad_meta["worktree"])
    git(repo, "worktree", "remove", "--force", str(bad_worker))
    bad_worker.mkdir()
    for run in (bad_run, healthy_run):
        meta = json.loads((run / "meta.json").read_text())
        meta["ended_at"] = "2020-01-01T00:00:00+00:00"
        (run / "meta.json").write_text(json.dumps(meta))
    p = invoke(environment, "gc", "--older-than", "1e-9")
    assert p.returncode == 1, p.stdout + p.stderr
    assert f"gc {bad_meta['run']} failed:" in p.stderr
    assert "not registered" in p.stderr
    assert bad_worker.is_dir()
    assert not json.loads((bad_run / "meta.json").read_text()).get("gc_at")
    assert json.loads((healthy_run / "meta.json").read_text()).get("gc_at")
    assert f"gc {healthy_run.name}" in p.stdout


def test_r9_gc_present_repo_git_error_never_uses_direct_remover(repo, environment, monkeypatch):
    _, brief = environment
    p = invoke(environment, "sol", "--repo", repo, "--brief", brief)
    assert p.returncode == 0, p.stdout + p.stderr
    run, meta = last_run(environment)
    def fail_git(*args, **kwargs):
        raise RuntimeError("existing repo Git failed")
    monkeypatch.setattr(runner, "git", fail_git)
    with runner.pin_directory(run) as directory:
        with pytest.raises(RuntimeError, match="existing repo Git failed"):
            runner.gc_run(directory, meta)
    assert Path(meta["worktree"]).is_dir()
    assert not meta.get("worktree_removed")


def test_r9_gc_tmp_error_includes_macos_manual_recovery(tmp_path, monkeypatch):
    run = tmp_path / "run with spaces"
    run.mkdir()
    def fail_cleanup(directory):
        raise PermissionError("ACL prevents cleanup")
    monkeypatch.setattr(runner, "remove_child_tmp", fail_cleanup)
    with runner.pin_directory(run) as directory:
        with pytest.raises(RuntimeError) as error:
            runner.gc_run(directory, {"state": "ok", "run": "case"})
    message = str(error.value)
    assert "on macOS" in message
    assert "chmod -RN" in message and "chflags -R nouchg" in message
    assert "'" + str(run / "child/tmp") + "'" in message
    assert "rerun" in message
    saved = json.loads((run / "meta.json").read_text())["gc_tmp_error"]
    assert "ACL prevents cleanup" in saved
    assert "chmod -RN" in saved and "chflags -R nouchg" in saved
