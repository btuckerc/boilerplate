#!/usr/bin/env python3
"""omp-baseline validate is observational and treats failed probes as errors."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "home/dot_local/bin/executable_omp-baseline"

# `mise exec -- chezmoi CMD ...` and `mise exec -- bun ...` stub. Probe results
# come from the environment so each test picks which probe fails; bun is real.
MISE = """#!/bin/sh
[ "$1" = exec ] && shift 2
tool="$1"; shift
[ "$tool" = bun ] && exec "$REAL_BUN" "$@"
[ "$tool" = chezmoi ] || exit 127
case "$1" in
  diff) exit "${FAIL_DIFF:-0}" ;;
  managed) [ -n "$FAIL_MANAGED" ] && exit "$FAIL_MANAGED"; printf '%s\\n' "${MANAGED_OUT:-.omp/agent/config.yml}" ;;
  *) exit 0 ;;
esac
"""
# Probes run where /bin/sh cannot start, so the omp stub is a bash script.
OMP = """#!/usr/bin/env bash
[ "$1" = --version ] && { echo "${VERSION_OUT:-omp/18.12.1}"; exit "${VERSION_EXIT:-0}"; }
[ -n "$OMP_LOG" ] && echo "$HOME $*" >>"$OMP_LOG"
if [ "$1 $2" = "models vllm" ]; then
  [ -n "$VLLM_EXIT" ] && exit "$VLLM_EXIT"
  printf '%s' "$VLLM_OUT"
  exit 0
fi
if [ "$1 $2 $3" = "config get defaultThinkingLevel" ]; then
  printf '{"value":"high"}\\n'
  exit "${SCALAR_EXIT:-0}"
