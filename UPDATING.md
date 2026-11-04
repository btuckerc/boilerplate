# Updating the fleet

Edit `~/src/boilerplate`, review and commit the intended changes, then publish.
MacBook, Mac Mini, and T14 share published `master`; any host may author.
`~/.local/share/chezmoi` must resolve to that checkout.

## Inspect and publish

```sh
cd ~/src/boilerplate
decent-angl-doctor --fleet
git status --short
git diff
python3 utils/scripts/check_baseline.py
decent-angl-skills audit-source
```

Stage explicit paths or hunks, inspect `git diff --cached`, and commit. Review
all outgoing commits, including earlier unpublished work. Then:

```sh
decent-angl-sync publish
```

Publication validates an exported committed HEAD, scans outgoing history for
credential signatures and forbidden runtime paths, and pushes that exact SHA.
Unrelated staged, unstaged, or untracked edits may remain. It does not apply live
files or include uncommitted changes. The scanner is a guardrail, not proof that
arbitrary data is safe to publish.

## Apply on a host

```sh
decent-angl-sync reconcile
decent-angl-doctor
```

Reconcile fetches, explicitly publishes local commits if needed, fast-forwards,
and applies committed state. It refuses divergence. The native 15-minute guard
does the same but never publishes; it never pushes, stashes, resets, or commits.
Mutation commands share a kernel lock; a collision exits 75 and can be retried.

Uncommitted work never deploys. Edited sources hold back only their own
targets; everything else applies. The whole apply defers when working edits
differ from incoming commits that change the same path, or change shared inputs
(`.chezmoidata`, `.chezmoitemplates`, `.chezmoiignore`, shared skills). Edits
already identical to the incoming commit (work mirrored from the publishing
host) are restored so the fast-forward lands. A committed change to
`.chezmoi.toml.tmpl` reruns `chezmoi init` non-interactively.
`decent-angl-sync status` prints the next `apply=` scope.

A host without a GitHub credential can fetch the public repository over HTTPS
and push over SSH: `git remote set-url origin https://github.com/btuckerc/boilerplate.git`,
then `git remote set-url --push origin git@github.com:btuckerc/boilerplate.git`.

`config-pending` in `~/.local/state/decent-angl` records held or deferred work.
`config-drift` records a failed guard operation.
The guard logs only when its result changes. Doctor reports cached Git counts,
source/applied/binary versions, service exits, and backup job timestamps. JSON
output is available with `--json`; `--strict` exits nonzero when review is needed.

Chezmoi `--exclude scripts` skips `run_*` hooks. Ordinary `executable_*` files
still deploy. Reconcile excludes hooks by default. For reviewed installation or
service hooks, use `decent-angl-sync reconcile --with-scripts` on a clean host.
A changed mise pin needs `mise install TOOL@VERSION` on each host; the ordinary
guard deliberately does not install tool upgrades.

For a change under active development, preview with `chezmoi diff` and apply the
explicit targets. Do not use broad `--force` to clear conflicts. If live state
contains intended changes, capture those targets with `decent-angl-sync capture`
and review the source diff. Secrets, auth, history, caches, and databases remain
machine-local. Use `decent-angl-sync adopt-source` to preserve and replace an old
independent chezmoi clone.

## Tool and skill changes

- Choose and test exact mise pins in `home/dot_config/mise/config.toml`.
  Check upstream release notes and backend metadata before choosing a version.
- Use `omp-baseline upgrade` and `omp-baseline validate --strict` for OMP.
  Never run `omp update`. Its manifest and setup hook pins must agree. Validate
  is read-only and includes the `omp-agent-policy` agent check against native
  `omp models --json` and `omp config list --json` evidence; its mirror is
  pinned to one OMP version (18.16.0), so an upgrade re-verifies it first and a
  rollback reverts the upgrade commit with it (then `chezmoi apply` the reverted
  non-manifest targets before `omp-baseline apply`). It fails the default profile when
  `task.structured` is off (18.10.2+ default: no `yield`, schemas dropped). It certifies
  static policy for a fresh depth-1 dispatch and defers the serving model (auth
  fallback) and MCP proxies to `omp-agent-smoke`. An unreviewed `OMP_*`/`PI_*`
  variable, launch-dir dotenv key, MCP or settings source fails closed. Its
  native probes run in a scratch HOME under a shell jail (bwrap on Linux,
  sandbox-exec on macOS) so no `!command` config value or stored key executes;
  a missing jail, or a `!command` value in any settings layer or models file,
  fails validate. The smoke proves each MCP proxy's server from the prompt's
  route or inventory label, not from a name prefix. A new or edited OMP
  extension needs its sha256 reviewed into the checker's `REVIEWED_EXTENSIONS`, and
  a custom command module (the `/review` override included) into `REVIEWED_COMMANDS`.
  `omp-baseline repair` fixes runtime permissions.
- Use the shared Codex model policy and `codex-baseline` wrapper. Account state
  remains local. See [the Codex baseline](home/private_dot_codex/README.md).
- Native OS packages belong in the Brewfile or platform prerequisites. Removing
  a declaration does not authorize uninstalling unrelated installed software.
- Shared skills originate in `home/dot_local/share/decent-angl/skills`. Apply
  their targets, run `decent-angl-skills sync`, and validate the projections.
