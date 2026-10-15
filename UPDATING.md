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
  pinned to one OMP version (18.10.4), so an upgrade re-verifies it first and a
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

Use `decent-angl-doctor --fleet --json` as input to an on-demand agent review.
It emits selected state fields and counts, never raw configs, logs, or secrets.
Keep mutation in reviewed commands. No Codex scheduled task is required.