fi
exit 1
"""


def real_omp():
    """The installed omp binary (not a mise shim, which needs the real HOME)."""
    try:
        found = subprocess.run(["mise", "which", "omp"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    path = found.stdout.strip()
    return path if found.returncode == 0 and os.access(path, os.X_OK) else None


REAL_OMP = real_omp()
# The installed binary: a mise shim needs the real HOME.
REAL_BUN = subprocess.run(["mise", "which", "bun"], capture_output=True, text=True).stdout.strip() or shutil.which("bun")


class OmpBaselineTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="omp-baseline-test-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.home, self.repo, self.mirror = self.root / "home", self.root / "repo", self.root / "mirror"
        self.bin = self.root / "bin"
        for directory in (self.home, self.repo, self.mirror, self.bin):
            directory.mkdir()
        rel = "home/private_dot_omp/private_agent/RULES.md"
        for base in (self.repo, self.mirror):
            (base / rel).parent.mkdir(parents=True)
            (base / rel).write_text("rules\n")
        (self.home / ".omp/agent").mkdir(parents=True)
        (self.home / ".omp/agent/RULES.md").write_text("rules\n")
        self.manifest = self.root / "manifest.tsv"
        self.manifest.write_text(f"# omp-version 18.12.1\nfile\t~/.omp/agent/RULES.md\t{rel}\n")
        for name, body in (("mise", MISE), ("omp", OMP)):
            (self.bin / name).write_text(body)
            (self.bin / name).chmod(0o755)
        self.env = {
            "HOME": str(self.home),
            "PATH": f"{self.bin}{os.pathsep}/usr/bin{os.pathsep}/bin",
            "XDG_STATE_HOME": str(self.root / "state"),
            "OMP_BASELINE_REPO_ROOT": str(self.repo),
            "REAL_BUN": REAL_BUN,
            "OMP_BASELINE_CHEZMOI_ROOT": str(self.mirror),
            "OMP_BASELINE_MANIFEST": str(self.manifest),
        }

    def run_baseline(self, *args, cwd=None, **env):
        return subprocess.run(["bash", str(SCRIPT), *args], env={**self.env, **env}, cwd=cwd or self.root,
                              capture_output=True, text=True, timeout=60)

    def source_root(self):
        """A minimal exported tree for check-source, with a fake checker (logging its
        arguments, PI_CONFIG_FILES and cwd) and an omp stub serving catalog evidence."""
        root = self.root / "snapshot"
        manifest = root / "home/dot_config/decent-angl/omp-baseline-manifest.tsv"
        manifest.parent.mkdir(parents=True)
        manifest.write_text("# omp-version\t18.12.1\n")
        checker = root / "home/dot_local/bin/executable_omp-agent-policy"
        checker.parent.mkdir(parents=True)
        checker.write_text("")
        for rel in ("private_agent", "private_profiles/local/private_agent"):
            (root / "home/private_dot_omp" / rel).mkdir(parents=True)
            (root / "home/private_dot_omp" / rel / "private_config.yml").write_text("theme: dark\n")
        (self.bin / "mise").write_text(MISE.replace(
            '[ "$tool" = bun ] && exec',
            'case "$tool $*" in "bun "*omp-agent-policy*) '
            'printf "%s|%s|%s|%s\\\\n" "$*" "${PI_CONFIG_FILES-unset}" "$PWD" "$(env | grep -c "^PI_MODEL=")" >>"$POLICY_LOG"; '
            'case "$* $FAIL_PROFILE" in *"--profile local"*local) exit 1 ;; esac; exit 0 ;; esac\n'
            '[ "$tool" = bun ] && exec',
        ))
        (self.bin / "omp").write_text(OMP.replace('[ -n "$OMP_LOG" ]', '''[ "$1" = --profile ] && shift 2
if [ "$1 $2" = "models --json" ]; then
  { echo "PROBE $HOME $PWD"; ls -A "$HOME/.omp/agent"; cut -d= -f1 "$HOME/.omp/agent/.env" 2>/dev/null
    env | grep -E "^(PI|OMP)_" | cut -d= -f1; } >>"$STUB_LOG"
  if [ -n "$CATALOG_OUT" ]; then printf '%s\\n' "$CATALOG_OUT"; else printf '{"models":[]}\\n'; fi
  exit 0
fi
[ "$1 $2" = "config list" ] && { printf '{}\\n'; exit 0; }
[ -n "$OMP_LOG" ]'''))
        return root

    def test_check_source_uses_the_snapshot_and_no_live_settings(self):
        # check-source resolves the snapshot physically (cd -P); on macOS the temp dir's /var is /private/var.
        root = self.source_root().resolve()
        agent = self.home / ".omp/agent"
        ran = self.root / "command-ran"
        (agent / "config.yml").write_text(f'modelRoles:\n  default: "{chr(33)}touch {ran}"\n')
        (agent / "models.yml").write_text("not: [valid\n")
        (agent / ".env").write_text("OPENAI_API_KEY=k\nOMP_AUTH_BROKER_URL=http://broker\n"
                                    "PI_SMOL_MODEL=x\nOMP_TASK_ISOLATION=1\n")
        launch = self.root / "launch"
        (launch / ".omp").mkdir(parents=True)
        (launch / ".omp/settings.json").write_text('{"modelRoles": {"default": "x"}}')
        (launch / ".env").write_text("PI_CONFIG_FILES=/nonexistent\n")
        log, omp_log, scratch = self.root / "policy.log", self.root / "omp.log", self.root / "tmp"
        scratch.mkdir()
        # An inherited PROBE_CWD names a project with its own .omp settings.
        env = dict(POLICY_LOG=str(log), STUB_LOG=str(omp_log), TMPDIR=str(scratch),
                   PI_MODEL="live", PI_CONFIG_FILES=str(self.root / "overlay.yml"),
                   OMP_AUTH_BROKER_URL="http://broker", PROBE_CWD=str(launch))
        result = self.run_baseline("check-source", str(root), cwd=launch, **env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        runs = log.read_text().splitlines()
        self.assertEqual(len(runs), 2)
        for run, profile in zip(runs, ("", " --profile local")):
            args, config_files, cwd, live_model = run.split("|")
            self.assertTrue(args.startswith(f"{root}/home/dot_local/bin/executable_omp-agent-policy --root {root}{profile} --catalog "), args)
            self.assertEqual((config_files, live_model), (":", "0"))
            self.assertTrue(cwd.startswith(f"{scratch}/omp-baseline-probe."), cwd)
        probes = omp_log.read_text()
        probe_cwds = [line.split()[2] for line in probes.splitlines() if line.startswith("PROBE ")]
        self.assertEqual(len(probe_cwds), 2)
        for cwd in probe_cwds:
            self.assertTrue(cwd.startswith(f"{scratch}/omp-baseline-probe."), cwd)
        self.assertNotIn("config.yml", probes)
        self.assertNotIn("models.yml", probes)
        self.assertIn("OPENAI_API_KEY", probes)
        self.assertIn("OMP_AUTH_BROKER_URL", probes)
        for leaked in ("PI_SMOL_MODEL", "OMP_TASK_ISOLATION", "PI_MODEL"):
            self.assertNotIn(leaked, probes)
        self.assertFalse(ran.exists())
        self.assertEqual([], list(scratch.iterdir()))

        # A relative ROOT still names the snapshot after the checker's cd.
        log.write_text("")
        result = self.run_baseline("check-source", root.name, cwd=root.parent, **env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        runs = log.read_text().splitlines()
        self.assertEqual(len(runs), 2)
        real = root.resolve()
        for run in runs:
            self.assertTrue(run.startswith(f"{real}/home/dot_local/bin/executable_omp-agent-policy --root {real} "), run)
        self.assertEqual([], list(scratch.iterdir()))

        result = self.run_baseline("check-source", str(root), FAIL_PROFILE="local", cwd=launch, **env)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual([], list(scratch.iterdir()))

    def test_check_source_fails_closed(self):
        root = self.source_root()
        scratch = self.root / "tmp"
        scratch.mkdir()
        env = dict(POLICY_LOG=str(self.root / "policy.log"), STUB_LOG=str(self.root / "omp.log"), TMPDIR=str(scratch))
        result = self.run_baseline("check-source", str(root), VERSION_OUT="omp/18.4.4", **env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("installed omp/18.4.4, source pin omp/18.12.1", result.stderr)
        result = self.run_baseline("check-source", str(root), CATALOG_OUT="not json", **env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("probe failed", result.stderr)
        (root / "home/dot_local/bin/executable_omp-agent-policy").unlink()
        result = self.run_baseline("check-source", str(root), **env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checker missing", result.stderr)
        self.assertEqual([], list(scratch.iterdir()))

    def test_check_source_runs_the_candidate_pin(self):
        # A publisher still on the previous release checks the candidate with its pinned one.
        root = self.source_root()
        pinned = self.root / "pinned"
        pinned.mkdir()
        (pinned / "omp").write_text((self.bin / "omp").read_text()
                                    .replace("${VERSION_OUT:-omp/18.12.1}", "omp/18.12.1")
                                    .replace('echo "PROBE $HOME', 'echo "PROBE pinned $HOME'))
        (pinned / "omp").chmod(0o755)
        (self.bin / "mise").write_text((self.bin / "mise").read_text().replace(
            '[ "$1" = exec ]', f'[ "$1" = -C ] && shift 2\ncase "$1" in install) exit 0 ;; where) echo "{pinned}"; exit 0 ;; esac\n[ "$1" = exec ]', 1))
        log = self.root / "omp.log"
        result = self.run_baseline("check-source", str(root), VERSION_OUT="omp/18.4.4",
                                   POLICY_LOG=str(self.root / "policy.log"), STUB_LOG=str(log))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("VERSION omp/18.12.1 matches the source pin", result.stdout)
        self.assertIn("PROBE pinned ", log.read_text())

    def snapshot(self):
        """Contents, modes and (where supported) file attributes under ~/.omp."""
        state = {}
        for path in sorted([self.home / ".omp", *(self.home / ".omp").rglob("*")]):
            entry = [oct(stat.S_IMODE(path.lstat().st_mode))]
            if path.is_file():
                entry.append(hashlib.sha256(path.read_bytes()).hexdigest())
            if shutil.which("lsattr"):
                attrs = subprocess.run(["lsattr", "-d", str(path)], capture_output=True, text=True)
                entry.append(attrs.stdout.split(" ")[0] if attrs.returncode == 0 else "unsupported")
            state[str(path.relative_to(self.home))] = entry
        return state

    def test_failed_diff_probe_is_not_clean(self):
        result = self.run_baseline("status", FAIL_DIFF="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("LIVE    probe failed (chezmoi diff exit 1)", result.stderr)
        self.assertNotIn("OK      ", result.stdout)

    def test_successful_empty_diff_is_clean(self):
        result = self.run_baseline("status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"OK      {self.home}/.omp/agent/RULES.md", result.stdout)

    def test_unterminated_final_manifest_row_is_checked(self):
        # read fails at EOF on a row without a newline; the row is still part of the manifest.
        self.manifest.write_text(self.manifest.read_text().rstrip("\n"))
        result = self.run_baseline("status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"OK      {self.home}/.omp/agent/RULES.md", result.stdout)

    def test_failed_secret_probes_are_errors(self):
        # The fixture repo is not a Git checkout, so git ls-files fails too.
        result = self.run_baseline("validate", FAIL_MANAGED="3")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SECRET  probe failed (git ls-files exit 128)", result.stderr)
        self.assertIn("SECRET  probe failed (chezmoi managed exit 3)", result.stderr)
        self.assertNotIn("boundary clean", result.stdout)

    def test_runtime_path_filters_cannot_fail_open(self):
        # A chezmoi-managed runtime path must be reported even when every grep fails.
        (self.bin / "grep").write_text("#!/bin/sh\nexit 2\n")
        (self.bin / "grep").chmod(0o755)
        result = self.run_baseline("validate", MANAGED_OUT=".omp/agent/agent.db")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SECRET  chezmoi owns runtime paths\n.omp/agent/agent.db", result.stderr)
        self.assertNotIn("chezmoi boundary clean", result.stdout)

    def test_probe_copies_drop_oauth_and_keep_api_keys(self):
        root = self.source_root()
        for rel in (".omp/agent", ".omp/profiles/local/agent"):
            agent = self.home / rel
            agent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(agent / "agent.db") as db:
                db.execute("CREATE TABLE auth_credentials (credential_type TEXT, data TEXT)")
                db.executemany("INSERT INTO auth_credentials VALUES (?, ?)",
                               [("oauth", "refresh-secret"), ("api_key", "key-secret")])
                db.execute("CREATE TABLE settings (key TEXT, value TEXT)")
                db.execute("INSERT INTO settings VALUES ('theme', 'dark')")
        omp = self.bin / "omp"
        omp.write_text(omp.read_text().replace('[ "$1" = --profile ] && shift 2', '''agent="$HOME/.omp/agent"
[ "$1" = --profile ] && agent="$HOME/.omp/profiles/$2/agent"
python3 - "$agent/agent.db" >>"$CREDS_LOG" <<'PY'
import sqlite3, sys
with sqlite3.connect(sys.argv[1]) as db:
    types = [row[0] for row in db.execute("SELECT credential_type FROM auth_credentials ORDER BY credential_type")]
    settings = db.execute("SELECT count(*) FROM settings").fetchone()[0]
print(sys.argv[1], ",".join(types), settings)
PY
[ "$1" = --profile ] && shift 2'''))
        log = self.root / "credentials.log"
        env = dict(POLICY_LOG=str(self.root / "policy.log"), STUB_LOG=str(self.root / "omp.log"),
                   CREDS_LOG=str(log))
        # validate copies the live default and local DBs into source and live profiles.
        result = self.run_baseline("validate", OMP_BASELINE_REPO_ROOT=str(root), **env)
        self.assertNotEqual(result.returncode, 0)  # Other fixture checks deliberately fail.
        rows = log.read_text().splitlines()
        for profile in ("/agent/agent.db", "/profiles/src-default/agent/agent.db",
                        "/profiles/src-local/agent/agent.db", "/profiles/local/agent/agent.db"):
            self.assertTrue(any(profile in row for row in rows), (profile, rows, result.stderr))
        for row in rows:
            self.assertEqual(row.split()[1:], ["api_key", "1"])
        # check-source alone also drops the settings rows.
        log.write_text("")
        result = self.run_baseline("check-source", str(root), **env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        rows = log.read_text().splitlines()
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row.split()[1:], ["api_key", "0"])
        for rel in (".omp/agent", ".omp/profiles/local/agent"):
            with sqlite3.connect(self.home / rel / "agent.db") as db:
                self.assertEqual(db.execute("SELECT count(*) FROM auth_credentials").fetchone()[0], 2)
                self.assertEqual(db.execute("SELECT count(*) FROM settings").fetchone()[0], 1)

    def test_validate_local_oauth_check_is_read_only(self):
        # Other validation checks fail in this fixture; isolate the AUTH result.
        result = self.run_baseline("validate")
        self.assertNotIn("AUTH    ", result.stderr)
        for rel in (".omp/agent", ".omp/profiles/local/agent"):
            with self.subTest(agent=rel):
                path = self.home / rel / "agent.db"
                path.parent.mkdir(parents=True, exist_ok=True)
                with sqlite3.connect(path) as db:
                    db.execute("CREATE TABLE auth_credentials (credential_type TEXT, data TEXT)")
                    db.executemany("INSERT INTO auth_credentials VALUES (?, ?)",
                                   [("oauth", "refresh-secret"), ("api_key", "key-secret")])
                before = self.snapshot()
                result = self.run_baseline("validate")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"AUTH    1 local OAuth login(s) in {path}; logins belong on the nous broker",
                              result.stderr)
                self.assertNotIn("refresh-secret", result.stdout + result.stderr)
                self.assertNotIn("key-secret", result.stdout + result.stderr)
                self.assertEqual(before, self.snapshot())
                with sqlite3.connect(path) as db:
                    db.execute("DELETE FROM auth_credentials WHERE credential_type = 'oauth'")
                result = self.run_baseline("validate")
                self.assertNotIn("AUTH    ", result.stderr)
                self.assertIn(f"AUTH    no local OAuth logins in {path}", result.stdout)
                with sqlite3.connect(path) as db:
                    db.execute("DROP TABLE auth_credentials")
                result = self.run_baseline("validate")
                self.assertNotIn("AUTH    ", result.stderr)
                self.assertIn(f"AUTH    no local OAuth logins in {path}", result.stdout)

    def test_validate_oauth_in_wal_does_not_create_live_shm(self):
        path = self.home / ".omp/agent/agent.db"
        # Leave a committed WAL without a shared-memory file, as a crashed writer can.
        subprocess.run(["python3", "-c", """
