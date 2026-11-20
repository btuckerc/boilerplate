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
])
def test_launches_that_cannot_notify_are_rejected(command, background, reason):
    code, err = run(command, background)
    assert code == 2 and reason in err


def test_other_tools_and_bad_input_pass():
    assert run("agent-run ask --model sol", False, tool="Read") == (0, "")
    p = subprocess.run([sys.executable, str(GUARD)], input="not json", capture_output=True, text=True)
    assert p.returncode == 0
