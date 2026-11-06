#!/usr/bin/env python3
"""decent-angl-launchd: role picks the launchd domain; installs never leave two copies."""
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / 'home/dot_local/bin/executable_decent-angl-launchd.tmpl'
LABEL = 'gg.angl.decent-angl-sync'

# Models what launchd has loaded as files in $FAKE_STATE; FAKE_STUCK names a
# service whose bootout never takes effect. Overrides (disable/enable) are shared
# by gui/<uid> and user/<uid>; gui/<uid> refuses them with no GUI session, and a
# disabled agent does not load (both as observed on macOS 26). A GUI login loads
# the agent unless disabled: `fake-login` runs one, and FAKE_LOGIN_AT runs one
# just before the first call starting with it if $FAKE_LOGIN_PLIST exists
# (/ = a login that read the plist earlier).
FAKE_LAUNCHCTL = '''#!/bin/sh
echo "launchctl $*" >>"$FAKE_LOG"
gui="gui/$(id -u)"
key() { printf '%s' "$1" | tr / _; }
disabled() { [ -e "$FAKE_STATE/disabled_$1" ]; }
login() { disabled "$FAKE_LOGIN_LABEL" || : >"$FAKE_STATE/$(key "$gui/$FAKE_LOGIN_LABEL")"; }
if [ -n "${FAKE_LOGIN_AT:-}" ] && [ ! -e "$FAKE_STATE.login" ]; then
    case "$*" in
        "$FAKE_LOGIN_AT"*)
            : >"$FAKE_STATE.login"
            [ ! -e "$FAKE_LOGIN_PLIST" ] || login ;;
    esac
fi
case "$1" in
    fake-login) login ;;
    print)
        case "$2" in
            system) exit 0 ;;
            "$gui") exit "${FAKE_GUI_STATUS:-0}" ;;
            "$gui"/*) [ "${FAKE_GUI_STATUS:-0}" = 0 ] || exit 113 ;;
        esac
        [ -e "$FAKE_STATE/$(key "$2")" ] || exit 113 ;;
    disable|enable)
        case "$2" in
            "$gui"/*) [ "${FAKE_GUI_STATUS:-0}" = 0 ] || exit 125 ;;
            user/*) ;;
            *) exit 0 ;;
        esac
        if [ "$1" = disable ]; then : >"$FAKE_STATE/disabled_${2##*/}"; else rm -f "$FAKE_STATE/disabled_${2##*/}"; fi ;;
    bootout)
        [ -e "$FAKE_STATE/$(key "$2")" ] || exit 3
        [ "$2" = "${FAKE_STUCK:-}" ] || rm -f "$FAKE_STATE/$(key "$2")" ;;
    bootstrap)
        [ "${FAKE_BOOTSTRAP_STATUS:-0}" = 0 ] || exit "$FAKE_BOOTSTRAP_STATUS"
        label="$(plutil -extract Label raw -o - "$3")"
        case "$2" in system) ;; *) ! disabled "$label" || exit 5 ;; esac
        : >"$FAKE_STATE/$(key "$2/$label")" ;;
esac
'''
# Runs the privileged step unprivileged: owner flags dropped, launchctl faked.
FAKE_SUDO = '''#!/bin/sh
[ "$FAKE_SUDO" = allow ] || exit 1
shift
echo "sudo $*" >>"$FAKE_LOG"
case "$1" in
    true) exit 0 ;;
    install) exec /usr/bin/install -m 644 "$8" "$9" ;;
    *) exec "$@" ;;
esac
'''


def plist(user):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key><array><string>/usr/bin/true</string></array>
  <key>UserName</key><string>{user}</string>
