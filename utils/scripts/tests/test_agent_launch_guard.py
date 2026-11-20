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
    ("agent-run ask --brief brief.md >|/dev/null --help", False),
    ("agent-run ask 2>&1 --help", False),
    ("cat <<'EOF'\n EOF\nagy\nEOF\n", False),
    ("cat <<EOF\nEOF\r\nantigravity models\nEOF\n", False),
    ("cat <<A <<B\nA\nantigravity models\nB\n", False),
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
    ("command agent-run ask --model sol --brief b.md", False, "run_in_background"),
    ("/agent-run ask --brief b.md &", True, "detach"),
    ("agent-run>|/dev/null ask --model sol --brief b.md &", True, "detach"),
    ("agent-run ask --model sol --brief b.md <<< --help &", True, "detach"),
    ("echo $(agent-run ask --model sol --brief b.md) $(agent-run ask --model sol --brief a.md) --help", True, "one agent-run"),
    ("LABEL=$(agent-run ask --model sol --brief inner.md) agent-run ask --model sol --brief outer.md", True, "one agent-run"),
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
    cases = (
        ("echo '" + '"$(' * 9000 + "'", 0),
        ("timeout --help -- -1 " * 16 + "true", 0),
        ("x" * 200000, 0),
        ("true;" * 20000 + "agent-run ask --brief b.md", 0),
        ("a=" + "b/" * 50000 + "c agent-run ask", 0),
        ("agent-run " + "--json " * 25 + "list", 0),
        ("agent-run ask --brief b.md; echo " + "9" * 90000, 0),
        ("mise " + "exec " * 5000 + "true", 0),
        ("mise " + "-C a " * 5000 + "true", 0),
        ("X=/env " * 40 + "true", 0), ("X=/mise " * 40 + "true", 0), ("X=/nohup " * 40 + "true", 0),
        ("nice -/exec " * 40 + "true", 0), ("env -/env " * 40 + "true", 0),
        ("<<< " * 40 + "true", 0), (">>>a " * 40 + "true", 0),
        ("mise exec -- " * 40 + "true", 0), ("mise -C x " * 40 + "true", 0),
        ("mise exec mise exec -- " * 40 + "true", 0), ("env -u a " * 40 + "true", 0),
        ("antigravity " + "0" * 5000 + "<&0 " * 40 + "-p", 2),
        (": `agy -h`; " * 10000, 0), ("&>/dev/null " * 8000 + "true", 0),
        ("antigravity --version " + "1" * 50000, 2),
        (": " + "$(true) " * 80000, 0), ("$(" * 2000 + "true" + ")" * 2000, 0),
        (": " + "{a[ " * 20000, 0),
        ("(" * 4200 + ": $(true)\n" * 20000 + ")" * 4200, 0),
        ("agent-run ask;" * 8000, 2),
        ("printf '%s' '" + "text <<EOF\n" * 8000 + "'", 0),
        ("\n" * 8000 + ":", 0),
        ("agy --help " + "<" * 20000, 2),
        ("agent-run >/dev/null" + "&>/dev/null" * 30 + " list", 0),
        ("echo " + "$(agent-run ask --model=sol --brief=b) " * 3300, 2),
        ("x=$(printf %s " + '\\"' * 32000 + ")", 0),
    )
    for command, expected in cases:
        start = time.monotonic()
        code, err = run(command)
        assert time.monotonic() - start < 2
        assert code == expected and "Traceback" not in err


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
    "\"$HOME/.local/bin/agy\" -p hi", "'/usr/local/bin/antigravity' acp",
    "command antigravity models", "command -p -- agy -p hi",
    "mise exec -- antigravity models", "mise -C \"$HOME\" x -- agy -p hi",
    "\"$HOME/.local/bin/mise\" exec -- antigravity -p hi",
    "$(mise which antigravity) -p hi", "\"$(mise which antigravity)\" acp",
    "out=$(mise exec -- antigravity -p hi)", "$(command -v agy) -p hi",
    "antigravity>/dev/null -p hi", "command antigravity>/dev/null -p hi",
    "mise exec -- antigravity>/dev/null -p hi",
    "</dev/null antigravity -p hi", "2>/dev/null agy -p hi",
    "2>/tmp/example\\ log antigravity models", "2>/dev/null>/dev/null antigravity models",
    "2>|/dev/null antigravity models",
    "env -u CLAUDECODE agy -p hi", "env --unset=AGENT_RUN_PARENT --unset CLAUDECODE agy -p hi",
    "env -u \"EXAMPLE\" antigravity models", "env --unset='EXAMPLE' antigravity models",
    "env -u FOO> /dev/null antigravity models", "env ->/dev/null antigravity models",
    "mise exec -->/dev/null antigravity models", "env \"--unset=$(antigravity models)\" agy --help",
    "antigravity --version >/tmp/example\\ #log models",
    "env \"--unset=EXAMPLE\" agy -p hi", "env \"--unset=$(printf EXAMPLE)\" agy models", "env '-u' CLAUDECODE agy -p hi",
    "env -u \"$(printf CLAUDECODE)\" agy -p hi", "env -u $(printf $(printf EXAMPLE)) agy -p hi",
    "env - agy -p hi", "LABEL=\"demo\" antigravity models", "LABEL=demo> /dev/null antigravity models",
    "printf '%s\\n' '<<EOF'\nantigravity models\nEOF",
    "cat <<true/EOF\ntrue/EOF\nagy\ntrue",
    "/agy models", "/tmp/x=y/agy models",
    "antigravity --version 2>&1 -p hi", "antigravity --version2>/dev/null", "mise exec -- antigravity --version <(true) -p hi",
    "antigravity --version >/dev/null`true` models", "antigravity --version >/dev/null$(true) models",
    "echo \"`echo \\`true\\``\"; antigravity --version >/dev/null`true` models",
    "antigravity --version >/dev/null\\) models", "antigravity --version >/dev/null\\; models",
    "antigravity --version >/dev/null\\`true\\` models", "echo `antigravity`", "antigravity`true` models",
    "agy -v", "agy help acp",
])
def test_agy_is_never_launched_by_an_agent(command):
    for background in (False, True):
        code, err = run(command, background)
        assert code == 2 and "personal Google sign-in" in err and "--model neon" not in err