- Omarchy changes require `omarchy-roaming-sync validate --strict` on Linux.
  An offline host remains unverified until it returns.

## Validation and recovery

For sync or bootstrap changes, run the regression suite:

```sh
python3 utils/scripts/check_baseline.py
python3 -m unittest discover -s utils/scripts -p 'test_*.py'
```

Tests use temporary Git repositories and fake installers. The chezmoi contract
tests use the installed binary against isolated source and destination trees.
They do not provision a fresh operating system. A fresh-host acceptance test
must also verify shell startup, tool installation, host data, native jobs, and
local authentication on macOS and Linux.

Rollback a published change with a reviewed `git revert`, then publish and
reconcile. Install the restored tool pin where required. This restores managed
source and files; arbitrary hook side effects and native package changes may
need explicit repair. Retain working backups and use the restore-smoke job to
check recovery. Diagnose failed maintenance before running retention changes.

Scheduled restic jobs (`restic-scheduled-job`) serialize on a per-host kernel
lock (`lockf` on macOS, `flock` on Linux, released when the holder exits), clear
only stale repository locks before each run (`restic unlock`, never
`--remove-all`), and wait up to 5 minutes on a live lock. The previous scheduler
serialized on a `restic-scheduler/lock` directory lease instead, which the kernel
lock cannot see, and its jobs cannot all be recognized while they run (stdin,
copies, orphaned helpers). The upgrade therefore needs one reboot per host: the
first run of the new scheduler records the boot id (`kern.bootsessionuuid` on
macOS, `/proc/sys/kernel/random/boot_id` on Linux) in the machine-local
`~/.local/state/decent-angl/restic-scheduler/kernel-lock-v2-origin-boot`, and
every job is recorded as failed, before touching a repository, until the host
has booted since. An unreadable boot id or record also fails the run. After
`chezmoi apply`, run `restic-schedule-apply` (it arms the record via
`restic-scheduled-job --prepare-kernel-lock-migration`, which needs no password
or repository), then reboot; a logout, reload or sleep does not count. Legacy
leases are left alone. The record must not be copied between hosts. Rolling
back to the lease scheduler and forward again needs the record deleted before
the new scheduler returns, then another reboot. A job whose SFTP host does not answer
(only an `nc` report of no route, timeout or DNS failure) logs `outcome=skipped`
and exits 0; a host that refuses the connection, a probe failure `nc` reports any
other way, or a host that is this machine (localhost, a loopback `HostName` alias,
its own hostname or interface address, in any spelling the resolver accepts),
always runs. A missing job helper is recorded as a failed run; an unknown
`--repo-target`, or any argument the scheduler does not take (it passes none to
the job helper), is a usage error and records nothing (`machine` and `primary`
are recorded as `local`). In
`~/.local/state/decent-angl/restic-scheduler/`, every run writes
`last-run.<target>.<job>`, each success writes `last-success.<target>.<job>`,
and the first run writes `first-run.<target>`. From these the doctor flags a
backup older than 3 days, a monthly job older than 40, and a monthly job that
has never succeeded once it ran or 40 days after the first run.
The macmini reaches its own repository over loopback SFTP, because launchd jobs
lack TCC access to the external volume. That needs a host-local key at
`~/.ssh/restic-loopback` whose `authorized_keys` entry starts with
`from="127.0.0.1,::1",restrict,command="internal-sftp"`, plus a pinned
`localhost` host key in `~/.ssh/known_hosts`.

Headless macOS jobs (restic, the sync guard, the omp-baseline guard) are
installed by `decent-angl-launchd install`, which picks the domain from the
machine role. The home-server (macmini) runs them as system LaunchDaemons with
`UserName` set to its admin account, so they keep running when no one or
another account holds the console. Installing them needs passwordless or cached
sudo (`sudo -v`); without it the install changes nothing and fails. The old
login agent is disabled first (`launchctl disable user/<uid>/<label>`, which
gui/<uid> shares and which works with no GUI session), so no later login loads
it; its plist moves to `~/.local/state/decent-angl/launchd-retired/`, and any
loaded copy (in gui/<uid>, or `user/<uid>` from older installs) is booted out.
Laptops keep per-user LaunchAgents, and an install there re-enables the label
and removes any stray daemon or `user/<uid>` copy. Both paths
judge by what launchd has loaded (a service survives deletion of its plist) and
fail if a bootout does not take effect within 10 seconds. The doctor flags a
copy loaded or installed in the wrong domain; on the home-server that check
needs passwordless sudo, and it says so when unavailable. Jobs that need GUI
or TCC access (omp-serve, Obsidian, iMessage) stay login agents and stop while
their user is logged out. Rollback: `sudo launchctl bootout system/<label>`,
delete `/Library/LaunchDaemons/<label>.plist`, move the retired plist back to
`~/Library/LaunchAgents/`, `launchctl enable user/<uid>/<label>`, and
`launchctl bootstrap gui/<uid>` it at the next login.

Use `decent-angl-doctor --fleet --json` as input to an on-demand agent review.
It emits selected state fields and counts, never raw configs, logs, or secrets.
Keep mutation in reviewed commands. No Codex scheduled task is required.
