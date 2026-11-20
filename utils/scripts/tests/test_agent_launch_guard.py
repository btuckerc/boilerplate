import json
import subprocess
import sys
from pathlib import Path

import pytest

GUARD = Path(__file__).resolve().parents[3] / "home/dot_local/bin/executable_agent-launch-guard"


def run(command, background=True, tool="Bash"):
    event = {"tool_name": tool, "tool_input": {"command": command, "run_in_background": background}}
    p = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event), capture_output=True, text=True)
    return p.returncode, p.stderr


@pytest.mark.parametrize("command", [
    "agent-run ask --model sol --brief b.md --timeout 1800 2>&1 | tail -3",
    "cd repo && agent-run sol --repo . --base HEAD --brief b.md > log 2>&1",
    "R=x; agent-run audit --repo . --packet p.md --candidate HEAD &>log",
    "timeout 3700 ~/.local/bin/agent-run --json ask --model sol --brief b.md",
    "for f in a b\ndo\n  test -f $f\ndone\nagent-run sol --repo . --brief b.md",
    "agent-run ask --name audit-nohup --model sol --brief b.md",
    "MODE=x timeout 30 agent-run ask --model sol --brief b.md",
    "agent-run ask --model sol --brief ~/nohup/b.md",
    "agent-run ask --name nohup --model sol --brief review/setsid/b.md",
    "agent-run ask --model sol --name x \\\n  --brief b.md",
    "command -v setsid >/dev/null && agent-run ask --model sol --brief b.md",
    "out=$(agent-run ask --model sol --brief \"R&D.md\")",
    "/opt/nohup/agent-run ask --model sol --brief b.md",
    "nohup true\nagent-run ask --model sol --brief b.md",
    "AGENT_RUN_HOME=$HOME/.local/state/nohup/agent-runs agent-run ask --model sol --brief b.md",
    "until [ $(agent-run list | wc -l) -lt 3 ]; do sleep 30; done; agent-run ask --model sol --brief b.md",
    "if ! agent-run ask --model sol --brief b.md; then echo failed; fi",
])
def test_one_background_launch_passes(command):
    assert run(command) == (0, "")


@pytest.mark.parametrize("command,background", [
    ("agent-run list; agent-run show ID; agent-run gc ID", False),
    ("agent-run ask --help", False),
    ("pgrep -af 'agent-run local' | wc -l", False),
    ("grep -n \"agent-run ask --model sol\" CLAUDE.md", False),
    ("python3 - <<'EOF'\ns = 'agent-run ask --model sol &'\nEOF\necho done", False),
    ("cat > brief.md <<EOF\nagent-run sol --repo . &\nfor s in a; do agent-run ask; done\nEOF", False),
    ("ls ~/.local/state/agent-runs/*-ask-x && sleep 1 &", False),
    ("printf '%s\\n' agent-run ask; echo agent-run sol", False),
    ("agent-run ask --help; true", False),
    ("# agent-run ask --model sol\nagent-run list", False),
    ("echo \"run agent-run ask later\"", False),
    ("setsid --fork sleep 1", False),
    ("cat <<'END-OF-TEXT'\nagent-run ask --model sol &\nEND-OF-TEXT", False),
    ("echo ready;# note; agent-run ask --model sol --brief b.md", False),
    ("echo see if agent-run ask works", False),
    ("echo check if agent-run ask is installed; command -v agent-run ask", False),
    ("\"/opt/backup-agent-run\" ask --model sol --brief b.md", False),
    ("echo $(date +%s) agent-run ask", False),
    ("echo Note! agent-run ask", False),
    ("echo \"Example: \\$(agent-run ask --brief b.md)\"", False),
    ("agent-run ask --brief \"$(printf %s b.md)\" --help", False),
    ("agent-run ask --model $seat --help", False),
    ("agent-run ask --brief $brief --help", False),
])
def test_non_launches_pass(command, background):
    assert run(command, background) == (0, "")