@pytest.mark.parametrize("command", [
    "agy --version", "agy '--version'", "~/.local/bin/agy --help", "agy -h", "agy help", "agy changelog",
    "mise -C \"$HOME\" exec -- antigravity --version",
    "version=$(mise exec -- antigravity --version)", "echo `agy --version`",
    "antigravity>/dev/null --version", "antigravity --version>/dev/null",
    "antigravity --version 2>/tmp/example\\ log", "agy --help 2>/dev/null> /dev/null",
    "agy --help >|/dev/null", ": > \"$(which agy)\"",
    "cat <<'EOF'\n$(antigravity models)\nEOF",
    "env -u CLAUDECODE agy --version", "env -u \"EXAMPLE\" agy --version", "</dev/null antigravity --version",
    "X=/agy true", "$(mise which antigravity) --version", "command -v agy",
    "bin=$(mise which antigravity)", "echo $(mise which antigravity)",
    "ls ~/.local/share/antigravity-cli/current/antigravity",
    "grep -n agy notes.md", "echo 'run agy yourself'", "cat ~/.gemini/antigravity/settings.json",
    "agy --version; agent-run list", "x/antigravity --version 2>&1 | head -5", "agy help > /tmp/h.txt",
])
def test_agy_mentions_and_harmless_flags_pass(command):
    assert run(command, False) == (0, "")


def run_agy_hook(command, tool="run_command"):
    event = {"hookEventName": "PreToolUse", "toolCall": {"id": "t1", "name": tool, "args": {"CommandLine": command}}}
    p = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event), capture_output=True, text=True)
    assert p.returncode == 0 and p.stderr == ""
    return json.loads(p.stdout)