</dict></plist>
'''


@unittest.skipUnless(sys.platform == 'darwin', 'launchd is macOS-only')
class LaunchdHelperTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.home = self.root / 'home'
        self.agents = self.home / 'Library/LaunchAgents'
        self.daemons = self.root / 'LaunchDaemons'
        self.retired = self.home / '.local/state/decent-angl/launchd-retired'
        self.log = self.root / 'log'
        fakes = self.root / 'bin'
        self.state = self.root / 'loaded'
        for path in (self.agents, self.daemons, fakes, self.state):
            path.mkdir(parents=True)
        for name, text in (('launchctl', FAKE_LAUNCHCTL), ('sudo', FAKE_SUDO), ('sleep', '#!/bin/sh\n')):
            (fakes / name).write_text(text)
            (fakes / name).chmod(0o755)
        self.source = self.root / f'{LABEL}.plist'
        self.source.write_text(plist(os.environ.get('USER') or subprocess.check_output(['id', '-un'], text=True).strip()))
        self.env = dict(os.environ, HOME=str(self.home), PATH=f'{fakes}:/usr/bin:/bin:/usr/sbin:/sbin',
                        FAKE_LOG=str(self.log), FAKE_STATE=str(self.state), FAKE_SUDO='allow',
                        DECENT_ANGL_LAUNCHD_DAEMON_DIR=str(self.daemons))
        self.gui = f'gui/{os.getuid()}/{LABEL}'
        self.system = f'system/{LABEL}'
        self.legacy_user = f'user/{os.getuid()}/{LABEL}'

    def load(self, service):
        (self.state / service.replace('/', '_')).touch()

    def is_loaded(self, service):
        return (self.state / service.replace('/', '_')).exists()

    def run_helper(self, role, *args):
        rendered = re.sub(r'^ROLE=\{\{.*\}\}$', f'ROLE="{role}"', HELPER.read_text(), flags=re.M)
        script = self.root / 'helper'
        script.write_text(rendered)
        result = subprocess.run(['sh', str(script), *args], env=self.env, text=True, capture_output=True)
        calls = self.log.read_text().splitlines() if self.log.exists() else []
        return result, calls

    def test_domain_follows_role(self):
        self.assertEqual(self.run_helper('home-server', 'domain')[0].stdout, 'system\n')
        self.assertEqual(self.run_helper('portable-macos-workstation', 'domain')[0].stdout, f'gui/{os.getuid()}\n')
        result, _ = self.run_helper('portable-linux-workstation', 'domain')
        self.assertNotEqual(result.returncode, 0)

    def test_server_retires_login_agent_then_loads_daemon(self):
        (self.agents / f'{LABEL}.plist').write_text('old agent')
        self.load(self.gui)
        result, calls = self.run_helper('home-server', 'install', str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.agents / f'{LABEL}.plist').exists())
        self.assertEqual((self.retired / f'{LABEL}.plist').read_text(), 'old agent')
        self.assertEqual((self.daemons / f'{LABEL}.plist').read_text(), self.source.read_text())
        self.assertEqual((self.is_loaded(self.gui), self.is_loaded(self.system)), (False, True))
        changes = [c for c in calls if c.startswith('launchctl ') and not c.startswith('launchctl print')]
        self.assertEqual(changes, [f'launchctl disable user/{os.getuid()}/{LABEL}', f'launchctl bootout {self.gui}',
                                   f'launchctl enable {self.system}',
                                   f'launchctl bootstrap system {self.daemons}/{LABEL}.plist'])

    def test_unchanged_loaded_job_is_not_restarted(self):
        for role, directory, service in (('home-server', self.daemons, self.system),
                                          ('portable-macos-workstation', self.agents, self.gui)):
            with self.subTest(role=role):
                # Run each role from a fresh load, retiring the previous domain.
                result, _ = self.run_helper(role, 'install', str(self.source))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.log.write_text('')
                result, calls = self.run_helper(role, 'install', str(self.source))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('unchanged', result.stdout)
                self.assertTrue(self.is_loaded(service))
                self.assertFalse([c for c in calls if ' bootout ' in c or ' bootstrap ' in c], calls)
                # A changed definition must still replace the loaded job.
                (directory / f'{LABEL}.plist').write_text('stale')
                self.log.write_text('')
                result, calls = self.run_helper(role, 'install', str(self.source))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f'launchctl bootout {service}', calls)
                self.assertTrue(any(' bootstrap ' in c for c in calls), calls)

    def test_unchanged_unloaded_job_is_loaded(self):
        for role, directory, service in (('home-server', self.daemons, self.system),
                                          ('portable-macos-workstation', self.agents, self.gui)):
            with self.subTest(role=role):
                (directory / f'{LABEL}.plist').write_text(self.source.read_text())
                result, calls = self.run_helper(role, 'install', str(self.source))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(self.is_loaded(service))
                self.assertTrue(any(' bootstrap ' in c for c in calls), calls)

    def test_reinstall_reenables_a_disabled_but_loaded_agent(self):
        result, _ = self.run_helper('portable-macos-workstation', 'install', str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr)
        subprocess.run([self.root / 'bin/launchctl', 'disable', self.legacy_user], env=self.env, check=True)
        result, _ = self.run_helper('portable-macos-workstation', 'install', str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('unchanged', result.stdout)
        self.assertFalse((self.state / f'disabled_{LABEL}').exists())

    def login(self):
        subprocess.run([self.root / 'bin/launchctl', 'fake-login'], env=self.env, check=True)

    def test_no_login_during_or_after_server_install_loads_the_agent(self):
        (self.agents / f'{LABEL}.plist').write_text('old agent')
        # A login that read the plist before the install, loading mid-install and again after it.
        self.env.update(FAKE_LOGIN_AT='print user/', FAKE_LOGIN_PLIST='/', FAKE_LOGIN_LABEL=LABEL)
        result, _ = self.run_helper('home-server', 'install', str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.login()
        self.assertEqual((self.is_loaded(self.gui), self.is_loaded(self.system)), (False, True))

    def test_server_install_without_gui_session_blocks_the_next_login(self):
        self.env.update(FAKE_GUI_STATUS='113', FAKE_LOGIN_LABEL=LABEL)
        result, _ = self.run_helper('home-server', 'install', str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.env['FAKE_GUI_STATUS'] = '0'
        self.login()
        self.assertEqual((self.is_loaded(self.gui), self.is_loaded(self.system)), (False, True))

    def test_workstation_install_reenables_an_agent_a_server_install_disabled(self):
        self.env['FAKE_LOGIN_LABEL'] = LABEL
        self.assertEqual(self.run_helper('home-server', 'install', str(self.source))[0].returncode, 0)
        result, _ = self.run_helper('portable-macos-workstation', 'install', str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.is_loaded(self.gui), self.is_loaded(self.system)), (True, False))

    def test_server_stops_when_the_login_agent_will_not_unload(self):
        self.load(self.gui)
        self.env['FAKE_STUCK'] = self.gui
        result, _ = self.run_helper('home-server', 'install', str(self.source))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('still loaded', result.stderr)
        self.assertEqual((list(self.daemons.iterdir()), self.is_loaded(self.system)), ([], False))

    def test_server_unloads_a_legacy_user_domain_copy(self):
        self.load(self.legacy_user)
        result, _ = self.run_helper('home-server', 'install', str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.is_loaded(self.legacy_user), self.is_loaded(self.system)), (False, True))

    def test_workstation_unloads_a_legacy_user_domain_copy(self):
        self.load(self.legacy_user)
        result, _ = self.run_helper('portable-macos-workstation', 'install', str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.is_loaded(self.legacy_user), self.is_loaded(self.gui)), (False, True))

    def test_server_without_sudo_changes_nothing(self):
        self.env['FAKE_SUDO'] = 'deny'
        (self.agents / f'{LABEL}.plist').write_text('old agent')
        result, calls = self.run_helper('home-server', 'install', str(self.source))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('sudo -v', result.stderr)
        self.assertTrue((self.agents / f'{LABEL}.plist').exists())
        self.assertEqual(list(self.daemons.iterdir()), [])
        self.assertEqual(calls, [])

    def test_server_rejects_daemon_running_as_another_user(self):
        self.source.write_text(plist('root'))
        result, calls = self.run_helper('home-server', 'install', str(self.source))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((list(self.daemons.iterdir()), calls), ([], []))

    def test_server_bootstrap_failure_is_reported(self):
        self.env['FAKE_BOOTSTRAP_STATUS'] = '5'
        result, _ = self.run_helper('home-server', 'install', str(self.source))
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('loaded in system', result.stdout)

    def test_workstation_never_uses_sudo(self):
        result, calls = self.run_helper('portable-macos-workstation', 'install', str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.agents / f'{LABEL}.plist').read_text(), self.source.read_text())
        self.assertFalse([c for c in calls if c.startswith('sudo ')])
        self.assertTrue(self.is_loaded(self.gui))

    def test_workstation_without_gui_session_defers_to_login(self):
        self.env['FAKE_GUI_STATUS'] = '1'
        result, calls = self.run_helper('portable-macos-workstation', 'install', str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('next login', result.stdout)
        self.assertFalse([c for c in calls if c.startswith('launchctl bootstrap')])

    def test_workstation_removes_a_stray_daemon(self):
        (self.daemons / f'{LABEL}.plist').write_text('stray daemon')
        self.load(self.system)
        result, _ = self.run_helper('portable-macos-workstation', 'install', str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.daemons / f'{LABEL}.plist').exists())
        self.assertEqual((self.is_loaded(self.system), self.is_loaded(self.gui)), (False, True))

    def test_workstation_unloads_a_daemon_whose_plist_is_gone(self):
        self.load(self.system)
        result, _ = self.run_helper('portable-macos-workstation', 'install', str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.is_loaded(self.system), self.is_loaded(self.gui)), (False, True))

    def test_workstation_stops_when_the_daemon_will_not_unload(self):
        self.load(self.system)
        self.env['FAKE_STUCK'] = self.system
        result, _ = self.run_helper('portable-macos-workstation', 'install', str(self.source))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('still loaded', result.stderr)
        self.assertFalse(self.is_loaded(self.gui))


if __name__ == '__main__':
    unittest.main()
