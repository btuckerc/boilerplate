#!/usr/bin/env python3
"""restic-scheduled-job outcomes, schedule lock and run bookkeeping."""
import ipaddress
import os
import runpy
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEDULER = ROOT / 'home/dot_local/bin/executable_restic-scheduled-job'
DOCTOR = runpy.run_path(str(ROOT / 'home/dot_local/bin/executable_decent-angl-doctor'))
# Any boot but this one: the record a reboot since the cutover leaves behind.
PRIOR_BOOT = '00000000-0000-4000-8000-000000000000'


def current_boot():
    if sys.platform == 'darwin':
        return subprocess.run(['/usr/sbin/sysctl', '-n', 'kern.bootsessionuuid'], capture_output=True, text=True,
                              check=True).stdout.strip()
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


class ScheduledJobTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.user = Path(self.tmp.name)
        binary = self.user / '.local/bin'
        binary.mkdir(parents=True)
        self.calls = self.user / 'calls'
        fakes = {
            'restic-target-env': '#!/bin/sh\n'
                                 'echo "export RESTIC_TARGET_NAME=\'local\'"\n'
                                 'echo "export RESTIC_TARGET_REPO=\'$FAKE_REPO\'"\n',
            'restic-machine': '#!/bin/sh\necho "machine $*" >>"$HOME/calls"\n',
            # A helper that inherits the lock marker could start a run that skips the lock.
            'restic-backup': '#!/bin/sh\necho "backup $*" >>"$HOME/calls"\n'
                             '[ -z "${RESTIC_SCHEDULE_LOCK_MARKER+set}" ] || exit 99\nexit "${FAKE_STATUS:-0}"\n',
        }
        for name, content in fakes.items():
            path = binary / name
            path.write_text(content)
            path.chmod(0o755)
        password = self.user / 'password'
        password.write_text('fixture, not a credential')
        self.state = self.user / 'state'
        self.lock = self.state / 'job.lock'
        self.env = dict(os.environ, HOME=str(self.user), RESTIC_CONFIG_FILE=str(self.user / 'absent'),
                        RESTIC_PASSWORD_FILE=str(password), RESTIC_MACHINE_ID='fixture',
                        RESTIC_SCHEDULE_STATE_DIR=str(self.state), RESTIC_SCHEDULE_LOCK_PATH=str(self.lock),
                        RESTIC_SCHEDULE_LOCK_WAIT_SECONDS='0', FAKE_REPO='/fixture-repo')
        self.env.pop('RESTIC_LOCAL_PASSWORD_FILE', None)
        # The host has rebooted since the kernel-lock cutover was armed (see cutover tests).
        self.cutover = self.user / '.local/state/decent-angl/restic-scheduler/kernel-lock-v2-origin-boot'
        self.cutover.parent.mkdir(parents=True)
        self.cutover.write_text(PRIOR_BOOT + '\n')

    def tearDown(self):
        self.tmp.cleanup()

    def run_job(self):
        result = subprocess.run(['sh', str(SCHEDULER), 'backup'], env=self.env, text=True, capture_output=True)
        lines = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
        calls = self.calls.read_text().splitlines() if self.calls.exists() else []
        return result, lines, calls

    def record(self):
        text = (self.state / 'last-run.local.backup').read_text()
        return dict(line.split('=', 1) for line in text.splitlines())

    def hold_lock(self, holder_info=''):
        """A live scheduler holding the lock, as another job would."""
        self.state.mkdir(parents=True, exist_ok=True)
        self.lock.write_text(holder_info)
        if sys.platform == 'darwin':
            argv = ['lockf', '-k', str(self.lock), 'sh', '-c', 'echo held; sleep 30']
        else:
            argv = ['flock', str(self.lock), 'sh', '-c', 'echo held; sleep 30']
        # Its own session, so the whole holder (lock tool and child) can be killed.
        holder = subprocess.Popen(argv, stdout=subprocess.PIPE, text=True, start_new_session=True)
        self.addCleanup(holder.stdout.close)
        self.addCleanup(self.kill_holder, holder)
        self.assertEqual(holder.stdout.readline().strip(), 'held')
        return holder

    @staticmethod
    def kill_holder(holder):
        try:
            os.killpg(holder.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        holder.wait()

    def test_success_unlocks_before_job_and_records_run(self):
        result, lines, calls = self.run_job()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ['machine --repo-target local unlock', 'backup --repo-target local'])
        self.assertEqual(lines['outcome'], 'success')
        self.assertEqual((self.state / 'last-success.local.backup').read_text().strip(), lines['finished_at'])
        self.assertEqual(self.record(), {'finished_at': lines['finished_at'], 'outcome': 'success', 'exit_code': '0'})
        self.assertEqual((self.state / 'first-run.local').read_text().strip(), lines['started_at'])
        self.assertEqual([p.name for p in self.state.iterdir() if p.name.startswith('.')], [])

    def test_failure_keeps_previous_last_success_and_records_failure(self):
        self.state.mkdir(parents=True)
        (self.state / 'last-success.local.backup').write_text('2026-01-01T00:00:00Z\n')
        (self.state / 'first-run.local').write_text('2025-01-01T00:00:00Z\n')
        self.env['FAKE_STATUS'] = '7'
        result, lines, _ = self.run_job()
        self.assertEqual(result.returncode, 7)
        self.assertEqual((lines['outcome'], lines['exit_code']), ('failed', '7'))
        self.assertEqual((self.state / 'last-success.local.backup').read_text(), '2026-01-01T00:00:00Z\n')
        self.assertEqual(self.record()['outcome'], 'failed')
        self.assertEqual((self.state / 'first-run.local').read_text(), '2025-01-01T00:00:00Z\n')

    @unittest.skipUnless(shutil.which('nc') and shutil.which('ssh'), 'needs nc and ssh')
    def test_unreachable_sftp_host_is_skipped_without_running(self):
        self.env['FAKE_REPO'] = 'sftp:admin@unreachable.invalid:/srv/restic/fixture'
        result, lines, calls = self.run_job()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((lines['outcome'], lines['exit_code']), ('skipped', '0'))
        self.assertEqual(calls, [])
        self.assertFalse((self.state / 'last-success.local.backup').exists())
        self.assertEqual(self.record()['outcome'], 'skipped')

    @unittest.skipUnless(shutil.which('nc') and shutil.which('ssh'), 'needs nc and ssh')
    def test_alias_resolving_to_this_host_runs_even_when_refused(self):
        # ssh reads the passwd home's config, so a wrapper points it at a fixture config.
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            closed_port = probe.getsockname()[1]
        (self.user / 'ssh_config').write_text(f'Host loopback-restic\n  HostName 127.0.0.1\n  Port {closed_port}\n')
        wrappers = self.user / 'wrappers'
        wrappers.mkdir()
        (wrappers / 'ssh').write_text(f'#!/bin/sh\nexec {shutil.which("ssh")} -F "$HOME/ssh_config" "$@"\n')
        (wrappers / 'ssh').chmod(0o755)
        self.env['PATH'] = f'{wrappers}:{self.env["PATH"]}'
        self.env['FAKE_REPO'] = 'sftp:admin@loopback-restic:/srv/restic/fixture'
        result, lines, calls = self.run_job()
        self.assertEqual((result.returncode, lines['outcome']), (0, 'success'), result.stderr)
        self.assertIn('backup --repo-target local', calls)

    def test_missing_job_helper_is_recorded_as_failed(self):
        (self.state / 'last-run.local.backup').parent.mkdir(parents=True)
        (self.state / 'last-run.local.backup').write_text('finished_at=2026-01-01T00:00:00Z\noutcome=success\nexit_code=0\n')
        (self.user / '.local/bin/restic-backup').unlink()
        self.env['PATH'] = f'{self.user / ".local/bin"}:/usr/bin:/bin:/usr/sbin:/sbin'
        result, _, calls = self.run_job()
        self.assertEqual(result.returncode, 1)
        self.assertIn('helper not found', result.stderr)
        self.assertEqual(calls, [])
        self.assertEqual({k: v for k, v in self.record().items() if k != 'finished_at'},
                         {'outcome': 'failed', 'exit_code': '1'})

    def scheduler(self, *argv, **extra):
        return subprocess.run(['sh', str(SCHEDULER), *argv], env={**self.env, **extra}, text=True, capture_output=True)

    def test_argument_errors_and_plans_are_not_runs(self):
        # Options count wherever they appear; nothing reaches the job helper.
        for argv, extra, message in ((['--repo-target', 'bogus', 'backup'], {}, 'Unknown repo target: bogus'),
                                     (['backup', '--repo-target', 'bogus'], {}, 'Unknown repo target: bogus'),
                                     (['backup'], {'RESTIC_REPO_TARGET': 'bogus'}, 'Unknown repo target: bogus'),
                                     (['backup', '--keep'], {}, 'Unknown argument: --keep'),
                                     (['backup', 'check'], {}, 'Only one job per run')):
            with self.subTest(argv=argv, env=extra):
                result = self.scheduler(*argv, **extra)
                self.assertEqual(result.returncode, 1)
                self.assertIn(message, result.stderr)
                self.assertEqual(sorted(p.name for p in self.state.glob('last-run.*')), [])
                self.assertFalse(self.calls.exists())
        result = self.scheduler('backup', '--repo-target', 'offsite', '--print-plan')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('job=backup\nrepo_target=offsite\n', result.stdout)
        self.assertEqual(sorted(p.name for p in self.state.glob('last-*')), [])
        self.assertFalse(self.calls.exists())
        # An alias that fails is recorded under the canonical target the doctor reads,
        # whatever TARGET_NAME the environment carries.
        os.unlink(self.env['RESTIC_PASSWORD_FILE'])
        result = self.scheduler('--repo-target', 'primary', 'backup', TARGET_NAME='bogus')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(sorted(p.name for p in self.state.glob('last-run.*')), ['last-run.local.backup'])
        self.assertEqual(self.record()['outcome'], 'failed')

    def test_live_holder_times_out_as_failed(self):
        self.hold_lock('job=check pid=1 since=2026-01-01T00:00:00Z\n')
        result, lines, calls = self.run_job()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(lines['outcome'], 'failed')
        self.assertIn('held by job=check', result.stderr)
        self.assertIn('Timed out', result.stderr)
        self.assertEqual(calls, [])
        self.assertEqual(self.record(), {'finished_at': lines['finished_at'], 'outcome': 'failed', 'exit_code': '1'})

    def test_job_status_75_is_not_mistaken_for_a_lock_timeout(self):
        self.env['FAKE_STATUS'] = '75'
        result, lines, calls = self.run_job()
        self.assertEqual((result.returncode, lines['exit_code']), (75, '75'))
        self.assertNotIn('Timed out', result.stderr)
        self.assertEqual(len(calls), 2)

    def test_killed_holder_leaves_no_stale_lock(self):
        holder = self.hold_lock('job=check pid=1 since=2026-01-01T00:00:00Z\n')
        self.kill_holder(holder)
        result, lines, _ = self.run_job()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(lines['outcome'], 'success')

    def legacy_lease(self, pid):
        """The previous scheduler's directory lease, which this one must never touch."""
        lease = self.state / 'lock'
        lease.mkdir(parents=True)
        (lease / 'machine_id').write_text('fixture\n')
        (lease / 'pid').write_text(f'{pid}\n')
        return lease

    def old_scheduler(self):
        """A job of the previous scheduler fed through stdin, so no process lists its script."""
        script = self.user / 'old-scheduler'
        script.write_text('echo started\nwhile [ -e "$HOME/old-running" ]; do sleep 0.05; done\n')
        (self.user / 'old-running').touch()
        with script.open() as stdin:
            old = subprocess.Popen(['sh', '-s', '--', 'backup'], stdin=stdin, env=self.env, stdout=subprocess.PIPE,
                                   text=True, start_new_session=True)
        self.addCleanup(old.stdout.close)
        self.addCleanup(self.kill_holder, old)
        self.assertEqual(old.stdout.readline().strip(), 'started')
        return old

    def assert_refused(self, result, calls, reason):
        self.assertEqual((result.returncode, calls), (1, []), result.stderr)
        self.assertIn(reason, result.stderr)
        self.assertEqual({k: v for k, v in self.record().items() if k != 'finished_at'},
                         {'outcome': 'failed', 'exit_code': '1'})

    def test_first_run_arms_the_cutover_and_runs_nothing_until_a_reboot(self):
        self.cutover.unlink()
        for _ in range(2):
            result, _, calls = self.run_job()
            self.assert_refused(result, calls, 'until this host reboots once')
            self.assertEqual(self.cutover.read_text(), current_boot() + '\n')
        self.assertEqual([p.name for p in self.cutover.parent.iterdir()], [self.cutover.name])

    def test_no_pass_runs_beside_a_previous_schedulers_job_before_a_reboot(self):
        self.cutover.write_text(current_boot() + '\n')
        self.old_scheduler()
        result, _, calls = self.run_job()
        self.assert_refused(result, calls, 'until this host reboots once')
        # The locked rerun checks too: its marker variable is no way around the cutover.
        self.state.mkdir(exist_ok=True)
        self.env['RESTIC_SCHEDULE_LOCK_MARKER'] = str(self.state / 'marker')
        result, _, calls = self.run_job()
        self.assert_refused(result, calls, 'until this host reboots once')
        self.assertFalse((self.state / 'marker').exists())

    def test_after_a_reboot_jobs_run_and_leave_legacy_leases_alone(self):
        # A lease naming a live, unrelated pid (as after pid reuse) does not block anything.
        lease = self.legacy_lease(os.getpid())
        result, lines, calls = self.run_job()
        self.assertEqual((result.returncode, lines['outcome']), (0, 'success'), result.stderr)
        self.assertEqual(calls, ['machine --repo-target local unlock', 'backup --repo-target local'])
        self.assertEqual(((lease / 'pid').read_text(), sorted(p.name for p in lease.iterdir())),
                         (f'{os.getpid()}\n', ['machine_id', 'pid']))
        self.assertEqual(self.cutover.read_text(), PRIOR_BOOT + '\n')

    def test_unreadable_boot_id_or_cutover_record_fails_closed(self):
        wrappers = self.user / 'uname-wrapper'
        wrappers.mkdir()
        (wrappers / 'uname').write_text('#!/bin/sh\necho Plan9\n')
        (wrappers / 'uname').chmod(0o755)
        path = self.env['PATH']
        self.env['PATH'] = f'{wrappers}:{path}'
        result, _, calls = self.run_job()
        self.assert_refused(result, calls, "Cannot read this host's boot id")
        self.env['PATH'] = path
        # Anything but exactly one UUID line, including extra blank lines or none at all.
        for content in ('', 'not-a-boot-id\n', PRIOR_BOOT + '\n' + PRIOR_BOOT + '\n', PRIOR_BOOT + '\n\n',
                        PRIOR_BOOT, '\n' + PRIOR_BOOT + '\n', PRIOR_BOOT + '\r\n', PRIOR_BOOT + '\n\0',
                        PRIOR_BOOT[:8] + '\0' + PRIOR_BOOT[8:] + '\n'):
            with self.subTest(record=content):
                self.cutover.write_text(content)
                result, _, calls = self.run_job()
                self.assert_refused(result, calls, 'Malformed kernel-lock cutover record')
                self.assertEqual(self.cutover.read_bytes(), content.encode())
        self.cutover.unlink()
        self.cutover.mkdir()
        result, _, calls = self.run_job()
        self.assert_refused(result, calls, 'Cannot read or create the kernel-lock cutover record')

    def prepare(self):
        return subprocess.run(['sh', str(SCHEDULER), '--prepare-kernel-lock-migration'], env=self.env, text=True,
                              capture_output=True)

    def test_prepare_arms_once_without_a_password_or_repository(self):
        self.cutover.unlink()
        os.unlink(self.env['RESTIC_PASSWORD_FILE'])
        # Concurrent first runs all agree on one complete record.
        runs = [subprocess.Popen(['sh', str(SCHEDULER), '--prepare-kernel-lock-migration'], env=self.env, text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(8)]
        for run in runs:
            out, err = run.communicate(timeout=30)
            self.assertEqual((run.returncode, out), (0, 'kernel_lock_cutover=reboot-required\n'), err)
        self.assertEqual(self.cutover.read_text(), current_boot() + '\n')
        self.assertEqual([p.name for p in self.cutover.parent.iterdir()], [self.cutover.name])
        self.cutover.write_text(PRIOR_BOOT + '\n')
        result = self.prepare()
        self.assertEqual((result.returncode, result.stdout), (0, 'kernel_lock_cutover=done\n'), result.stderr)
        self.assertEqual(self.cutover.read_text(), PRIOR_BOOT + '\n')
        self.assertFalse(self.calls.exists())

    def fake_nc(self, output, ssh_hostname=None):
        wrappers = self.user / 'nc-wrapper'
        wrappers.mkdir(exist_ok=True)
        (wrappers / 'nc').write_text(f'#!/bin/sh\necho "{output}" >&2\nexit 1\n')
        (wrappers / 'nc').chmod(0o755)
        if ssh_hostname:
            # An ssh alias whose HostName is the given spelling (ssh -G is all the scheduler asks).
            (wrappers / 'ssh').write_text(f'#!/bin/sh\nprintf "user admin\\nhostname {ssh_hostname}\\nport 22\\n"\n')
            (wrappers / 'ssh').chmod(0o755)
        if str(wrappers) not in self.env['PATH']:
            self.env['PATH'] = f'{wrappers}:{self.env["PATH"]}'

    @unittest.skipUnless(shutil.which('ssh'), 'needs ssh')
    def test_only_a_network_failure_skips_a_remote_host(self):
        self.env['FAKE_REPO'] = 'sftp:admin@192.0.2.10:/srv/restic/fixture'
        # Real macOS and netcat-openbsd wording; anything unrecognised must not silence backups.
        for output, outcome in (('nc: connect to 192.0.2.10 port 22 (tcp) failed: Connection refused', 'success'),
                                ('nc: invalid option -- G', 'success'),
                                ('nc: connectx to 192.0.2.10 port 22 (tcp) failed: Operation timed out', 'skipped'),
                                ('nc: connect to 192.0.2.10 port 22 (tcp) timed out: Operation now in progress',
                                 'skipped'),
                                ('nc: connect to 192.0.2.10 port 22 (tcp) failed: No route to host', 'skipped'),
                                ('nc: getaddrinfo: nodename nor servname provided, or not known', 'skipped'),
                                ('nc: getaddrinfo for host "x" port 22: Name or service not known', 'skipped')):
            with self.subTest(nc=output):
                self.fake_nc(output.replace('"', '\\"'))
                result, lines, _ = self.run_job()
                self.assertEqual((result.returncode, lines['outcome']), (0, outcome), result.stderr)

    @unittest.skipUnless(shutil.which('ssh'), 'needs ssh')
    def test_dropped_connection_to_this_machines_address_runs_the_job(self):
        addresses = subprocess.run(['sh', '-c', '{ ip -o addr show 2>/dev/null || ifconfig -a; } | '
                                    "awk '$0 ~ /inet / { for (i = 1; i < NF; i++) if ($i == \"inet\") print $(i + 1) }'"],
                                   capture_output=True, text=True).stdout.split()
        own = next((a.split('/')[0] for a in addresses if not a.startswith('127.')), None)
        if own is None:
            self.skipTest('no non-loopback IPv4 address')
        self.fake_nc(f'nc: connect to {own} port 22 (tcp) failed: Operation timed out')
        self.env['FAKE_REPO'] = f'sftp:admin@{own}:/srv/restic/fixture'
        result, lines, calls = self.run_job()
        self.assertEqual((result.returncode, lines['outcome']), (0, 'success'), result.stderr)
        # The same failure for a remote address is a skip.
        self.env['FAKE_REPO'] = 'sftp:admin@192.0.2.10:/srv/restic/fixture'
        result, lines, _ = self.run_job()
        self.assertEqual((result.returncode, lines['outcome']), (0, 'skipped'), result.stderr)

    def test_other_spellings_of_this_machines_address_run_the_job(self):
        listing = subprocess.run(['sh', '-c', 'ip -o addr show 2>/dev/null || ifconfig -a'],
                                 capture_output=True, text=True).stdout.split()
        found = [listing[i + 1].split('/')[0].split('%')[0] for i, word in enumerate(listing[:-1])
                 if word in ('inet', 'inet6')]
        spellings = []
        own4 = next((a for a in found if '.' in a and not a.startswith('127.')), None)
        if own4:
            spellings.append(str(int(ipaddress.IPv4Address(own4))))
        own6 = next((a for a in found if ':' in a and not ipaddress.IPv6Address(a).is_link_local
                     and not ipaddress.IPv6Address(a).is_loopback), None)
        if own6:
            spellings.append(ipaddress.IPv6Address(own6).exploded.upper())
        if not spellings:
            self.skipTest('no non-loopback address')
        for spelling in spellings:
            with self.subTest(spelling=spelling):
                self.fake_nc(f'nc: connect to {spelling} port 22 (tcp) failed: Operation timed out', spelling)
                self.env['FAKE_REPO'] = 'sftp:admin@self-backup:/srv/restic/fixture'
                result, lines, _ = self.run_job()
                self.assertEqual((result.returncode, lines['outcome']), (0, 'success'), result.stderr)


class BackupFreshnessTest(unittest.TestCase):
    """The doctor reads the scheduler's state files, which exist on every platform."""

    def issues(self, files, now='2026-06-01T00:00:00Z'):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / 'restic-scheduler'
            state.mkdir()
            for name, text in {'last-success.local.backup': '2026-05-31T00:00:00Z\n', **files}.items():
                (state / name).write_text(text)
            jobs = DOCTOR['backup_jobs'](Path(tmp))
        return DOCTOR['backup_issues'](jobs, DOCTOR['datetime'].fromisoformat(now))

    def test_monthly_job_that_never_succeeded_is_flagged_once_it_ran(self):
        for outcome, code in (('failed', 1), ('skipped', 0)):
            record = f'finished_at=2026-05-01T00:00:00Z\noutcome={outcome}\nexit_code={code}\n'
            issues = self.issues({'last-run.local.check': record})
            self.assertIn('successful check timestamp unavailable', issues)

    def test_monthly_job_that_never_runs_is_flagged_after_40_days(self):
        self.assertEqual(self.issues({'first-run.local': '2026-05-01T00:00:00Z\n'}), [])
        issues = self.issues({'first-run.local': '2026-04-01T00:00:00Z\n'})
        self.assertIn('check has not run in the 40 days since scheduled jobs started', issues)


if __name__ == '__main__':
    unittest.main()
