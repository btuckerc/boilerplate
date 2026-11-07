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
RUNTIME_DECLARATIONS = ("home/private_dot_omp/private_agent/.chezmoiignore", "home/private_dot_codex/.chezmoiignore",
                        "home/private_dot_claude/.chezmoiignore")


def real_rg():
    """The ripgrep binary itself: a mise shim stops resolving under the fixture's HOME."""
    found = shutil.which("rg")
    if found and os.path.basename(os.path.realpath(found)) != "rg":
        found = subprocess.run(["mise", "which", "rg"], text=True, capture_output=True, check=True).stdout.strip()
    if not found:
        raise RuntimeError("ripgrep is required to run these tests")
    return found


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
        self.executable(self.bin / "rg", f'#!/bin/sh\nexec "{real_rg()}" "$@"\n')
        self.command("git", "init", "--bare", "-b", "master", str(self.remote))
        self.command("git", "init", "-b", "master", str(self.repo))
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.root / "source").symlink_to(self.repo, target_is_directory=True)
        # The snapshot's own omp-baseline: check-source logs the exported root and
        # fails when that root holds a committed bad policy marker.
        self.executable(self.repo / "home/dot_local/bin/executable_omp-baseline", '''#!/bin/sh
[ "$1" = check-source ] || exit 17
printf '%s\\n' "$2" >>"$BASELINE_LOG"
if grep -qs 'bad committed policy' "$2/home/policy"; then
  echo "EFFORT browser expected medium resolved high" >&2
  exit 1
fi
''')
        self.env["BASELINE_LOG"] = str(self.root / "baseline.log")
        self.write("home/dot_local/bin/executable_decent-angl-skills", "#!/bin/sh\nexit 0\n")
        self.write("utils/scripts/check_baseline.py", "import sys\nsys.exit(0)\n")
        self.write("home/example", "initial\n")
        self.write(".chezmoiroot", "home\n")
        # The repo's real runtime declarations: the publisher refuses what they list.
        for decl in RUNTIME_DECLARATIONS:
            self.write(decl, (SCRIPT.parents[3] / decl).read_text())
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
        # The deployed omp-baseline: apply installs pins and validates once per revision.
        self.executable(self.user / ".local/bin/omp-baseline", '''#!/bin/sh
[ "$1" = apply ] && [ "$OMP_BASELINE_SOURCE_APPLIED" = 1 ] || exit 17
echo apply >>"$HOME/live-apply.log"
[ -z "$FAIL_LIVE_APPLY" ] || { echo "MISSING scout expected user definition" >&2; exit 1; }
''')

    def command(self, *args, check=True, **kwargs):
        # surrogateescape: refused names may hold bytes that are not valid UTF-8.
        return subprocess.run(args, env=self.env, text=True, errors="surrogateescape", stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, check=check, **kwargs)

    def git(self, *args):
        return self.command("git", "-C", str(self.repo), *args)

    def write(self, name, text):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def stage(self, name, text):
        # Index-only entry, so the name reaches Git byte for byte even where the filesystem would refuse it
        # (APFS rejects invalid UTF-8) or merge it into an existing entry (APFS opens Home/ as home/).
        blob = self.root / "staged-blob"
        blob.write_text(text)
        sha = self.git("hash-object", "-w", str(blob)).stdout.strip()
        self.git("update-index", "--add", "--cacheinfo", f"100644,{sha},{name}")

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

    def test_publish_runs_no_pre_push_hook(self):
        # A pre-push hook (git-lfs uploads object content there) could send what the scans never saw.
        self.executable(self.repo / ".git/hooks/pre-push", f"#!/bin/sh\ntouch '{self.root / 'hook-ran'}'\n")
        self.outgoing()
        self.run_sync("publish")
        self.assertEqual(self.remote_head(), self.git("rev-parse", "HEAD").stdout.strip())
        self.assertFalse((self.root / "hook-ran").exists())

    def test_terminal_publish_never_pages(self):
        # On a terminal, git pages diff --check; a LESS without F waited for q even on empty output.
        import pty
        sentinel = self.root / "paged"
        for name in ("GIT_PAGER", "PAGER"):
            self.env.pop(name, None)
        self.env.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="core.pager",
                        GIT_CONFIG_VALUE_0=f"touch '{sentinel}'; cat")
        self.outgoing()
        primary, secondary = pty.openpty()
        try:
            result = subprocess.run(["bash", str(SCRIPT), "publish"], env=self.env, stdin=secondary,
                                    stdout=secondary, stderr=subprocess.PIPE, text=True, timeout=60)
        finally:
            os.close(secondary)
            os.close(primary)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(sentinel.exists())

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
        self.assertFalse((self.user / "apply.log").exists())
        self.assertEqual(self.git("stash", "list").stdout, "")

    def check_source_runs(self):
        log = Path(self.env["BASELINE_LOG"])
        return log.read_text().splitlines() if log.exists() else []

    def worktree_state(self):
        return (self.git("diff", "--binary").stdout, self.git("diff", "--cached", "--binary").stdout,
                self.git("status", "--porcelain=v1", "--untracked-files=all").stdout)

    def test_publish_checks_the_committed_snapshot_not_the_worktree(self):
        self.write("home/policy", "bad committed policy\n")
        self.commit("bad policy")
        self.write("home/policy", "corrected but uncommitted\n")
        result = self.run_sync("publish", success=False)
        self.assertIn("EFFORT browser", result.stderr)
        self.assertEqual(self.remote_head(), self.initial)

        self.write("home/policy", "corrected policy\n")
        self.commit("corrected policy")
        self.write("home/policy", "bad committed policy\n")
        self.write("home/unrelated", "staged\n")
        self.git("add", "home/unrelated")
        self.write("home/unrelated", "staged then unstaged\n")
        self.write("home/untracked", "untracked\n")
        before = self.worktree_state()
        result = self.run_sync("publish")
        self.assertIn("receipt none", result.stdout)
        self.assertEqual(self.remote_head(), self.git("rev-parse", "HEAD").stdout.strip())
        self.assertEqual(self.worktree_state(), before)
        runs = self.check_source_runs()
        self.assertEqual(len(runs), 2)
        self.assertTrue(all(run.startswith(str(self.root / "validation/validate.")) for run in runs))
        self.assertFalse(any(Path(run).exists() for run in runs))

    def test_publish_requires_snapshot_baseline(self):
        self.outgoing()
        self.git("rm", "-q", "home/dot_local/bin/executable_omp-baseline")
        self.git("commit", "-m", "drop baseline")
        result = self.run_sync("publish", success=False)
        self.assertIn("Missing snapshot omp-baseline", result.stderr)
        self.assertEqual(self.remote_head(), self.initial)

    def test_publish_and_validate_require_check_baseline(self):
        self.outgoing()
        self.git("rm", "-q", "utils/scripts/check_baseline.py")
        self.git("commit", "-m", "drop check_baseline")
        result = self.run_sync("validate", success=False)
        self.assertIn("Missing check_baseline", result.stderr)
        result = self.run_sync("publish", success=False)
        self.assertIn("Missing snapshot check_baseline", result.stderr)
        self.assertEqual(self.remote_head(), self.initial)

    def key_then_clean(self):
        """B -> U (adds a private key) -> R (deletes it); returns U."""
        self.write("home/backup.pem", "-----BEGIN EC PRIVATE " + "KEY-----\nMHcCAQEE\n")
        self.commit("key fixture")
        unsafe = self.git("rev-parse", "HEAD").stdout.strip()
        self.git("rm", "-q", "home/backup.pem")
        self.commit("remove key fixture")
        return unsafe

    def test_publish_base_is_the_remote_tracking_ref_not_a_local_branch(self):
        # A local branch named origin/master would win the short-name lookup and hide U from the scan.
        unsafe = self.key_then_clean()
        self.git("update-ref", "refs/heads/origin/master", unsafe)
        result = self.run_sync("publish", success=False)
        self.assertIn(f"Refusing credential signature in commit {unsafe}", result.stderr)
        self.assertEqual(self.remote_head(), self.initial)

    def test_publish_snapshot_is_the_pushed_blobs(self):
        # git archive would drop an export-ignore'd file before check-source; the snapshot is written from the blobs.
        self.write(".gitattributes", "home/policy export-ignore\nhome/example export-subst\n")
        self.write("home/policy", "bad committed policy\n")
        self.commit("hidden policy")
        result = self.run_sync("publish", success=False)
        self.assertIn("EFFORT browser", result.stderr)
        self.assertEqual(self.remote_head(), self.initial)

    def test_publish_and_validate_refuse_checkout_altering_attributes(self):
        # A checkout must deploy the scanned bytes: no git-lfs smudge, ident, re-encoding, CRLF or macro.
        self.write("home/dot_config/x/.gitattributes", "*.txt text eol=lf\n# comment\n\n*.md -diff linguist-generated\n")
        self.commit("benign attributes")
        self.run_sync("validate")
        self.run_sync("publish")
        published = self.remote_head()
        refused = ("*.bin filter=lfs diff=lfs merge=lfs -text", "* ident", "*.txt working-tree-encoding=UTF-16",
                   "*.txt eol=crlf", "[attr]lfs filter=lfs", '"a b" text', '"home/example"ident', "home/example\rident")
        # The last case has no trailing newline: read fails at EOF, but Git still applies the rule.
        for line, end in [(line, "\n") for line in refused] + [("home/example ident", "")]:
            with self.subTest(line=line, end=end):
                self.write("home/dot_config/x/.gitattributes", line + end)
                self.assertIn("Refusing checkout-altering attributes", self.run_sync("validate", success=False).stderr)
                self.commit(f"attributes {line}")
                result = self.run_sync("publish", success=False)
                self.assertIn("Refusing checkout-altering attributes in", result.stderr)
                self.assertEqual(self.remote_head(), published)
                self.git("reset", "-q", "--hard", published)

    def test_publish_and_validate_require_home_chezmoiroot(self):
        # The scans read home/ as the chezmoi source root; another root would deploy names they never mapped.
        for content in ("payload\n", None, "home/\n"):
            with self.subTest(content=content):
                if content is None:
                    self.git("rm", "-q", ".chezmoiroot")
                else:
                    self.write(".chezmoiroot", content)
                self.assertIn(".chezmoiroot must be a regular file reading home", self.run_sync("validate", success=False).stderr)
                self.commit(f"root {content!r}")
                bad = self.git("rev-parse", "HEAD").stdout.strip()
                # Restoring home afterwards does not help: the bad commit is still pushed.
                self.write(".chezmoiroot", "home\n")
                self.commit("root restored")
                result = self.run_sync("publish", success=False)
                self.assertIn(f"Refusing commit {bad}: .chezmoiroot must be a regular file reading home", result.stderr)
                self.assertEqual(self.remote_head(), self.initial)
                self.git("reset", "-q", "--hard", self.initial)
        # chezmoi trims surrounding whitespace (trailing whitespace would fail diff --check first).
        self.write(".chezmoiroot", "  home\n")
        self.commit("padded root")
        self.run_sync("validate")
        self.run_sync("publish")

    def test_publish_ignores_replacement_objects(self):
        # refs/replace/U -> a clean V would hide U from rev-list/grep, but the push still sends U.
        unsafe = self.key_then_clean()
        tree = self.git("rev-parse", f"{self.initial}^{{tree}}").stdout.strip()
        clean = self.git("commit-tree", tree, "-p", self.initial, "-m", "clean stand-in").stdout.strip()
        self.git("replace", unsafe, clean)
        result = self.run_sync("publish", success=False)
        self.assertIn(f"Refusing credential signature in commit {unsafe}", result.stderr)
        self.assertEqual(self.remote_head(), self.initial)

    def test_publish_refuses_grafted_repository(self):
        self.key_then_clean()
        (self.repo / ".git/info").mkdir(exist_ok=True)
        (self.repo / ".git/info/grafts").write_text(f"{self.git('rev-parse', 'HEAD').stdout.strip()} {self.initial}\n")
        result = self.run_sync("publish", success=False)
        self.assertIn("Refusing to publish from a shallow or grafted repository.", result.stderr)
        self.assertEqual(self.remote_head(), self.initial)

    def test_publish_refuses_credential_in_commit_message(self):
        self.write("home/example", "changed\n")
        self.git("add", ".")
        self.git("commit", "-m", "token gh" + "p_" + "A" * 36)
        result = self.run_sync("publish", success=False)
        self.assertIn("(commit message or header)", result.stderr)
        self.assertEqual(self.remote_head(), self.initial)

    def test_guard_defers_and_incoming_validation_skips_check_source(self):
        self.outgoing()
        self.run_sync("guard")
        self.assertEqual(self.remote_head(), self.initial)
        self.assertEqual(self.check_source_runs(), [])
        self.run_sync("reconcile")
        self.assertEqual(self.remote_head(), self.git("rev-parse", "HEAD").stdout.strip())
        self.assertEqual(len(self.check_source_runs()), 1)
        # Incoming: another clone publishes; this host fast-forwards and applies.
        other = self.root / "other"
        self.command("git", "clone", "-q", str(self.remote), str(other))
        (other / "home/example").write_text("incoming\n")
        self.command("git", "-C", str(other), "-c", "user.name=F", "-c", "user.email=f@x.invalid",
                     "commit", "-qam", "incoming")
        self.command("git", "-C", str(other), "push", "-q", "origin", "master")
        self.run_sync("guard")
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), self.remote_head())
        self.assertEqual(len(self.check_source_runs()), 1)

    def receipt(self, candidate, start=None, end=None, extra="", **fields):
        import hashlib
        import json
        packet = self.root / "packet.md"
        packet.write_text(f"# packet\nAudited-Range: {start or self.initial}..{end or candidate}\n{extra}")
        data = {"accepted": True, "verdict": "PASS", "release": True, "candidate": candidate,
                "packet_sha256": hashlib.sha256(packet.read_bytes()).hexdigest()}
        data.update(fields)
        result = self.root / "result.json"
        result.write_text(json.dumps(data))
        self.env.update(DECENT_ANGL_PUBLISH_RECEIPT=str(result), DECENT_ANGL_PUBLISH_PACKET=str(packet))
        return result, packet

    def test_receipt_gate_accepts_the_audited_commit(self):
        self.write("home/example", "reviewed\n")
        self.commit("reviewed")
        revision = self.git("rev-parse", "HEAD").stdout.strip()
        result, _ = self.receipt(revision)
        self.assertIn(f"receipt {result}", self.run_sync("publish").stdout)
        self.assertEqual(self.remote_head(), revision)

    def test_receipt_gate_binds_the_outgoing_history(self):
        # Audit B..C with final tree T, then rebuild the unpublished history as
        # B -> U (unreviewed) -> R (restores T): same tree, different commits.
        self.write("home/example", "reviewed\n")
        self.commit("reviewed")
        audited = self.git("rev-parse", "HEAD").stdout.strip()
        tree = self.git("rev-parse", "HEAD^{tree}").stdout.strip()
        self.git("reset", "-q", "--hard", self.initial)
        self.write("home/example", "unreviewed hook change\n")
        self.commit("unreviewed")
        self.write("home/example", "reviewed\n")
        self.commit("restore")
        self.assertEqual(self.git("rev-parse", "HEAD^{tree}").stdout.strip(), tree)
        for candidate, end in ((audited, audited), (tree, tree)):
            with self.subTest(candidate=candidate):
                self.receipt(candidate, end=end)
                self.assertIn("is not the outgoing commit", self.run_sync("publish", success=False).stderr)
                self.assertEqual(self.remote_head(), self.initial)
        self.assertEqual(self.check_source_runs(), [])

    def test_receipt_gate_refuses_and_publishes_nothing(self):
        self.outgoing()
        first = self.git("rev-parse", "HEAD").stdout.strip()
        self.write("home/example", "second\n")
        self.commit("second")
        revision = self.git("rev-parse", "HEAD").stdout.strip()
        cases = {
            "BLOCK": lambda: self.receipt(revision, verdict="BLOCK"),
            "UNVERIFIED": lambda: self.receipt(revision, verdict="UNVERIFIED"),
            "not accepted": lambda: self.receipt(revision, accepted=False),
            "string boolean": lambda: self.receipt(revision, accepted="true"),
            "not release": lambda: self.receipt(revision, release=False),
            "missing release": lambda: self.receipt(revision, release=None),
            "other candidate": lambda: self.receipt(first),
            "ref name": lambda: self.receipt("master", end=revision),
            "range of the last phase only": lambda: self.receipt(revision, start=first),
            "range end differs": lambda: self.receipt(revision, end=first),
            "two ranges": lambda: self.receipt(revision, extra=f"Audited-Range: {self.initial}..{revision}\n"),
        }
        for name, make in cases.items():
            with self.subTest(name):
                make()
                self.assertIn("Receipt gate:", self.run_sync("publish", success=False).stderr)
                self.assertEqual(self.remote_head(), self.initial)
        _, packet = self.receipt(revision)
        packet.write_text(packet.read_text() + "edited after the audit\n")
        self.assertIn("digest", self.run_sync("publish", success=False).stderr)
        self.receipt(revision)
        (self.root / "result.json").write_text("{not json")
        self.run_sync("publish", success=False)
        self.receipt(revision)
        self.env["DECENT_ANGL_PUBLISH_RECEIPT"] = ""
        self.assertIn("empty or unreadable", self.run_sync("publish", success=False).stderr)
        self.receipt(revision)
        del self.env["DECENT_ANGL_PUBLISH_PACKET"]
        self.assertIn("packet", self.run_sync("publish", success=False).stderr)
        self.assertEqual(self.remote_head(), self.initial)
        self.assertEqual(self.check_source_runs(), [])

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

    def test_live_apply_gates_convergence_once_per_revision(self):
        # Pin installation does not depend on chezmoi run_ hooks. An older guard's
        # validate-only receipt for this revision does not count as an apply.
        (self.state / "config-validated-commit").write_text(self.initial + "\n")
        self.env["FAIL_LIVE_APPLY"] = "1"
        result = self.run_sync("guard", success=False)
        self.assertIn("Live omp-baseline apply failed", result.stdout)
        self.assertNotIn("CONFIG  converged", result.stdout)
        self.assertTrue((self.state / "config-drift").exists())
        self.assertFalse((self.state / "config-live-applied-commit").exists())
        del self.env["FAIL_LIVE_APPLY"]
        self.assertIn("CONFIG  converged", self.run_sync("reconcile").stdout)
        self.assertFalse((self.state / "config-drift").exists())
        self.assertEqual((self.state / "config-live-applied-commit").read_text().strip(), self.initial)
        self.run_sync("guard")
        self.assertEqual((self.user / "live-apply.log").read_text().splitlines(), ["apply", "apply"])
        (self.user / ".local/bin/omp-baseline").unlink()
        self.outgoing()
        self.run_sync("publish")
        self.assertIn("Missing live omp-baseline", self.run_sync("guard", success=False).stdout)

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

    def test_deleted_non_ascii_credential_in_outgoing_history_still_blocks(self):
        # Git quotes non-ASCII names ("home/caf\303\251/auth.json"); the scan must read raw names.
        self.git("config", "core.quotePath", "true")
        self.write("home/café/auth.json", "{}\n")
        self.commit("credential fixture")
        self.git("rm", "home/café/auth.json")
        self.commit("remove credential fixture")
        result = self.run_sync("publish", success=False)
        self.assertIn("Refusing runtime or credential paths in commit", result.stderr)
        self.assertEqual(self.remote_head(), self.initial)

    def test_validate_refuses_non_ascii_machine_local_path(self):
        self.git("config", "core.quotePath", "true")
        self.write("home/café/auth.json", "{}\n")
        result = self.run_sync("validate", success=False)
        self.assertIn("home/café/auth.json", result.stderr)

    def failing_rg(self):
        # rg exit 2 is a scan error, not "no match"; both scans must fail closed. The stub passes
        # rg_ready's probe (match home/auth.json, reject home/example) so the scan itself errors.
        self.executable(self.bin / "rg", "#!/bin/sh\ninput=$(cat)\n"
                        "case \"$input\" in home/auth.json) exit 0 ;; home/example) exit 1 ;; esac\n"
                        "echo 'rg: simulated failure' >&2\nexit 2\n")

    def test_publish_credential_path_scan_error_blocks(self):
        self.outgoing()
        self.failing_rg()
        result = self.run_sync("publish", success=False)
        self.assertIn("Credential path scan failed for commit", result.stderr)
        self.assertEqual(self.remote_head(), self.initial)

    def test_validate_machine_local_path_scan_error_blocks(self):
        self.failing_rg()
        result = self.run_sync("validate", success=False)
        self.assertIn("Machine-local path scan failed.", result.stderr)

    def dead_shim_rg(self):
        # A mise shim whose tool is gone exits 1, which reads as "no match".
        self.executable(self.bin / "rg", "#!/bin/sh\necho 'mise ERROR rg is not a valid shim.' >&2\nexit 1\n")

    def test_publish_with_dead_rg_shim_blocks_deleted_credential(self):
        self.write("home/auth.json", "{}\n")
        self.commit("credential fixture")
        self.git("rm", "home/auth.json")
        self.commit("remove credential fixture")
        self.dead_shim_rg()
        result = self.run_sync("publish", success=False)
        self.assertIn("A working ripgrep is required", result.stderr)
        self.assertEqual(self.remote_head(), self.initial)

    def test_validate_with_dead_rg_shim_blocks(self):
        self.dead_shim_rg()
        result = self.run_sync("validate", success=False)
        self.assertIn("A working ripgrep is required for source checks.", result.stderr)

    def publish_added_then_deleted(self, name, index_only=False):
        if index_only:
            self.stage(name, "fixture\n")
            self.git("commit", "-q", "-m", "runtime fixture")
            self.git("rm", "-q", "--cached", name)
        else:
            self.write(name, "fixture\n")
            self.commit("runtime fixture")
            self.git("rm", "-q", name)
        self.git("commit", "-q", "-m", "remove runtime fixture")
        result = self.run_sync("publish", success=False)
        self.assertIn("Refusing runtime or credential paths in commit", result.stderr)
        self.assertEqual(self.remote_head(), self.initial)
        return result

    def test_publish_refuses_declared_runtime_path_in_history(self):
        # private_agent/.chezmoiignore declares secret-placeholder.key machine-local.
        self.publish_added_then_deleted("home/private_dot_omp/private_agent/secret-placeholder.key")

    def test_publish_refuses_runtime_path_behind_chezmoi_attributes(self):
        # private_state/ deploys as state/ in a profile agent dir; cache/x.tmpl as cache/x.
        self.publish_added_then_deleted("home/private_dot_omp/private_profiles/local/private_agent/private_state/x")
        self.publish_added_then_deleted("home/private_dot_omp/private_agent/cache/x.tmpl")

    def test_publish_refuses_codex_runtime_path(self):
        self.publish_added_then_deleted("home/private_dot_codex/history.jsonl")

    def test_outgoing_commit_cannot_narrow_the_declaration(self):
        decl = "home/private_dot_omp/private_agent/.chezmoiignore"
        self.write(decl, "agent.db\n")
        self.write("home/private_dot_omp/private_agent/terminal-sessions/s1", "fixture\n")
        self.commit("narrow the declaration and add runtime state")
        result = self.run_sync("publish", success=False)
        self.assertIn("terminal-sessions/s1", result.stderr)
        self.assertEqual(self.remote_head(), self.initial)

    def test_validate_refuses_declared_runtime_path(self):
        self.write("home/private_dot_omp/private_agent/gpu_cache.json", "{}\n")
        result = self.run_sync("validate", success=False)
        self.assertIn(".omp/agent/gpu_cache.json", result.stderr)

    def test_validate_allows_ordinary_agent_config(self):
        self.write("home/private_dot_omp/private_agent/config.yml", "a: 1\n")
        self.write("home/private_dot_codex/config.toml", "a = 1\n")
        self.run_sync("validate")

    def test_missing_runtime_declaration_blocks(self):
        for decl in RUNTIME_DECLARATIONS:
            self.git("rm", "-q", decl)
        self.commit("drop declarations")
        result = self.run_sync("validate", success=False)
        self.assertIn("is missing.", result.stderr)

    def test_untranslatable_runtime_pattern_blocks(self):
        # Unsupported glob syntax, an absolute path chezmoi rejects, and a .. that resolves elsewhere.
        decl = self.repo / RUNTIME_DECLARATIONS[0]
        original = decl.read_text()
        for pattern in ("cache-[ab]/", "/abs.key", "a/../b.key"):
            decl.write_text(original + pattern + "\n")
            result = self.run_sync("validate", success=False)
            self.assertIn(f"Unsupported runtime pattern in {RUNTIME_DECLARATIONS[0]}: {pattern}", result.stderr)

    def test_double_star_slash_matches_the_declared_dir_itself(self):
        # chezmoi (doublestar): **/runtime.key also ignores runtime.key directly in the agent dir.
        decl = self.repo / RUNTIME_DECLARATIONS[0]
        decl.write_text(decl.read_text() + "**/runtime.key\n")
        self.write("home/private_dot_omp/private_agent/runtime.key", "fixture\n")
        result = self.run_sync("validate", success=False)
        self.assertIn(".omp/agent/runtime.key", result.stderr)

    def test_question_mark_matches_one_multibyte_character(self):
        # chezmoi's ? is one character; scans run in byte mode, where é is two bytes.
        decl = self.repo / RUNTIME_DECLARATIONS[0]
        decl.write_text(decl.read_text() + "?.key\n")
        self.commit("declare one-character keys")
        name = "home/private_dot_omp/private_agent/é.key"
        self.write(name, "fixture\n")
        self.assertIn(".omp/agent/é.key", self.run_sync("validate", success=False).stderr)
        (self.repo / name).unlink()
        self.publish_added_then_deleted(name)

    def test_path_scans_fold_case_for_case_insensitive_hosts(self):
        # On APFS these names are the denied file itself: case variants, long s (U+017F), Kelvin sign (U+212A),
        # and full-folding forms Rust's (?i) misses: sharp s (ss) and the st ligature (U+FB06). Outside home/
        # a long s still aliases a by-path name such as .gitattributes.
        for name in ("home/private_dot_omp/private_agent/AUTH.JSON", "home/x/\u017fessions/s1",
                     "home/private_dot_omp/private_agent/Secret-Placeholder.KEY",
                     "home/private_dot_omp/private_agent/secret-placeholder.\u212aey",
                     "home/x/se\u00dfions/s1", "home/private_dot_omp/private_agent/hi\ufb06ory.db",
                     "utils/.gitattribute\u017f"):
            with self.subTest(name=name):
                self.write(name, "fixture\n")
                self.assertIn("Refusing", self.run_sync("validate", success=False).stderr)
                (self.repo / name).unlink()
        self.publish_added_then_deleted("home/private_dot_omp/private_agent/AUTH.JSON")

    def test_case_insensitive_path_aliases_refuse(self):
        # A Mac checkout (APFS) merges Home/ into home/ and opens .GITATTRIBUTES as .gitattributes. The names are
        # staged index-only so the test builds the same commits on a case-insensitive filesystem.
        for name, content, reported in (
                ("Home/private_dot_omp/private_agent/secret-placeholder.key", "fixture\n", "Home (opened as home)"),
                (".GITATTRIBUTES", "home/example ident\n", ".GITATTRIBUTES (opened as .gitattributes)"),
                ("home/EXAMPLE", "other\n", "home/example (same path as home/EXAMPLE when case-folded)")):
            with self.subTest(name=name):
                self.stage(name, content)
                self.assertIn(reported, self.run_sync("validate", success=False).stderr)
                self.git("commit", "-q", "-m", f"alias {name}")
                self.git("rm", "-q", "--cached", name)
                self.git("commit", "-q", "-m", f"drop {name}")
                result = self.run_sync("publish", success=False)
                self.assertIn(f"Refusing case-insensitive path aliases in commit", result.stderr)
                self.assertIn(reported, result.stderr)
                self.assertEqual(self.remote_head(), self.initial)
                self.git("reset", "-q", "--hard", self.initial)

    def test_runtime_pattern_with_trailing_comment(self):
        # chezmoi: whitespace then # starts a comment, so "runtime.key # note" declares runtime.key.
        decl = self.repo / RUNTIME_DECLARATIONS[0]
        decl.write_text(decl.read_text() + "runtime.key\t# machine-local\n")
        self.write("home/private_dot_omp/private_agent/runtime.key", "fixture\n")
        result = self.run_sync("validate", success=False)
        self.assertIn(".omp/agent/runtime.key", result.stderr)

    def test_runtime_pattern_matches_chezmoi_literal_suffix_target(self):
        # A final .literal stops chezmoi's suffix parsing, and an external_ dir deploys its children unparsed:
        # both sources target .omp/agent/runtime.key.literal.
        decl = self.repo / RUNTIME_DECLARATIONS[0]
        decl.write_text(decl.read_text() + "runtime.key.literal\n")
        self.commit("declare runtime.key.literal")
        self.git("push", "-q")
        self.initial = self.git("rev-parse", "HEAD").stdout.strip()
        for name in ("home/private_dot_omp/private_agent/runtime.key.literal.literal",
                     "home/private_dot_omp/external_agent/runtime.key.literal"):
            with self.subTest(name=name):
                self.write(name, "fixture\n")
                self.assertIn(".omp/agent/runtime.key.literal", self.run_sync("validate", success=False).stderr)
                (self.repo / name).unlink()
                self.publish_added_then_deleted(name)
                self.git("reset", "-q", "--hard", self.initial)

    def test_newline_in_path_name_blocks(self):
        # A newline would split "trace\n.log" into records that no longer match the *.log declaration.
        name = "home/private_dot_omp/private_agent/trace\n.log"
        self.write(name, "fixture\n")
        result = self.run_sync("validate", success=False)
        self.assertIn("Refusing path names containing a newline", result.stderr)
        self.commit("runtime fixture")
        self.git("rm", "-q", name)
        self.commit("remove runtime fixture")
        result = self.run_sync("publish", success=False)
        self.assertIn("Refusing path names containing a newline or \\001 in commit", result.stderr)
        self.assertEqual(self.remote_head(), self.initial)

    def credential_file_blocks(self, name, content, symlink=False):
        # The content scan covers every file, whatever its name, encoding or type, in the tree and in history.
        if symlink:
            (self.repo / name).parent.mkdir(parents=True, exist_ok=True)
            os.symlink(content, self.repo / name)
        else:
            self.write(name, content)
        result = self.run_sync("validate", success=False)
        self.assertIn(f"Refusing credential signatures in: {name}", result.stderr)
        self.commit("credential fixture")
        self.git("rm", "-q", name)
        self.commit("remove credential fixture")
        result = self.run_sync("publish", success=False)
        self.assertIn("Refusing credential signature in commit", result.stderr)
        self.assertIn(name, result.stderr)
        self.assertEqual(self.remote_head(), self.initial)

    def test_credential_signature_in_lock_file_blocks(self):
        self.credential_file_blocks("home/backup.lock", "gh" + "p_" + "A" * 36 + "\n")

    def test_credential_signature_in_binary_file_blocks(self):
        self.credential_file_blocks("home/backup.bin", "\0gh" + "p_" + "A" * 36 + "\n")

    def test_credential_signature_in_symlink_target_blocks(self):
        # git grep skips mode-120000 entries; their stored target text is scanned separately.
        self.credential_file_blocks("home/backup-link", "gh" + "p_" + "A" * 36, symlink=True)

    def test_any_private_key_armor_blocks(self):
        for kind in ("EC ", "DSA ", "ENCRYPTED ", "PGP "):
            with self.subTest(kind=kind):
                block = " BLOCK" if kind == "PGP " else ""
                self.write("home/backup.pem", f"-----BEGIN {kind}PRIVATE " + f"KEY{block}-----\nMHcCAQEE\n")
                result = self.run_sync("validate", success=False)
                self.assertIn("Refusing credential signatures in: home/backup.pem", result.stderr)

    def test_runtime_path_with_invalid_utf8_byte_blocks(self):
        # A raw 0xff byte must not stop [^/]* from matching the *.log declaration.
        name = os.fsdecode(b"home/private_dot_omp/private_agent/\xff.log")
        self.publish_added_then_deleted(name, index_only=True)

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

    def test_behind_guard_settles_edits_matching_incoming(self):
        # Work mirrored from the publishing host: identical content, one
        # tracked edit and one new file, plus an unrelated edit to keep.
        self.peer_commit("remote\n")
        peer = self.root / "peer"
        (peer / "home/new").write_text("new\n")
        self.command("git", "-C", str(peer), "add", ".")
        self.command("git", "-C", str(peer), "commit", "-m", "add new")
        self.command("git", "-C", str(peer), "push")
        self.write("home/example", "remote\n")
        self.write("home/new", "new\n")
        self.write("home/untracked", "keep\n")
        self.run_sync("guard")
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), self.remote_head())
        self.assertEqual(self.git("status", "--porcelain=v1").stdout, "?? home/untracked\n")

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