import os, sqlite3, sys
db = sqlite3.connect(sys.argv[1])
db.execute("CREATE TABLE auth_credentials (credential_type TEXT, data TEXT)")
db.commit()
db.execute("PRAGMA journal_mode=WAL")
db.execute("INSERT INTO auth_credentials VALUES ('oauth', 'refresh-secret')")
db.commit()
os._exit(0)
""", str(path)], check=True)
        Path(str(path) + "-shm").unlink()
        self.assertTrue(Path(str(path) + "-wal").is_file())
        before = self.snapshot()
        result = self.run_baseline("validate")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"AUTH    1 local OAuth login(s) in {path}; logins belong on the nous broker",
                      result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_validate_reports_but_never_changes_modes_and_repair_fixes(self):
        agent = self.home / ".omp/agent"
        (agent / "agent.db").write_text("db\n")
        (agent / "auth-openai.token").write_text("token\n")
        (agent / "agent.db").chmod(0o644)
        (agent / "auth-openai.token").chmod(0o644)
        agent.chmod(0o755)
        (self.home / ".omp").chmod(0o755)
        before = self.snapshot()

        result = self.run_baseline("validate")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"MODE    expected 700 on {self.home}/.omp, found 755", result.stderr)
        self.assertIn(f"MODE    expected 600 on {agent}/agent.db, found 644", result.stderr)
        self.assertEqual(before, self.snapshot())

        self.run_baseline("repair")
        self.assertEqual(stat.S_IMODE((self.home / ".omp").stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(agent.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((agent / "agent.db").stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((agent / "auth-openai.token").stat().st_mode), 0o600)

    def test_vllm_probe_failure_or_empty_output_is_an_error(self):
        for env in ({"VLLM_EXIT": "3"}, {"VLLM_OUT": ""}, {"VLLM_OUT": "not json"}):
            with self.subTest(**env):
                result = self.run_baseline("validate", **env)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("MODEL   probe failed (omp models vllm --json)", result.stderr)
                self.assertNotIn("READY   vLLM", result.stdout)
        result = self.run_baseline("validate", VLLM_OUT='{"models":[{"id":"Qwen3.8-27B-Swift-Heretic-MXFP4"}]}')
        self.assertIn("MODEL   Swift Heretic Qwen local catalog entry", result.stdout)

    def test_failed_catalog_query_is_not_a_readiness_gap(self):
        # A working catalog without the entry is the nonfatal READY gap; a failed
        # jq query over the same catalog is a failed probe.
        models = self.repo / "home/private_dot_omp/private_agent/private_models.yml"
        models.write_text("providers:\n  vllm:\n    models:\n      - id: Qwen3.8-27B-Swift-Heretic-MXFP4\n")
        result = self.run_baseline("validate", VLLM_OUT='{"models":[]}')
        self.assertIn("READY   vLLM discovery unavailable", result.stdout)
        # The jq the fixture PATH would find (a mise shim needs the real HOME).
        real_jq = shutil.which("jq", path=f"/usr/bin{os.pathsep}/bin")
        if real_jq is None:
            self.skipTest("no jq in /usr/bin or /bin")
        (self.bin / "jq").write_text(
            f'#!/bin/sh\nfor a in "$@"; do case "$a" in *index*) exit 5 ;; esac; done\nexec {real_jq} "$@"\n')
        (self.bin / "jq").chmod(0o755)
        result = self.run_baseline("validate", VLLM_OUT='{"models":[]}')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MODEL   probe failed (omp models vllm --json)", result.stderr)
        self.assertNotIn("READY   vLLM", result.stdout)

    def test_failed_scalar_probe_is_an_error_despite_expected_stdout(self):
        config = self.repo / "home/private_dot_omp/private_agent/private_config.yml"
        config.write_text("defaultThinkingLevel: high\n")
        result = self.run_baseline("validate")
        self.assertIn("CONFIG  effective defaultThinkingLevel high", result.stdout)
        result = self.run_baseline("validate", SCALAR_EXIT="7")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CONFIG  effective defaultThinkingLevel probe failed (omp config get)", result.stderr)
        self.assertNotIn("CONFIG  effective defaultThinkingLevel high", result.stdout)

    def test_failed_version_probe_is_an_error_despite_expected_stdout(self):
        result = self.run_baseline("status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("VERSION omp/18.12.1", result.stdout)
        result = self.run_baseline("status", VERSION_EXIT="7")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("VERSION probe failed (omp --version exit 7)", result.stderr)
        self.assertNotIn("VERSION omp/18.12.1", result.stdout)

    @unittest.skipUnless(os.uname().sysname == "Linux", "lsattr NOCOW check is Linux-only")
    def test_failed_nocow_probe_is_an_error_despite_expected_stdout(self):
        # On btrfs, an lsattr that prints the C attribute but fails is a failed probe.
        (self.bin / "findmnt").write_text("#!/bin/sh\necho btrfs\n")
        # The printed path holds a C (as /home/Carol/... would), outside the attribute field.
        (self.bin / "lsattr").write_text(
            '#!/bin/sh\nprintf "%s /C%s\\n" "${LSATTR_ATTRS:----------------C------}" "$2"\nexit "${LSATTR_EXIT:-0}"\n')
        for name in ("findmnt", "lsattr"):
            (self.bin / name).chmod(0o755)
        result = self.run_baseline("validate")
        self.assertIn("NOCOW   ~/.omp/agent", result.stdout)
        result = self.run_baseline("validate", LSATTR_EXIT="7")
        self.assertIn("NOCOW   probe failed (lsattr) on ~/.omp/agent", result.stderr)
        self.assertNotIn("NOCOW   ~/.omp/agent", result.stdout)
        result = self.run_baseline("validate", LSATTR_ATTRS="----------------------")
        self.assertIn("NOCOW   expected chattr +C on ~/.omp/agent", result.stderr)
        self.assertNotIn("NOCOW   ~/.omp/agent", result.stdout)

    def test_agent_checker_does_not_see_baseline_settings(self):
        # The checker fails on any unreviewed OMP_* variable; validate's own settings
        # (set by the chezmoi hook and fixtures) are not part of a dispatch launch.
        log = self.root / "bun-env"
        (self.bin / "mise").write_text(MISE.replace(
            '[ "$tool" = bun ] && exec',
            'case "$tool $*" in "bun "*omp-agent-policy*) echo ran >>"$BUN_ENV_LOG"; env | grep "^OMP_BASELINE_" >>"$BUN_ENV_LOG"; exit 0 ;; esac\n'
            '[ "$tool" = bun ] && exec',
        ))
        checker = self.repo / "home/dot_local/bin/executable_omp-agent-policy"
        checker.parent.mkdir(parents=True)
        checker.write_text("")
        self.run_baseline("validate", BUN_ENV_LOG=str(log), OMP_BASELINE_SOURCE_APPLIED="1")
        self.assertIn("ran", log.read_text())
        self.assertNotIn("OMP_BASELINE_", log.read_text())

    @unittest.skipUnless(REAL_OMP, "real omp binary not found")
    def test_validate_with_real_omp_leaves_home_and_project_unchanged(self):
        # The real binary hardens agent-dir modes and writes logs and natives
        # under ~/.omp on every config/models/setup call, quarantines a malformed
        # .omp/config.yml in its cwd, loads the cwd's .env, whose
        # PI_CODING_AGENT_DIR would point it back at the live agent dir, and
        # runs configured extensions in `omp models` unless told not to.
        (self.bin / "omp").unlink()
        (self.bin / "omp").symlink_to(REAL_OMP)
        # With a checker present, validate also captures the agent-policy evidence (omp models, config list).
        checker = self.repo / "home/dot_local/bin/executable_omp-agent-policy"
        checker.parent.mkdir(parents=True)
        shutil.copy(SCRIPT.parent / "executable_omp-agent-policy", checker)
        agent = self.home / ".omp/agent"
        sentinel = self.root / "extension-ran"
        extension = self.root / "sentinel.ts"
        extension.write_text(f'import * as fs from "node:fs";\nexport default function () {{ fs.writeFileSync({str(sentinel)!r}, "ran"); }}\n')
        (agent / "config.yml").write_text(f"cycleOrder: [default, fable, task]\nextensions: [{extension}]\n")
        sqlite3.connect(agent / "agent.db").close()
        (agent / "agent.db").chmod(0o644)
        agent.chmod(0o755)
        (self.home / ".omp").chmod(0o755)
        project = self.root / "project"
        (project / ".omp").mkdir(parents=True)
        (project / ".omp/config.yml").write_text("modelRoles: [\n")
        (project / ".env").write_text(f"PI_CODING_AGENT_DIR={agent}\n")
        project_before = sorted((p.name, p.read_bytes()) for p in [*project.iterdir(), *(project / ".omp").iterdir()] if p.is_file())
        scratch = self.root / "tmp"
        scratch.mkdir()
        before = self.snapshot()

        result = self.run_baseline("validate", cwd=project, TMPDIR=str(scratch))
        self.assertNotIn("PROBE ", result.stderr)
        self.assertIn('CONFIG  effective cycleOrder ["default","fable","task"]', result.stdout)
        self.assertEqual(before, self.snapshot())
        project_after = sorted((p.name, p.read_bytes()) for p in [*project.iterdir(), *(project / ".omp").iterdir()] if p.is_file())
        self.assertEqual(project_before, project_after)
        self.assertEqual([], [p.name for p in scratch.iterdir() if p.name.startswith("omp-baseline-probe.")])
        self.assertFalse(sentinel.exists(), "validate executed a configured extension")
        # From a clean cwd the live agent-policy capture runs to completion, still without running the extension.
        result = self.run_baseline("validate", TMPDIR=str(scratch))
        self.assertNotIn("AGENT   probe failed (omp models --json, live default)", result.stderr)
        self.assertEqual(before, self.snapshot())
        self.assertFalse(sentinel.exists(), "validate executed a configured extension")

    @unittest.skipUnless(REAL_OMP, "real omp binary not found")
    def test_validate_runs_no_command_backed_config_value(self):
        # Native omp runs a "!"-prefixed config value as `/bin/sh -c`
        # (config/resolve-config-value.ts:104-145): stored api_key credentials,
        # which `omp models` resolves for built-in discovery, and the headers of
        # a keyless vLLM provider, which it always fetches.
        (self.bin / "omp").unlink()
        (self.bin / "omp").symlink_to(REAL_OMP)
        agent = self.home / ".omp/agent"
        (agent / "config.yml").write_text("cycleOrder: [default, fable, task]\n")
        cwd = self.root / "cwd"
        cwd.mkdir()
        subprocess.run([REAL_OMP, "config", "list", "--json"], env={"HOME": str(self.home), "PATH": "/usr/bin:/bin"},
                       cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, timeout=60, check=True)
        db = sqlite3.connect(agent / "agent.db")
        for provider in ("openrouter", "anthropic", "openai"):
            key = f"!touch {self.root}/credential-{provider}; printf sk-test"
            db.execute("INSERT INTO auth_credentials (provider, credential_type, data) VALUES (?, 'api_key', ?)",
                       (provider, json.dumps({"key": key})))
        db.commit()
        db.close()
        scratch = self.root / "tmp"
        scratch.mkdir()
        ran = lambda: sorted(p.name for p in self.root.iterdir() if p.name.startswith(("credential-", "header-")))
        before = self.snapshot()

        result = self.run_baseline("validate", TMPDIR=str(scratch))
        self.assertNotIn("PROBE ", result.stderr)
        self.assertIn('CONFIG  effective cycleOrder ["default","fable","task"]', result.stdout)
        self.assertEqual([], ran(), "validate ran a stored credential command")
        self.assertEqual(before, self.snapshot())

        (agent / "models.yml").write_text(
            "providers:\n  sentinel-llama:\n    baseUrl: http://127.0.0.1:9/v1\n    api: openai-completions\n"
            "    auth: none\n    discovery:\n      type: llama.cpp\n    headers:\n"
            f"      X-Sentinel: '!touch {self.root}/header-ran; printf value'\n")
        before = self.snapshot()
        result = self.run_baseline("validate", TMPDIR=str(scratch))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"PROBE   {agent}/models.yml: providers.sentinel-llama.headers.X-Sentinel is command-backed",
                      result.stderr)
        self.assertEqual([], ran(), "validate ran a models.yml header command")
        self.assertEqual(before, self.snapshot())
        # Only validate's own temp dirs count: the real omp extracts native libraries (omp-applefm-*.dylib on macOS).
        self.assertEqual([], [p.name for p in scratch.iterdir() if p.name.startswith("omp-baseline-")])

    @unittest.skipUnless(REAL_OMP, "real omp binary not found")
    def test_dotenv_relocating_omp_state_fails_closed(self):
        # The real binary loads agent/.env and re-resolves its directories, so a
        # copied PI_CODING_AGENT_DIR would send probes back to the live agent dir.
        (self.bin / "omp").unlink()
        (self.bin / "omp").symlink_to(REAL_OMP)
        agent = self.home / ".omp/agent"
        (agent / "agent.db").write_text("db\n")
        (agent / "agent.db").chmod(0o644)
        agent.chmod(0o755)
        (self.home / ".omp").chmod(0o755)
        scratch = self.root / "tmp"
        scratch.mkdir()
        for line in (f"PI_CODING_AGENT_DIR={agent}", "export OMP_PROFILE=work", "XDG_DATA_HOME=/elsewhere"):
            with self.subTest(line=line):
                (agent / ".env").write_text(f"OMP_AUTH_BROKER_URL=http://broker\n{line}\n")
                before = self.snapshot()
                result = self.run_baseline("validate", TMPDIR=str(scratch))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"PROBE   {agent}/.env sets an OMP directory or profile variable", result.stderr)
                self.assertEqual(before, self.snapshot())
                self.assertEqual([], [p.name for p in scratch.iterdir() if p.name.startswith("omp-baseline-")])

    def test_upgrade_config_check_runs_in_scratch_home_and_restores_pins(self):
        # upgrade's post-install config check uses omp_probe, which needs the scratch HOME validate prepares.
        pins = {
            "home/dot_config/decent-angl/omp-baseline-manifest.tsv": "# omp-version\t18.4.4\n",
            "home/dot_config/mise/config.toml": '[tools]\n"github:can1357/oh-my-pi" = "18.4.4"\n',
        }
        for rel, text in pins.items():
            (self.repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / rel).write_text(text)
        git = ["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run([*git, "init", "-q"], check=True)
        subprocess.run([*git, "add", "-A"], check=True)
        subprocess.run([*git, "commit", "-qm", "pins"], check=True)
        self.manifest.write_text(self.manifest.read_text().replace("18.12.1", "18.4.4"))
        (self.bin / "mise").write_text(MISE.replace('[ "$1" = exec ]', 'case "$1" in install|reshim) exit 0 ;; esac\n[ "$1" = exec ]'))
        (self.bin / "gh").write_text("#!/bin/sh\necho v18.12.1\n")
        skills = self.home / ".local/bin/decent-angl-skills"
        skills.parent.mkdir(parents=True)
        skills.write_text("#!/bin/sh\nexit 0\n")
        for exe in (self.bin / "gh", skills):
            exe.chmod(0o755)
        scratch, log = self.root / "tmp", self.root / "omp.log"
        scratch.mkdir()
        log.touch()
        result = self.run_baseline("upgrade", "18.12.1", TMPDIR=str(scratch), OMP_LOG=str(log), OMP_BASELINE_IN_GUARD="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("UPGRADE OMP config checks failed; restoring pin 18.4.4", result.stderr)
        # The native probes ran, each under a scratch HOME (the stub's config answers fail the check).
        probes = [line for line in log.read_text().splitlines() if " config get modelRoles" in line]
        self.assertTrue(probes, result.stderr)
        for line in probes:
            self.assertTrue(line.startswith(f"{scratch}/omp-baseline-probe."), line)
        status = subprocess.run([*git, "status", "--porcelain"], capture_output=True, text=True, check=True)
        self.assertEqual("", status.stdout)
        self.assertEqual([], list(scratch.iterdir()))


if __name__ == "__main__":
    unittest.main()
