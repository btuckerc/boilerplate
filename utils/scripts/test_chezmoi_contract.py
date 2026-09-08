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


if __name__ == "__main__":
    unittest.main()
