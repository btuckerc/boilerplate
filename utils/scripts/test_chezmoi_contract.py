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
                              stdin=subprocess.DEVNULL, capture_output=True, text=True)

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

    def test_gemini_settings_and_hooks_merge_idempotently(self):
        import json
        home_src = Path(__file__).resolve().parents[2] / "home"
        def render(rel, text):
            result = subprocess.run([*self.base, "execute-template", "--with-stdin", "--file", str(home_src / rel)],
                                    input=text, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout

        seeded_settings = {"model": "Gemini 4 Neon", "trustedWorkspaces": ["/home/tux/hearth"],
                           "showTips": True, "showFeedbackSurvey": True,
                           "permissions": {"allow": ["command(git)"], "deny": ["command(rm -rf /)"]}}
        once = render("private_dot_gemini/private_antigravity-cli/modify_private_settings.json", json.dumps(seeded_settings))
        self.assertEqual(render("private_dot_gemini/private_antigravity-cli/modify_private_settings.json", once), once)
        parsed = json.loads(once)
        self.assertEqual(parsed["model"], "Gemini 4 Neon")
        self.assertEqual(parsed["trustedWorkspaces"], ["/home/tux/hearth"])
        self.assertEqual(parsed["agentMode"], "accept-edits")
        self.assertEqual(parsed["toolPermission"], "always-proceed")
        self.assertTrue(parsed["allowNonWorkspaceAccess"])
        self.assertTrue(parsed["showTips"])
        self.assertTrue(parsed["showFeedbackSurvey"])
        self.assertEqual(parsed["permissions"]["deny"], ["command(rm -rf /)"])
        self.assertIn("command(git)", parsed["permissions"]["allow"])
        self.assertIn("read_file(*)", parsed["permissions"]["allow"])
        self.assertIn("write_file(*)", parsed["permissions"]["allow"])
        # Empty / fresh file and malformed permissions shapes never abort.
        fresh = json.loads(render("private_dot_gemini/private_antigravity-cli/modify_private_settings.json", ""))
        self.assertEqual(fresh["permissions"]["allow"], ["read_file(*)", "write_file(*)"])
        self.assertNotIn("showTips", fresh)
        self.assertNotIn("showFeedbackSurvey", fresh)
        for broken in ({"permissions": "bad"}, {"permissions": {"allow": "bad"}}):
            self.assertEqual(json.loads(render("private_dot_gemini/private_antigravity-cli/modify_private_settings.json",
                                               json.dumps(broken)))["permissions"], broken["permissions"])
        # UTF-8 BOM-prefixed JSON files (accepted by Antigravity 1.5.13) converge cleanly and stay idempotent.
        bom_settings = "\ufeff" + once
        self.assertEqual(render("private_dot_gemini/private_antigravity-cli/modify_private_settings.json", bom_settings), bom_settings)
        bom_fresh = json.loads(render("private_dot_gemini/private_antigravity-cli/modify_private_settings.json",
                                      "\ufeff" + json.dumps({"model": "custom"})))
        self.assertEqual(bom_fresh["model"], "custom")
        self.assertEqual(bom_fresh["toolPermission"], "always-proceed")

        seeded_hooks = {"herdr": {"PreInvocation": [{"type": "command", "command": "herdr-state", "timeout": 10}]}}
        hooks_once = render("private_dot_gemini/private_config/modify_hooks.json", json.dumps(seeded_hooks))
        self.assertEqual(render("private_dot_gemini/private_config/modify_hooks.json", hooks_once), hooks_once)
        bom_hooks = "\ufeff" + hooks_once
        self.assertEqual(render("private_dot_gemini/private_config/modify_hooks.json", bom_hooks), bom_hooks)
        parsed_hooks = json.loads(hooks_once)
        self.assertEqual(parsed_hooks["herdr"], seeded_hooks["herdr"])
        guard_hooks = parsed_hooks["agent-launch-guard"]["PreToolUse"]
        self.assertEqual(guard_hooks[0]["matcher"], "run_command")
        self.assertTrue(guard_hooks[0]["hooks"][0]["command"].endswith("/.local/bin/agent-launch-guard"))

        # skills.json.tmpl uses an absolute path (no ~) and excludes .no-claude skills.
        skills_cmd = [self.base[0], "--source", str(home_src), "--destination", str(self.dest),
                      "--config", str(self.root / "config.toml"), "--persistent-state", str(self.root / "state.db"),
                      "execute-template", "--file", str(home_src / "private_dot_gemini/private_config/skills.json.tmpl")]
        skills_res = subprocess.run(skills_cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True)
        self.assertEqual(skills_res.returncode, 0, skills_res.stderr)
        skills_cfg = json.loads(skills_res.stdout)
        entry = skills_cfg["entries"][0]
        self.assertTrue(entry["path"].startswith("/") and "~" not in entry["path"])
        self.assertTrue(entry["path"].endswith("/.local/share/decent-angl/skills"))
        self.assertIn("local-workers", entry["exclude"])
        self.assertIn("omp-drive", entry["exclude"])

    def test_agent_host_removes_retired_acp_helper_and_ignores_gemini_runtime_state(self):
        repo_root = Path(__file__).resolve().parents[2]
        agent_cfg = self.root / "nous.toml"
        agent_cfg.write_text('[data.decentangl]\nmachine_id = "nous"\n')
        cmd = [self.base[0], "--source", str(repo_root), "--destination", str(self.dest),
               "--config", str(agent_cfg), "--persistent-state", str(self.root / "nous-state.db")]
        # Seed retired helper and sensitive Antigravity runtime files.
        retired = self.dest / ".local/bin/agent-run-acp"
        retired.parent.mkdir(parents=True, exist_ok=True)
        retired.write_text("#!/usr/bin/env python3\n")
        retired.chmod(0o755)
        token = self.dest / ".gemini/antigravity-cli/antigravity-oauth-token"
        token.parent.mkdir(parents=True, exist_ok=True)
        token.write_text("secret-token\n")
        install_id = self.dest / ".gemini/antigravity-cli/installation_id"
        install_id.write_text("id-123\n")
        # 1) Prove the agent-host allowlist actually ran (hearth included, workstation rc excluded)
        #    and that all four managed .gemini files are managed while runtime/auth files are ignored.
        managed = set(subprocess.run([*cmd, "managed", "--include=files"], stdin=subprocess.DEVNULL,
                                     capture_output=True, text=True, check=True).stdout.splitlines())
        self.assertIn("hearth/AGENTS.md", managed)
        self.assertNotIn(".bashrc", managed)
        for expected in (".gemini/GEMINI.md", ".gemini/antigravity-cli/settings.json",
                         ".gemini/config/hooks.json", ".gemini/config/skills.json"):
            self.assertIn(expected, managed)
        unmanaged = set(subprocess.run([*cmd, "unmanaged", str(self.dest / ".gemini")], stdin=subprocess.DEVNULL,
                                       capture_output=True, text=True, check=True).stdout.splitlines())
        self.assertNotIn(".gemini/antigravity-cli/antigravity-oauth-token", unmanaged)
        self.assertNotIn(".gemini/antigravity-cli/installation_id", unmanaged)
        # 2) Retired agent-run-acp is scheduled for removal under agent-host role and removed on apply.
        removable = set(subprocess.run([*cmd, "managed", "--include=remove"], stdin=subprocess.DEVNULL,
                                       capture_output=True, text=True, check=True).stdout.splitlines())
        self.assertIn(".local/bin/agent-run-acp", removable)
        applied = subprocess.run([*cmd, "apply", "--no-tty", "--exclude", "scripts,dirs",
                                  str(retired)], stdin=subprocess.DEVNULL, capture_output=True, text=True)
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertFalse(retired.exists())

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