def test_antigravity_pretooluse_contract():
    assert run_agy_hook("agent-run ask --model sol --brief b.md") == {"decision": "allow"}
    assert run_agy_hook("agy --version") == {"decision": "allow"}
    assert run_agy_hook("agy '--version'") == {"decision": "allow"}
    assert run_agy_hook("antigravity --version 2>/tmp/example\\ log") == {"decision": "allow"}
    assert run_agy_hook("agy --help 2>/dev/null> /dev/null") == {"decision": "allow"}
    assert run_agy_hook("agy --help >|/dev/null") == {"decision": "allow"}
    assert run_agy_hook(": > \"$(which agy)\"") == {"decision": "allow"}
    assert run_agy_hook("agy help") == {"decision": "allow"}
    assert run_agy_hook("agy changelog") == {"decision": "allow"}
    assert run_agy_hook("mise -C \"$HOME\" exec -- antigravity --version") == {"decision": "allow"}
    assert run_agy_hook("version=$(mise exec -- antigravity --version)") == {"decision": "allow"}
    assert run_agy_hook("antigravity>/dev/null --version") == {"decision": "allow"}
    assert run_agy_hook("antigravity --version>/dev/null") == {"decision": "allow"}
    assert run_agy_hook("env -u CLAUDECODE agy --version") == {"decision": "allow"}
    assert run_agy_hook("agy -p hi", tool="read_file") == {"decision": "allow"}
    for cmd, snippet in (
        ("agy -p 'hi'", "personal Google sign-in"),
        ("\"/home/tux/.local/bin/agy\" acp", "personal Google sign-in"),
        ("command antigravity models", "personal Google sign-in"),
        ("mise exec -- antigravity models", "personal Google sign-in"),
        ("\"$HOME/.local/bin/mise\" exec -- antigravity -p hi", "personal Google sign-in"),
        ("out=$(mise exec -- antigravity -p hi)", "personal Google sign-in"),
        ("antigravity>/dev/null -p hi", "personal Google sign-in"),
        ("mise exec -- antigravity>/dev/null -p hi", "personal Google sign-in"),
        ("</dev/null antigravity -p hi", "personal Google sign-in"),
        ("2>/tmp/example\\ log antigravity models", "personal Google sign-in"),
        ("2>|/dev/null antigravity models", "personal Google sign-in"),
        ("env -u CLAUDECODE agy -p hi", "personal Google sign-in"),
        ("env -u \"EXAMPLE\" antigravity models", "personal Google sign-in"),
        ("env -u FOO> /dev/null antigravity models", "personal Google sign-in"),
        ("env ->/dev/null antigravity models", "personal Google sign-in"),
        ("mise exec -->/dev/null antigravity models", "personal Google sign-in"),
        ("env \"--unset=$(antigravity models)\" agy --help", "personal Google sign-in"),
        ("antigravity --version >/tmp/example\\ #log models", "personal Google sign-in"),
        ("LABEL=$(agent-run ask --model sol --brief inner.md) agent-run ask --model sol --brief outer.md", "one agent-run"),
        ("env --unset='EXAMPLE' antigravity models", "personal Google sign-in"),
        ("env \"--unset=EXAMPLE\" agy -p hi", "personal Google sign-in"),
        ("env \"--unset=$(printf EXAMPLE)\" agy models", "personal Google sign-in"),
        ("env -u $(printf $(printf EXAMPLE)) agy -p hi", "personal Google sign-in"),
        ("env - agy -p hi", "personal Google sign-in"),
        ("LABEL=\"demo\" antigravity models", "personal Google sign-in"),
        ("LABEL=demo> /dev/null antigravity models", "personal Google sign-in"),
        ("printf '%s\\n' '<<EOF'\nantigravity models\nEOF", "personal Google sign-in"),
        ("cat <<true/EOF\ntrue/EOF\nagy\ntrue", "personal Google sign-in"),
        ("agent-run>|/dev/null ask --model sol --brief b.md &", "detach"),
        ("/agy models", "personal Google sign-in"),
        ("/tmp/x=y/agy models", "personal Google sign-in"),
        ("antigravity --version 2>&1 -p hi", "personal Google sign-in"),
        ("antigravity --version2>/dev/null", "personal Google sign-in"),
        ("mise exec -- antigravity --version <(true) -p hi", "personal Google sign-in"),
        ("antigravity --version >/dev/null`true` models", "personal Google sign-in"),
        ("antigravity --version >/dev/null$(true) models", "personal Google sign-in"),
        ("echo \"`echo \\`true\\``\"; antigravity --version >/dev/null`true` models", "personal Google sign-in"),
        ("antigravity --version >/dev/null\\) models", "personal Google sign-in"),
        ("antigravity --version >/dev/null\\; models", "personal Google sign-in"),
        ("\"$(mise which antigravity)\" -p hi", "personal Google sign-in"),
        ("/agent-run ask --brief b.md &", "detach"),
        ("agent-run ask --model sol --brief b.md <<< --help &", "detach"),
        ("agent-run ask --model sol --brief a.md; agent-run ask --model opus --brief b.md", "one agent-run launch"),
        ("nohup agent-run ask --model sol --brief b.md", "detach"),
    ):
        res = run_agy_hook(cmd)
        assert res["decision"] == "deny" and snippet in res["reason"]


def test_agy_wrapper_refuses_agent_sessions(tmp_path):
    wrapper = Path(__file__).resolve().parents[3] / "home/dot_local/bin/executable_agy"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    real = tmp_path / "fake-antigravity"
    real.write_text("#!/bin/sh\nprintf 'ran:%s\\n' \"$*\"\n")
    real.chmod(0o755)
    mise = fake_bin / "mise"
    mise.write_text(f"#!/bin/sh\necho '{real}'\n")
    mise.chmod(0o755)
    base_env = {"PATH": f"{fake_bin}:/usr/bin:/bin", "HOME": str(tmp_path)}
    no_mise_env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}
    markers = ("AGENT_RUN_PARENT", "AGENT_RUN_CHILD", "ANTIGRAVITY_CONVERSATION_ID",
               "CLAUDE_CODE_SESSION_ID", "CLAUDECODE", "PI_SESSION_FILE", "OMPCODE",
               "CODEX_THREAD_ID", "CODEX_SANDBOX", "CODEX_SANDBOX_NETWORK_DISABLED")
    for marker in markers:
        for val in ("1", ""):
            p = subprocess.run(["sh", str(wrapper), "-p", "hi"], env={**no_mise_env, marker: val},
                               capture_output=True, text=True)
            assert p.returncode == 126 and "refusing to run inside an agent session" in p.stderr
    for disallowed in (["-v"], ["help", "acp"]):
        p = subprocess.run(["sh", str(wrapper), *disallowed], env={**base_env, "AGENT_RUN_PARENT": "agy"},
                           capture_output=True, text=True)
        assert p.returncode == 126
    for ok_flag in ("--version", "--help", "-h", "help", "changelog"):
        p = subprocess.run(["sh", str(wrapper), ok_flag], env={**base_env, "AGENT_RUN_PARENT": "agy"},
                           capture_output=True, text=True)
        assert p.returncode == 0 and p.stdout.strip() == f"ran:{ok_flag}"
    p = subprocess.run(["sh", str(wrapper), "models"], env=base_env, capture_output=True, text=True)
    assert p.returncode == 0 and p.stdout.strip() == "ran:models"
