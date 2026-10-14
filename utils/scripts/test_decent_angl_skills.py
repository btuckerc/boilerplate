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

    @unittest.skipUnless(REAL_READLINK, "readlink binary not found")
    def test_readlink_output_with_failure_is_not_accepted(self):
        self.sync_and_validate()
        self.install_shim("readlink", '"$REAL_READLINK" "$@"; exit 7')
        result = self.run_script("validate", REAL_READLINK=REAL_READLINK)
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn("SKILL  live ok", result.stdout)

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
