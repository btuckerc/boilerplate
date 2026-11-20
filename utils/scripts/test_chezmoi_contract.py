#!/usr/bin/env python3
"""Check assumptions about chezmoi against the installed, pinned executable."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class ChezmoiContract(unittest.TestCase):
    def setUp(self):
        binary = os.environ.get("CHEZMOI_TEST_BIN")
        if not binary and shutil.which("mise"):
            result = subprocess.run(["mise", "which", "chezmoi"], capture_output=True, text=True)
            if result.returncode == 0:
                binary = result.stdout.strip()
        binary = binary or shutil.which("chezmoi")
        if not binary:
            self.skipTest("chezmoi unavailable")
        self.tmp = tempfile.TemporaryDirectory(prefix="chezmoi-contract-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source, self.dest = self.root / "source", self.root / "dest"
        self.source.mkdir()
        self.dest.mkdir()
        (self.root / "config.toml").write_text("")
        self.base = [binary, "--source", str(self.source), "--destination", str(self.dest),
                     "--config", str(self.root / "config.toml"), "--persistent-state", str(self.root / "state.db")]

    def apply(self):
        return subprocess.run([*self.base, "apply", "--exclude", "scripts", "--no-tty"],
                              capture_output=True, text=True)

    def test_claude_settings_merge_keeps_other_hooks_and_adds_the_guard_once(self):
        import json
        template = Path(__file__).resolve().parents[2] / "home/private_dot_claude/modify_settings.json"
        def render(text):
            result = subprocess.run([*self.base, "execute-template", "--with-stdin", "--file", str(template)],
                                    input=text, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout
        seeded = {"hooks": {"SessionStart": [{"hooks": [{"command": "herdr session", "type": "command"}]}],
                            "PreToolUse": [{"matcher": "Edit", "hooks": [{"command": "other", "type": "command"}]},
                                           {"matcher": "Write", "hooks": [{"command": str(Path.home() / ".local/bin/agent-launch-guard"),
                                                                            "type": "command"}]}]}}
        once = render(json.dumps(seeded))
        self.assertEqual(render(once), once)
        hooks = json.loads(once)["hooks"]
        self.assertEqual(hooks["SessionStart"], seeded["hooks"]["SessionStart"])
        commands = [h["command"] for entry in hooks["PreToolUse"] for h in entry["hooks"]]
        self.assertEqual(commands.count("other"), 1)
        bash = [h["command"] for entry in hooks["PreToolUse"] if entry["matcher"] == "Bash" for h in entry["hooks"]]
        self.assertEqual([c.endswith("/.local/bin/agent-launch-guard") for c in bash], [True])
        for covering in ("Bash|Write", "Bash | Write", "*"):  # already covers Bash: left alone
            seeded["hooks"]["PreToolUse"][1]["matcher"] = covering
            self.assertEqual(json.loads(render(json.dumps(seeded)))["hooks"], seeded["hooks"])
        seeded["hooks"]["PreToolUse"][1]["matcher"] = "^mcp__.*(Read|Bash)$"  # does not match Bash
        self.assertEqual(len(json.loads(render(json.dumps(seeded)))["hooks"]["PreToolUse"]), 3)
        odd = {"hooks": {"PreToolUse": [{"matcher": 7, "hooks": []}, None, {"matcher": "(?!Ask).*", "hooks": [None]},
                                        {"matcher": "Bash", "hooks": [{"command": 123}]},
                                        {"matcher": False, "hooks": [{"command": str(Path.home() / ".local/bin/agent-launch-guard")}]}]}}
        self.assertEqual(len(json.loads(render(json.dumps(odd)))["hooks"]["PreToolUse"]), 6)  # renders, adds one
        for broken in ("oops", {"0": {"matcher": "Read", "hooks": []}}, [{"matcher": "Bash", "hooks": "oops"}],
                       [{"matcher": "Bash", "hooks": [{"type": 5, "command": "x"}]}]):
            render(json.dumps({"hooks": {"PreToolUse": broken}}))  # never aborts
        for kept in ({"hooks": {"PreToolUse": False}}, {"hooks": False}):  # non-list values are left as they are
            self.assertEqual(json.loads(render(json.dumps(kept)))["hooks"], kept["hooks"])
        seeded["hooks"]["PreToolUse"][1]["matcher"] = "^mcp__(Read|Bash|Write)$"  # a regex naming mcp__Bash only
        self.assertEqual(len(json.loads(render(json.dumps(seeded)))["hooks"]["PreToolUse"]), 3)

    def test_excluding_scripts_still_installs_executable_files(self):
        (self.source / "executable_helper").write_text("#!/bin/sh\necho helper\n")
        (self.source / "run_once_hook").write_text("#!/bin/sh\nexit 43\n")
        result = self.apply()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(os.access(self.dest / "helper", os.X_OK))

    def test_conflicting_live_edit_is_preserved_without_force(self):
        (self.source / "dot_example").write_text("initial\n")
        self.assertEqual(self.apply().returncode, 0)
        (self.dest / ".example").write_text("local edit\n")
        (self.source / "dot_example").write_text("published change\n")
        self.apply()
        self.assertEqual((self.dest / ".example").read_text(), "local edit\n")

    def test_managed_directory_list_uses_nul_separator(self):
        (self.source / 'dot_nested').mkdir()
        (self.source / 'dot_nested/example').write_text('fixture\n')
        result = subprocess.run([*self.base, 'managed', '--include', 'dirs',
                                 '--path-style', 'absolute', '--nul-path-separator'],
                                capture_output=True, check=True)
        self.assertEqual(result.stdout.split(bytes([0])),
                         [os.fsencode(self.dest / '.nested'), b''])


if __name__ == "__main__":
    unittest.main()