@pytest.mark.parametrize("command,background,reason", [
    ("agent-run ask --model sol --brief b.md", False, "run_in_background"),
    ("(agent-run ask --model sol --brief b.md > log 2>&1 &)", False, "detach"),
    ("nohup agent-run sol --repo . --brief b.md >log 2>&1", True, "detach"),
    ("agent-run local --repo . --brief b.md & disown", True, "detach"),
    ("for s in sol fable; do agent-run ask --model $s --brief b-$s.md; done", True, "one agent-run launch"),
    ("for i in $(seq 1 120); do out=$(agent-run ask --model sol --brief b.md 2>&1); sleep 60; done", True, "one agent-run"),
    ("agent-run ask --model sol --brief a.md; agent-run ask --model opus --brief b.md", True, "one agent-run"),
    ("for s in sol fable\ndo\n  agent-run ask --model $s --brief b.md\ndone", True, "one agent-run"),
    ("agent-run --json ask --model sol --brief b.md", False, "run_in_background"),
    ("/home/u/.local/bin/agent-run sol --repo . --brief b.md", False, "run_in_background"),
    ("agent-run ask --model sol --brief b.md; agent-run ask --help", False, "run_in_background"),
    ("result=\"$(agent-run ask --model sol --brief b.md)\"", False, "run_in_background"),
    ("~/.local/bin/agent-run ask --model sol --brief b.md &", True, "detach"),
    ("until agent-run ask --model sol --brief b.md; do sleep 60; done", True, "one agent-run"),
    ("while ! agent-run ask --model sol --brief b.md\ndo sleep 60\ndone", True, "one agent-run"),
    ("if ! agent-run ask --model sol --brief b.md; then echo x; fi", False, "run_in_background"),
    ("# don't wait here\nagent-run ask --model sol --brief 'b.md' &", True, "detach"),
    ("\"$HOME/.local/bin/agent-run\" ask --model sol --brief b.md", False, "run_in_background"),
    ("setsid --fork agent-run ask --model sol --brief b.md", True, "detach"),
    ("setsid -f agent-run ask --model sol --brief b.md", True, "detach"),
    ("/usr/bin/nohup agent-run ask --model sol --brief b.md", True, "detach"),
    ("env MODE=x nohup agent-run ask --model sol --brief b.md", True, "detach"),
    ("cat <<EOF\nEOF\nagent-run ask --model sol --brief b.md", False, "run_in_background"),
    ("printf '%s' \"result: $(agent-run ask --model sol --brief \"$brief\")\"", False, "run_in_background"),
    ("\"/opt/agent tools/agent-run\" ask --model sol --brief b.md", False, "run_in_background"),
    ("if true; then disown; fi; agent-run ask --model sol --brief b.md", True, "detach"),
    ("out=$(\"/opt/agent tools/agent-run\" ask --model sol --brief b.md)", False, "run_in_background"),
    ("printf '%s' \"$(agent-run ask --brief 'draft (rev 2).md' --model sol)\"", False, "run_in_background"),
    ("nohup env LABEL=$(date +%s) agent-run ask --model sol --brief b.md", True, "detach"),
    ("TAG=agent-run.log nohup agent-run ask --model sol --brief b.md", True, "detach"),
    ("result=\"$(agent-run ask --model sol --brief 'design (draft.md')\"", False, "run_in_background"),
    ("agent-\\\nrun ask --model sol --brief b.md", False, "run_in_background"),
    ("cat <<<EOF\nagent-run ask --model sol --brief b.md\ncat <<EOF\nbody\nEOF", False, "run_in_background"),
    ("result=\"$(agent-run ask --model sol --brief \"$brief\")\"", False, "run_in_background"),
    ("a=\"$(agent-run ask --brief \"$x\")\"; agent-run ask --brief b.md", True, "one agent-run"),
    ("for s in sol opus; do out=\"$(agent-run ask --model \"$s\" --brief \"brief-$s.md\")\"; done", True, "one agent-run"),
    ("agent-run \\\nask --model sol --brief b.md", False, "run_in_background"),
    ("timeout 3700 nohup agent-run ask --model sol --brief b.md", True, "detach"),
    ("agent-run ask --model sol --brief $(agent-run ask --model luna --brief a.md)", True, "one agent-run"),
    ("cat <<'EOF' >/dev/null && agent-run ask --model sol --brief b.md\nbody\nEOF", False, "run_in_background"),
])
def test_launches_that_cannot_notify_are_rejected(command, background, reason):
    code, err = run(command, background)
    assert code == 2 and reason in err


def test_background_must_be_the_boolean_true():
    for value in (1, "true", "false"):
        event = {"tool_name": "Bash", "tool_input": {"command": "agent-run ask --brief b.md", "run_in_background": value}}
        p = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event), capture_output=True, text=True)
        assert p.returncode == 2


def test_slow_inputs_finish_quickly():
    import time
    for command in ("echo '" + '"$(' * 9000 + "'", "timeout --help -- -1 " * 16 + "true", "x" * 200000,
                    "true;" * 20000 + "agent-run ask --brief b.md", "a=" + "b/" * 50000 + "c agent-run ask",
                    "agent-run " + "--json " * 25 + "list", "agent-run ask --brief b.md; echo " + "9" * 90000):
        start = time.monotonic()
        run(command)
        assert time.monotonic() - start < 2


def test_other_tools_and_bad_input_pass():
    assert run("agent-run ask --model sol", False, tool="Read") == (0, "")
    for bad in ("not json", "null", '{"tool_name": "Bash", "tool_input": {"command": 1}}',
                '{"tool_name": "Bash", "tool_input": ' + "[" * 10000 + "0" + "]" * 10000 + "}"):
        p = subprocess.run([sys.executable, str(GUARD)], input=bad, capture_output=True, text=True)
        assert p.returncode == 0, bad


@pytest.mark.parametrize("command", [
    "agy", "agy -p 'summarize this' --model gemini-4-neon-high", "~/.local/bin/agy acp",
    "cd repo && antigravity models", "timeout 60 agy -p hi", "out=$(agy -p hi)",
    "~/.local/share/antigravity-cli/current/antigravity --print hi",
])
def test_agy_is_never_launched_by_an_agent(command):
    for background in (False, True):
        code, err = run(command, background)
        assert code == 2 and "personal Google sign-in" in err


@pytest.mark.parametrize("command", [
    "agy --version", "~/.local/bin/agy --help", "agy changelog", "ls ~/.local/share/antigravity-cli/current/antigravity",
    "grep -n agy notes.md", "echo 'run agy yourself'", "cat ~/.gemini/antigravity/settings.json",
    "agy --version; agent-run list", "x/antigravity --version 2>&1 | head -5", "agy help > /tmp/h.txt",
])
def test_agy_mentions_and_harmless_flags_pass(command):
    assert run(command, False) == (0, "")
