#!/usr/bin/env python3
"""Exercise Git publication/reconciliation with real repos and fake apply tools."""
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "home/dot_local/bin/executable_decent-angl-sync"


class SyncTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="decent-angl-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo, self.remote = self.root / "repo", self.root / "remote.git"
        self.user, self.state = self.root / "user", self.root / "state/decent-angl"
        self.user.mkdir()
        self.state.mkdir(parents=True)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.env = dict(os.environ, HOME=str(self.user), XDG_STATE_HOME=str(self.root / "state"),
                        DECENT_ANGL_REPO_ROOT=str(self.repo), DECENT_ANGL_SOURCE_LINK=str(self.root / "source"),
                        DECENT_ANGL_VALIDATION_ROOT=str(self.root / "validation"),
                        PATH=str(self.bin) + os.pathsep + os.environ["PATH"])
        self.env.pop("DECENT_ANGL_SYNC_LOCK_HELD", None)
        self.command("git", "init", "--bare", "-b", "master", str(self.remote))
        self.command("git", "init", "-b", "master", str(self.repo))
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.root / "source").symlink_to(self.repo, target_is_directory=True)
        self.write("home/dot_local/bin/executable_decent-angl-skills", "#!/bin/sh\nexit 0\n")
        self.write("home/example", "initial\n")
        self.commit("initial")
        self.git("remote", "add", "origin", str(self.remote))
        self.git("push", "-u", "origin", "master")
        self.initial = self.git("rev-parse", "HEAD").stdout.strip()
        # Fake `mise -C HOME exec -- chezmoi CMD ...`: source home/<p> targets $HOME/<p>.
        self.executable(self.bin / "mise", '''#!/bin/sh
if [ "$1" = -C ]; then shift 2; fi
shift
shift
shift
cmd="$1"; shift
case "$cmd" in
  managed)
    case "$*" in
      *"--include dirs"*) python3 -c 'import json,os,sys; [sys.stdout.buffer.write(os.fsencode(n)+bytes([0])) for n in json.loads(os.environ.get("MANAGED_DIRS_JSON","[]"))]'; exit "${FAIL_MANAGED:-0}" ;;
      *) printf '%s\\n' "$HOME/example" "$HOME/other" ;;
    esac ;;
  target-path) for p in "$@"; do [ "$p" = -- ] || printf '%s\\n' "$HOME/${p#*/home/}"; done ;;
  apply) echo "apply $*" >> "$HOME/apply.log"; exit "${FAIL_APPLY:-0}" ;;
  data) [ -z "$STALE_CONFIG" ] || echo "chezmoi: warning: config file template has changed, run chezmoi init to regenerate config file" >&2 ;;
  init) echo init >> "$HOME/init.log" ;;
  *) exit 0 ;;
esac
''')
        self.executable(self.user / ".local/bin/decent-angl-skills", "#!/bin/sh\nexit 0\n")

    def command(self, *args, check=True, **kwargs):
        return subprocess.run(args, env=self.env, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, check=check, **kwargs)

    def git(self, *args):
        return self.command("git", "-C", str(self.repo), *args)

    def write(self, name, text):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def executable(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        path.chmod(0o755)

    def commit(self, message):
        self.git("add", ".")
        self.git("commit", "-m", message)

    def run_sync(self, action, success=True):
        result = self.command("bash", str(SCRIPT), action, check=False)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def remote_head(self):
        return self.command("git", "--git-dir", str(self.remote), "rev-parse", "master").stdout.strip()

    def test_new_directories_created_without_changing_existing_modes(self):
        import json
        existing, new = self.user / 'private', self.user / 'new/nested'
        existing.mkdir(mode=0o700)
        self.env['MANAGED_DIRS_JSON'] = json.dumps([str(existing), str(new)])
        self.run_sync('reconcile')
        self.assertTrue(new.is_dir())
        self.assertEqual(existing.stat().st_mode & 0o777, 0o700)
        self.assertEqual(new.stat().st_mode & 0o777, 0o700)

    def test_directory_enumeration_failure_stops_before_apply(self):
        self.env['FAIL_MANAGED'] = '42'
        self.run_sync('guard', success=False)
        self.assertFalse((self.user / 'apply.log').exists())

    def outgoing(self):
        self.write("home/example", "reviewed\n")
        self.commit("reviewed")

    def dirty(self):
        self.write("home/example", "staged\n")
        self.git("add", "home/example")
        self.write("home/example", "unstaged\n")
        self.write("home/untracked", "untracked\n")

    def snapshot(self):
        return (self.git("diff", "--binary").stdout,
                self.git("diff", "--cached", "--binary").stdout,
                self.git("status", "--porcelain=v1").stdout,
                (self.repo / "home/untracked").read_text())

    def applied(self):
        """Targets passed to the last apply; [] means a full apply."""
        lines = (self.user / "apply.log").read_text().splitlines()
        return [a for a in lines[-1].split()[1:] if not a.startswith("-") and a != "scripts,dirs"]

    def test_publish_preserves_staged_unstaged_and_untracked(self):
        self.outgoing()
        self.dirty()
        before = self.snapshot()
        self.run_sync("publish")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.remote_head(), self.git("rev-parse", "HEAD").stdout.strip())
        self.assertFalse((self.user / "apply.log").exists())
        self.assertEqual(self.git("stash", "list").stdout, "")

    def test_reconcile_publishes_and_holds_dirty_target(self):
        self.outgoing()
        self.dirty()
        before = self.snapshot()
        self.run_sync("reconcile")
        self.assertEqual(before, self.snapshot())
        self.assertNotEqual(self.remote_head(), self.initial)
        self.assertTrue((self.state / "config-pending").exists())
        self.assertEqual(self.applied(), [str(self.user / "other")])

    def test_guard_never_publishes_local_commits(self):
        self.outgoing()
        self.run_sync("guard")
        self.assertEqual(self.remote_head(), self.initial)
        self.assertFalse((self.user / "apply.log").exists())

    def test_guard_preserves_dirty_tree_and_does_not_stash(self):
        self.dirty()
        before = self.snapshot()
        self.run_sync("guard")
        self.assertEqual(before, self.snapshot())
        self.assertEqual(self.git("stash", "list").stdout, "")
        self.assertNotIn(str(self.user / "example"), self.applied())

    def test_shared_input_edit_defers_whole_apply(self):
        self.write("home/.chezmoidata/fleet.yaml", "hosts: []\n")
        self.run_sync("guard")
        self.assertFalse((self.user / "apply.log").exists())
        self.assertIn(".chezmoidata/fleet.yaml", (self.state / "config-pending").read_text())

    def test_edits_outside_chezmoi_source_converge_fully(self):
        self.write("docs/notes.md", "draft\n")
        result = self.run_sync("guard")
        self.assertIn("converged", result.stdout)
        self.assertEqual(self.applied(), [])
        self.assertFalse((self.state / "config-pending").exists())

    def test_stale_config_template_reruns_init_before_apply(self):
        self.env["STALE_CONFIG"] = "1"
        self.run_sync("guard")
        self.assertTrue((self.user / "init.log").exists())

    def test_dirty_config_template_is_not_rendered(self):
        self.env["STALE_CONFIG"] = "1"
        self.write("home/.chezmoi.toml.tmpl", "draft\n")
        self.run_sync("guard")
        self.assertFalse((self.user / "init.log").exists())
        self.assertEqual(self.applied(), [])

    def test_guard_apply_failure_is_not_convergence(self):
        self.env["FAIL_APPLY"] = "23"
        result = self.run_sync("guard", success=False)
        self.assertNotIn("converged", result.stdout)
        self.assertTrue((self.state / "config-drift").exists())
        self.assertFalse((self.state / "config-applied-commit").exists())

    def test_guard_clean_apply_succeeds(self):
        self.run_sync("guard")
        self.assertTrue((self.user / "apply.log").exists())
        self.assertEqual((self.state / "config-applied-commit").read_text().strip(), self.initial)

    def test_failed_skill_audit_blocks_publish(self):
        self.write("home/dot_local/bin/executable_decent-angl-skills", "#!/bin/sh\nexit 8\n")
        self.commit("invalid skill")
        self.run_sync("publish", success=False)
        self.assertEqual(self.remote_head(), self.initial)

    def test_uncommitted_invalid_skill_does_not_block_committed_snapshot(self):
        self.outgoing()
        self.write("home/dot_local/bin/executable_decent-angl-skills", "#!/bin/sh\nexit 8\n")
        self.run_sync("publish")
        self.assertNotEqual(self.remote_head(), self.initial)

    def test_deleted_credential_in_outgoing_history_still_blocks(self):
        self.write("home/auth.json", "{}\n")
        self.commit("credential fixture")
        self.git("rm", "home/auth.json")
        self.commit("remove credential fixture")
        self.run_sync("publish", success=False)
        self.assertEqual(self.remote_head(), self.initial)

    def test_guard_failed_fetch_stops_before_apply(self):
        self.git("remote", "set-url", "origin", str(self.root / "missing"))
        self.run_sync("guard", success=False)
        self.assertFalse((self.user / "apply.log").exists())

    def peer_commit(self, text, name="home/example"):
        peer = self.root / "peer"
        self.command("git", "clone", str(self.remote), str(peer))
        self.command("git", "-C", str(peer), "config", "user.name", "Peer")
        self.command("git", "-C", str(peer), "config", "user.email", "peer@example.invalid")
        (peer / name).write_text(text)
        self.command("git", "-C", str(peer), "add", ".")
        self.command("git", "-C", str(peer), "commit", "-m", "remote update")
        self.command("git", "-C", str(peer), "push")

    def test_behind_overlapping_dirty_guard_does_not_fast_forward(self):
        self.peer_commit("remote\n")
        self.dirty()
        before = self.snapshot()
        self.run_sync("guard")
        self.assertEqual(before, self.snapshot())
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), self.initial)
        self.assertFalse((self.user / "apply.log").exists())
        self.assertIn("home/example", (self.state / "config-pending").read_text())

    def test_behind_disjoint_dirty_guard_fast_forwards_and_holds_edits(self):
        self.peer_commit("remote\n", name="home/other")
        self.dirty()
        before = self.snapshot()
        self.run_sync("guard")
        self.assertEqual(before, self.snapshot())
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), self.remote_head())
        self.assertEqual(self.applied(), [str(self.user / "other")])

    def test_behind_clean_guard_fast_forwards_and_applies(self):
        self.peer_commit("remote\n")
        self.run_sync("guard")
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), self.remote_head())
        self.assertTrue((self.user / "apply.log").exists())

    def test_divergence_stops_reconcile(self):
        self.outgoing()
        self.peer_commit("divergent\n")
        self.run_sync("reconcile", success=False)
        self.assertNotEqual(self.git("rev-parse", "HEAD").stdout.strip(), self.remote_head())
        self.assertFalse((self.user / "apply.log").exists())

    def test_guard_invalid_committed_skill_stops_before_apply(self):
        self.write("home/dot_local/bin/executable_decent-angl-skills", "#!/bin/sh\nexit 8\n")
        self.commit("invalid skill")
        self.git("push")
        self.run_sync("guard", success=False)
        self.assertFalse((self.user / "apply.log").exists())

    def test_kernel_lock_covers_manual_and_guard(self):
        with (self.state / "config-sync.flock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            for action in ("guard", "publish", "reconcile"):
                result = self.run_sync(action, success=False)
                self.assertEqual(result.returncode, 75)
        self.run_sync("guard")


if __name__ == "__main__":
    unittest.main()
