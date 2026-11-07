#!/usr/bin/env python3
"""decent-angl-skills treats failed output-producing probes as errors."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "home/dot_local/bin/executable_decent-angl-skills"
REAL_READLINK = shutil.which("readlink")
REAL_UNAME = shutil.which("uname")
REAL_FIND = shutil.which("find")


class DecentAnglSkillsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="decent-angl-skills-test-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.home = self.root / "home"
        self.repo = self.root / "repo"
        self.source = self.repo / "source"
        self.canonical = self.home / "canonical"
        self.render = self.home / "render"
        self.codex = self.home / "codex"
        self.omp = self.home / "omp"
        # Managed roots must sit below HOME or /tmp (macOS TMPDIR is neither).
        self.state = self.home / "state"
        self.bin = self.root / "bin"
        for path in (self.home, self.source, self.canonical, self.render,
                     self.codex, self.omp, self.state, self.bin):
            path.mkdir(parents=True, exist_ok=True)
        self.skill = self.source / "demo"
        self.skill.mkdir()
        self.skill_file = self.skill / "SKILL.md"
        self.skill_file.write_text("---\nname: demo\ndescription: d\n---\nbody\n")
        canonical_skill = self.canonical / "demo"
        canonical_skill.mkdir()
        (canonical_skill / "SKILL.md").write_text(self.skill_file.read_text())
        self.env = {
            "HOME": str(self.home),
            "PATH": f"{self.bin}{os.pathsep}/usr/bin{os.pathsep}/bin",
            "DECENT_ANGL_REPO_ROOT": str(self.repo),
            "DECENT_ANGL_SKILL_SOURCE_ROOT": str(self.source),
            "DECENT_ANGL_SKILL_ROOT": str(self.canonical),
            "DECENT_ANGL_SKILL_RENDER_ROOT": str(self.render),
            "DECENT_ANGL_CODEX_SKILL_ROOT": str(self.codex),
            "DECENT_ANGL_OMP_SKILL_ROOT": str(self.omp),
            "XDG_STATE_HOME": str(self.state),
        }

    def run_script(self, *args, **extra):
        return subprocess.run(["bash", str(SCRIPT), *args], env={**self.env, **extra},
                              capture_output=True, text=True, timeout=30)

    def sync_and_validate(self):
        synced = self.run_script("sync")
        self.assertEqual(0, synced.returncode, synced.stderr)
        result = self.run_script("validate")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("SKILL  live ok 1 skill(s)", result.stdout)
        return result

    def install_shim(self, name, body):
        shim = self.bin / name
        shim.write_text("#!/bin/sh\n" + body + "\n")
        shim.chmod(0o755)

    def test_validate_control(self):
        self.sync_and_validate()

    def test_no_claude_marker_withdraws_only_the_claude_link(self):
        self.sync_and_validate()
        claude_link = self.home / ".claude/skills/demo"
        self.assertEqual(str(self.canonical / "demo"), os.readlink(claude_link))
        (self.skill / ".no-claude").write_text("")
        self.sync_and_validate()
        self.assertFalse(claude_link.is_symlink())
        self.assertTrue((self.omp / "demo").is_symlink())
        self.assertTrue((self.codex / "demo").is_symlink())
        claude_link.symlink_to(self.canonical / "demo")
        result = self.run_script("validate")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("live Claude link for .no-claude skill: demo", result.stderr)

    def test_validate_rejects_untracked_managed_claude_link(self):
        self.sync_and_validate()
        stale = self.home / ".claude/skills/retired-demo"
        stale.symlink_to(self.canonical / "demo")
        result = self.run_script("validate")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("SKILL  live Claude link stale: retired-demo", result.stderr)

    def test_sync_removes_untracked_managed_claude_link(self):
        self.sync_and_validate()
        stale = self.home / ".claude/skills/retired-demo"
        stale.symlink_to(self.render / "codex/demo")
        result = self.run_script("sync")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse(stale.is_symlink())
        self.assertEqual(0, self.run_script("validate").returncode)

    def test_validate_rejects_relative_untracked_managed_claude_link(self):
        self.sync_and_validate()
        stale = self.home / ".claude/skills/retired-demo"
        stale.symlink_to("../../canonical/demo")
        result = self.run_script("validate")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("SKILL  live Claude link stale: retired-demo", result.stderr)

    def test_sync_removes_relative_untracked_managed_claude_link(self):
        self.sync_and_validate()
        stale = self.home / ".claude/skills/retired-demo"
        stale.symlink_to("../../canonical/demo")
        result = self.run_script("sync")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse(stale.is_symlink())

    def test_validate_ignores_absolute_target_outside_managed_root(self):
        self.sync_and_validate()
        outside = self.home / "outside-dir"
        outside.mkdir()
        stale = self.home / ".claude/skills/user-link"
        stale.symlink_to(self.canonical / ".." / "outside-dir")
        result = self.run_script("validate")
        self.assertEqual(0, result.returncode, result.stderr)
        synced = self.run_script("sync")
        self.assertEqual(0, synced.returncode, synced.stderr)
        self.assertTrue(stale.is_symlink())
        self.assertEqual(str(self.canonical / ".." / "outside-dir"), os.readlink(stale))

    def test_validate_rejects_untracked_link_through_managed_root_alias(self):
        self.sync_and_validate()
        alias = self.home / "canonical-alias"
        alias.symlink_to(self.canonical, target_is_directory=True)
        stale = self.home / ".claude/skills/retired-demo"
        stale.symlink_to(alias / "demo")
        result = self.run_script("validate")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("SKILL  live Claude link stale: retired-demo", result.stderr)

    def test_dot_dot_after_symlinked_component_follows_the_symlink_first(self):
        # alias/../<canonical name>/demo really lives under outside/, not under the managed root.
        self.sync_and_validate()
        nested = self.home / "outside/nested"
        nested.mkdir(parents=True)
        alias = self.home / "alias"
        alias.symlink_to(nested, target_is_directory=True)
        target = f"{alias}/../{self.canonical.name}/demo"
        self.assertEqual(self.home, self.canonical.parent)
        user = self.home / ".claude/skills/user-link"
        user.symlink_to(target)
        result = self.run_script("validate")
        self.assertEqual(0, result.returncode, result.stderr)
        synced = self.run_script("sync")
        self.assertEqual(0, synced.returncode, synced.stderr)
        self.assertEqual(target, os.readlink(user))

    def test_retired_owned_name_keeps_link_retargeted_outside_managed_roots(self):
        retired = self.source / "retired"
        canonical_retired = self.canonical / "retired"
        for path in (retired, canonical_retired):
            path.mkdir()
            (path / "SKILL.md").write_text("---\nname: retired\ndescription: d\n---\nbody\n")
        synced = self.run_script("sync")
        self.assertEqual(0, synced.returncode, synced.stderr)
        link = self.home / ".claude/skills/retired"
        self.assertTrue(link.is_symlink())
        shutil.rmtree(retired)
        (self.home / "user-skill").mkdir()
        link.unlink()
        target = f"{self.canonical}/../user-skill"
        link.symlink_to(target)
        synced = self.run_script("sync")
        self.assertEqual(0, synced.returncode, synced.stderr)
        self.assertEqual(target, os.readlink(link))

    def test_current_name_linked_outside_managed_roots_is_a_collision(self):
        self.sync_and_validate()
        (self.home / "user-skill").mkdir()
        link = self.home / ".claude/skills/demo"
        link.unlink()
        target = f"{self.canonical}/../user-skill"
        link.symlink_to(target)
        synced = self.run_script("sync")
        self.assertNotEqual(0, synced.returncode)
        self.assertIn("SKILL  collision", synced.stderr)
        self.assertEqual(target, os.readlink(link))

    def assert_unmanaged_link_kept(self, target):
        self.sync_and_validate()
        link = self.home / ".claude/skills/user-link"
        link.symlink_to(target)
        validated = self.run_script("validate")
        self.assertEqual(0, validated.returncode, validated.stderr)
        synced = self.run_script("sync")
        self.assertEqual(0, synced.returncode, synced.stderr)
        self.assertEqual(target, os.readlink(link))

    def test_link_target_with_embedded_newline_is_unmanaged(self):
        (self.home / f"{self.canonical.name}\n").mkdir()
        (self.home / "user-skill").mkdir()
        self.assert_unmanaged_link_kept(f"{self.canonical}\n/../user-skill")

    def test_link_target_with_trailing_newline_is_unmanaged(self):
        (self.home / f"{self.canonical.name}\n").mkdir()
        self.assert_unmanaged_link_kept(f"{self.canonical}\n")

    def test_link_through_alias_of_newline_directory_is_unmanaged(self):
        newline_dir = self.home / f"{self.canonical.name}\n"
        newline_dir.mkdir()
        (newline_dir / "user-skill").mkdir()
        alias = self.home / "alias"
        alias.symlink_to(newline_dir)
        self.assert_unmanaged_link_kept(f"{alias}/user-skill")

    def assert_stale_link_removed(self, link, target):
        self.sync_and_validate()
        link.symlink_to(target)
        validated = self.run_script("validate")
        self.assertNotEqual(0, validated.returncode)
        self.assertIn("link stale", validated.stderr)
        synced = self.run_script("sync")
        self.assertEqual(0, synced.returncode, synced.stderr)
        self.assertFalse(os.path.lexists(link))

    def test_newline_target_resolving_into_canonical_is_stale(self):
        (self.home / "staging\n").mkdir()
        self.assert_stale_link_removed(
            self.home / ".claude/skills/retired-demo",
            f"{self.home}/staging\n/../canonical/demo",
        )

    def test_newline_link_name_is_not_an_inventory_match(self):
        self.assert_stale_link_removed(
            self.home / ".claude/skills/demo\nextra", f"{self.canonical}/demo"
        )

    def test_newline_directory_name_fails_inventory(self):
        self.sync_and_validate()
        (self.canonical / "demo\nextra").mkdir()
        validated = self.run_script("validate")
        self.assertNotEqual(0, validated.returncode)
        self.assertIn("SKILL  unsupported directory name", validated.stderr)
        self.assertNotIn("SKILL  live ok", validated.stdout)

    def test_link_through_render_alias_to_outside_is_unmanaged(self):
        (self.home / "user-skill").mkdir()
        alias = self.render / "user-alias"
        self.sync_and_validate()
        alias.symlink_to(self.home / "user-skill")
        self.assert_unmanaged_link_kept(str(alias))

    def test_link_through_render_alias_dangling_outside_is_unmanaged(self):
        alias = self.render / "user-alias"
        self.sync_and_validate()
        alias.symlink_to(self.home / "missing-skill")
        self.assert_unmanaged_link_kept(str(alias))

    def test_link_through_symlink_loop_is_unmanaged(self):
        loop = self.render / "loop"
        self.sync_and_validate()
        loop.symlink_to("loop")
        self.assert_unmanaged_link_kept(str(loop))

    def test_dangling_intermediate_symlink_is_unmanaged(self):
        (self.home / "dangling").symlink_to(self.home / "absent")
        self.assert_unmanaged_link_kept(f"{self.home}/dangling/../render/codex/demo")

    def test_file_intermediate_component_is_unmanaged(self):
        (self.home / "plain-file").write_text("x")
        self.assert_unmanaged_link_kept(f"{self.home}/plain-file/../render/codex/demo")

    def test_dotdot_after_absent_component_is_unmanaged(self):
        self.assert_unmanaged_link_kept(f"{self.home}/absent/../canonical/demo")

    def test_dangling_link_outside_written_form_is_unmanaged(self):
        self.assert_unmanaged_link_kept(f"{self.render}/gone/demo")

    def test_dangling_link_in_written_form_is_stale(self):
        self.assert_stale_link_removed(
            self.home / ".claude/skills/retired-demo", f"{self.canonical}/retired-demo"
        )

    def test_dangling_overlong_name_is_unmanaged(self):
        self.assert_unmanaged_link_kept(f"{self.canonical}/" + "x" * 256)

    def test_written_form_naming_dangling_alias_is_unmanaged(self):
        self.sync_and_validate()
        (self.canonical / "alias").symlink_to(self.home / "missing-skill")
        self.assert_unmanaged_link_kept(f"{self.canonical}/alias")

    def test_written_form_under_codex_symlinked_outside_render_is_unmanaged(self):
        self.sync_and_validate()
        outside = self.home / "outside-codex"
        (self.render / "codex").rename(outside)
        (self.render / "codex").symlink_to(outside)
        link = self.home / ".claude/skills/user-link"
        link.symlink_to(f"{self.render}/codex/gone")
        validated = self.run_script("validate")
        self.assertNotIn("link stale: user-link", validated.stderr)
        synced = self.run_script("sync")
        self.assertEqual(f"{self.render}/codex/gone", os.readlink(link), synced.stderr)

    def test_written_form_through_symlink_chain_root_hitting_eloop_is_unmanaged(self):
        previous = self.canonical
        for index in range(39, -1, -1):
            hop = self.home / f"chain{index}"
            hop.symlink_to(previous)
            previous = hop
        link = self.home / ".claude/skills/user-link"
        link.parent.mkdir(parents=True, exist_ok=True)
        target = f"{self.home}/chain0/retired"
        link.symlink_to(target)
        self.run_script("sync", DECENT_ANGL_SKILL_ROOT=str(self.home / "chain0"))
        self.assertEqual(target, os.readlink(link))

    def test_trailing_slash_on_file_target_is_unmanaged(self):
        self.sync_and_validate()
        (self.render / "plain-file").write_text("x")
        self.assert_unmanaged_link_kept(f"{self.render}/plain-file/")

    def test_symlink_loop_limit_in_intermediate_components_is_unmanaged(self):
        (self.home / "bounce").symlink_to(".")
        for count in (40, 41):
            with self.subTest(count=count):
                self.assert_unmanaged_link_kept(
                    f"{self.home}/" + "bounce/" * count + "canonical/demo"
                )
                (self.home / ".claude/skills/user-link").unlink()

    def test_link_through_render_alias_into_canonical_is_stale(self):
        alias = self.render / "demo-alias"
        self.sync_and_validate()
        alias.symlink_to("../canonical/demo")
        self.assert_stale_link_removed(self.home / ".claude/skills/retired-demo", str(alias))

    def test_unmanaged_claude_content_is_ignored(self):
        self.sync_and_validate()
        skills = self.home / ".claude/skills"
        user_dir = skills / "user-skill"
        user_dir.mkdir()
        unmanaged_target = self.home / "user-skill"
        unmanaged_target.mkdir()
        user_link = skills / "user-link"
        user_link.symlink_to(unmanaged_target)
        result = self.run_script("validate")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(user_dir.is_dir())
        self.assertEqual(str(unmanaged_target), os.readlink(user_link))

    @unittest.skipUnless(REAL_READLINK, "readlink binary not found")
    def test_readlink_output_with_failure_is_not_accepted(self):
        self.sync_and_validate()
        self.install_shim("readlink", '"$REAL_READLINK" "$@"; exit 7')
        result = self.run_script("validate", REAL_READLINK=REAL_READLINK)
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn("SKILL  live ok", result.stdout)

    def shim_readlink_for(self, name, succeed_first):
        counter = self.root / "readlink-count"
        counter.unlink(missing_ok=True)
        limit = 1 if succeed_first else 0
        self.install_shim("readlink", f'''for target; do :; done
case "$target" in
  */{name})
    n=$(cat "{counter}" 2>/dev/null || echo 0); echo $((n + 1)) > "{counter}"
    [ "$n" -lt {limit} ] || exit 7 ;;
esac
exec "$REAL_READLINK" "$@"''')

    @unittest.skipUnless(REAL_READLINK, "readlink binary not found")
    def test_stale_link_readlink_failing_after_first_read_never_validates(self):
        self.sync_and_validate()
        stale = self.home / ".claude/skills/retired-demo"
        stale.symlink_to(self.canonical / "demo")
        self.shim_readlink_for("retired-demo", succeed_first=True)
        result = self.run_script("validate", REAL_READLINK=REAL_READLINK)
        self.assertNotEqual(0, result.returncode, result.stderr)
        self.assertNotIn("SKILL  live ok", result.stdout)

    @unittest.skipUnless(REAL_READLINK, "readlink binary not found")
    def test_stale_link_readlink_failure_is_a_probe_failure(self):
        self.sync_and_validate()
        stale = self.home / ".claude/skills/retired-demo"
        stale.symlink_to(self.canonical / "demo")
        for command in ("validate", "sync"):
            self.shim_readlink_for("retired-demo", succeed_first=False)
            result = self.run_script(command, REAL_READLINK=REAL_READLINK)
            self.assertNotEqual(0, result.returncode, command)
            self.assertIn("SKILL  probe failed (link target)", result.stderr, command)
            self.assertNotIn("SKILL  live ok", result.stdout, command)
        self.assertTrue(stale.is_symlink())

    @unittest.skipUnless(REAL_UNAME, "uname binary not found")
    def test_uname_output_with_failure_is_not_accepted(self):
        self.sync_and_validate()
        self.install_shim("uname", 'printf "Linux\\n"; exit 7')
        result = self.run_script("validate")
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn("SKILL  live ok", result.stdout)

    @unittest.skipUnless(REAL_FIND, "find binary not found")
    def test_find_output_with_failure_is_not_accepted(self):
        (self.skill / "references").mkdir()
        (self.skill / "references" / "note.md").write_text("reference\n")
        self.skill_file.write_text("---\nname: demo\ndescription: d\n---\nSee (references/note.md)\n")
        self.install_shim("find", '"$REAL_FIND" "$@"; exit 7')
        result = self.run_script("audit-source", REAL_FIND=REAL_FIND)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("references unreadable", result.stderr)
        self.assertNotIn("SKILL  source ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
