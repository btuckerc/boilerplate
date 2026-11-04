#!/usr/bin/env python3
"""Managed shell startup reorders PATH without losing or inventing components.

An empty PATH component searches the current directory; startup must keep one it
inherits (and every other inherited entry) while putting ~/.local/bin and mise
shims first and dropping Omarchy's bin dir, and must never add one, e.g. by
prepending to an empty PATH (which has no components).
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMON_SH = ROOT / 'home/dot_config/shell/common.sh'
ZSHENV = ROOT / 'home/dot_zshenv'
ZPROFILE = ROOT / 'home/dot_config/zsh/dot_zprofile'
# dot_zshenv adds these on macOS when present; they are not under test here.
MACOS_SYSTEM_DIRS = {'/opt/homebrew/bin', '/opt/homebrew/sbin', '/usr/local/bin', '/usr/local/sbin'}


def shells():
    found = []
    for path in ('/bin/zsh', '/usr/bin/zsh', '/bin/bash', '/usr/bin/bash', '/opt/homebrew/bin/bash', '/usr/local/bin/bash'):
        if os.access(path, os.X_OK) and os.path.realpath(path) not in [os.path.realpath(p) for p in found]:
            found.append(path)
    return found


def zsh():
    return next((s for s in shells() if s.endswith('/zsh')), None)


def lookup(path):
    """The directories PATH searches, in order (repeats add nothing; '' is the current directory)."""
    seen = []
    for entry in path.split(':') if path else []:
        if entry not in seen:
            seen.append(entry)
    return seen


class PathSetupTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name).resolve()
        self.local_bin = str(self.home / '.local/bin')
        self.shims = str(self.home / '.local/share/mise/shims')
        self.omarchy = str(self.home / '.local/share/omarchy/bin')
        for d in (self.local_bin, self.shims, self.omarchy):
            os.makedirs(d)
        # One empty component, the omarchy dir, and a user dir out of place.
        self.inherited = f'/usr/bin::{self.local_bin}:/bin:{self.omarchy}'
        self.expected = [self.local_bin, self.shims, '/usr/bin', '', '/bin']

    def run_shell(self, args, path, script, home=None):
        env = {'HOME': str(home or self.home), 'PATH': path, 'USER': os.environ.get('USER', ''), 'TERM': 'dumb',
               'COMMON_SH': str(COMMON_SH)}
        result = subprocess.run(args + ['-c', script], env=env, cwd=self.home, capture_output=True,
                                text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_common_sh_keeps_inherited_components_in_every_shell(self):
        # .zshrc/.bashrc call remove_path_dir again after mise activation.
        script = ('. "$COMMON_SH" >/dev/null 2>&1; PATH="$PATH:$HOME/.local/share/omarchy/bin"; '
                  'remove_path_dir "$HOME/.local/share/omarchy/bin"; printf %s "$PATH"')
        bare = self.home / 'bare'  # no managed directories
        for shell in shells():
            args = [shell, '-f'] if shell.endswith('/zsh') else [shell, '--norc', '--noprofile']
            with self.subTest(shell=shell):
                self.assertEqual(lookup(self.run_shell(args, self.inherited, script)), self.expected)
                # A trailing empty component (bash IFS splitting drops it) survives too.
                self.assertEqual(lookup(self.run_shell(args, '/usr/bin:/bin:', script)),
                                 [self.local_bin, self.shims, '/usr/bin', '/bin', ''])
                self.assertEqual(lookup(self.run_shell(args, '', script)), [self.local_bin, self.shims])
                # Removing the only other component must not lose the empty one.
                self.assertEqual(lookup(self.run_shell(args, f'{self.omarchy}:', script)),
                                 [self.local_bin, self.shims, ''])
                self.assertEqual(lookup(self.run_shell(args, f'{bare}/.local/share/omarchy/bin:', script, bare)),
                                 [''])

    def test_zsh_startup_files_keep_inherited_components(self):
        shell = zsh()
        if shell is None:
            self.skipTest('zsh not installed')
        bare = self.home / 'bare'
        for home in (self.home, bare):
            (home / '.config/zsh').mkdir(parents=True)
            (home / '.zshenv').write_bytes(ZSHENV.read_bytes())
            (home / '.config/zsh/.zprofile').write_bytes(ZPROFILE.read_bytes())
        printer = "print -rn -- $PATH"

        def managed(out):
            return [p for p in lookup(out) if p not in MACOS_SYSTEM_DIRS]

        plain = self.run_shell([shell], self.inherited, printer)
        self.assertEqual(managed(plain), self.expected)
        # Login shells run /etc/zprofile (path_helper on macOS) and then .zprofile,
        # which must restore .zshenv's order ahead of anything path_helper added.
        login = self.run_shell([shell, '-l'], self.inherited, printer)
        self.assertEqual(lookup(login)[:len(lookup(plain))], lookup(plain))
        self.assertEqual(managed(self.run_shell([shell], '', printer)), [self.local_bin, self.shims])
        self.assertEqual(managed(self.run_shell([shell], f'{self.omarchy}:', printer)),
                         [self.local_bin, self.shims, ''])
        self.assertEqual(managed(self.run_shell([shell], f'{bare}/.local/share/omarchy/bin:', printer, bare)), [''])
        # The empty component still resolves commands from the current directory.
        tool = self.home / 'only-here'
        tool.write_text('#!/bin/sh\necho found-in-cwd\n')
        tool.chmod(0o755)
        self.assertEqual(self.run_shell([shell], self.inherited, 'only-here'), 'found-in-cwd\n')

    @unittest.skipUnless(shutil.which('chezmoi'), 'needs chezmoi to render the rc templates')
    def test_interactive_rc_files_neither_add_nor_drop_the_current_directory(self):
        def render(source):
            return subprocess.run(['chezmoi', 'execute-template', '--source', str(ROOT / 'home'),
                                   '--file', str(ROOT / source)], capture_output=True, text=True, check=True).stdout

        # No managed directories, so the rc files' own prepends meet the inherited PATH as is.
        home = self.home / 'rc'
        (home / '.config/shell').mkdir(parents=True)
        (home / '.config/zsh').mkdir(parents=True)
        shutil.copy(COMMON_SH, home / '.config/shell/common.sh')
        (home / '.bashrc').write_text(render('home/dot_bashrc.tmpl'))
        (home / '.zshenv').write_bytes(ZSHENV.read_bytes())
        (home / '.config/zsh/.zprofile').write_bytes(ZPROFILE.read_bytes())
        (home / '.config/zsh/.zshrc').write_text(render('home/dot_config/zsh/dot_zshrc.tmpl'))
        for shell in shells():
            with self.subTest(shell=shell):
                self.assertNotIn('', lookup(self.run_shell([shell, '-i'], '', 'printf %s "$PATH"', home)))
                self.assertIn('', lookup(self.run_shell([shell, '-i'], '/usr/bin::/bin', 'printf %s "$PATH"', home)))


if __name__ == '__main__':
    unittest.main()
