#!/usr/bin/env python3
"""Exercise canonical bootstrap and failure boundaries without real installers."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class BootstrapTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='bootstrap-contract-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.user = self.root / 'user'
        self.repo = self.user / 'src/boilerplate'
        self.source = self.user / '.local/share/chezmoi'
        self.bin = self.user / '.local/bin'
        self.bin.mkdir(parents=True)
        self.repo.mkdir(parents=True)
        (self.repo / '.git').mkdir()
        (self.repo / '.chezmoiroot').write_text('home\n')
        shutil.copyfile(ROOT / 'setup', self.repo / 'setup')
        self.env = dict(os.environ, HOME=str(self.user), XDG_STATE_HOME=str(self.user / '.local/state'),
                        BOILERPLATE_ROOT=str(self.repo), BOILERPLATE_SOURCE_LINK=str(self.source),
                        CHEZMOI_BIN_DIR=str(self.bin))
        for name, fail in [('chezmoi', 'FAIL_APPLY'), ('mise', 'FAIL_TOOLS'), ('decent-angl-skills', 'FAIL_SKILLS')]:
            file = self.bin / name
            file.write_text(f'''#!/bin/sh
if [ "$1" = --version ]; then exit 0; fi
echo {name} >> "$HOME/calls"
exit "${{{fail}:-0}}"
''')
            file.chmod(0o755)

    def setup(self, *args):
        return subprocess.run(['bash', str(self.repo / 'setup'), *args], env=self.env,
                              text=True, capture_output=True)

    def test_plan_has_no_side_effects(self):
        p = self.setup('--plan')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(self.source.exists())
        self.assertFalse((self.user / 'calls').exists())

    def test_preserves_old_source_and_repeat_is_idempotent(self):
        self.source.mkdir(parents=True)
        (self.source / 'local-work').write_text('keep me')
        for _ in range(2):
            p = self.setup()
            self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(self.source.is_symlink())
        self.assertEqual(self.source.resolve(), self.repo)
        backups = list((self.user / '.local/state/decent-angl/source-backups').glob('*/source/local-work'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), 'keep me')

    def test_failed_apply_never_reports_success_or_runs_verification(self):
        self.env['FAIL_APPLY'] = '43'
        p = self.setup()
        self.assertEqual(p.returncode, 43)
        self.assertNotIn('Bootstrap complete', p.stdout)
        self.assertEqual((self.user / 'calls').read_text(), 'chezmoi\n')

    def test_failed_tool_verification_stops_before_skills(self):
        self.env['FAIL_TOOLS'] = '44'
        p = self.setup()
        self.assertEqual(p.returncode, 44)
        self.assertNotIn('Bootstrap complete', p.stdout)
        self.assertEqual((self.user / 'calls').read_text(), 'chezmoi\nmise\n')

    def test_alternate_checkout_is_refused_before_mutation(self):
        self.env['BOILERPLATE_ROOT'] = str(self.root / 'different')
        p = self.setup()
        self.assertNotEqual(p.returncode, 0)
        self.assertFalse(self.source.exists())
        self.assertFalse((self.user / 'calls').exists())


class ResticCheckTest(unittest.TestCase):
    def test_full_reads_all_data_and_default_samples_data(self):
        with tempfile.TemporaryDirectory() as directory:
            user = Path(directory)
            binary = user / '.local/bin'
            binary.mkdir(parents=True)
            for name, content in {
                'restic': '#!/bin/sh\nprintf "%s\\n" "$@"\n',
                'restic-target-env': "#!/bin/sh\necho \"RESTIC_TARGET_REPO='/fixture'\"\n",
            }.items():
                path = binary / name
                path.write_text(content)
                path.chmod(0o755)
            password = user / 'password'
            password.write_text('fixture, not a credential')
            env = dict(os.environ, HOME=str(user), RESTIC_CONFIG_FILE=str(user / 'absent'),
                       RESTIC_PASSWORD_FILE=str(password), RESTIC_CHECK_READ_DATA_SUBSET='10%')
            for flags, expected in [([], ['--read-data-subset', '10%']), (['--full'], ['--read-data'])]:
                result = subprocess.run(['sh', str(ROOT / 'home/dot_local/bin/executable_restic-check'), *flags],
                                        env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.splitlines(), ['-r', '/fixture', 'check', *expected])


if __name__ == '__main__':
    unittest.main()
