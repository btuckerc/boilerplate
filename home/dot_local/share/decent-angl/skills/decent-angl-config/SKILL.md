---
name: decent-angl-config
description: Sync, publish, capture, or reconcile the shared chezmoi baseline in ~/src/boilerplate across hosts. Explicit requests only; not for application repos.
---

# Decent Angl config

Published `master` is authoritative. Any fleet machine may author a reviewed
commit; no mutable live filesystem silently wins.

## Invariants

- The canonical checkout is `~/src/boilerplate`. Exported snapshots are for
  validation only; never apply or author changes from them.
- `~/.local/share/chezmoi` resolves to that checkout. `adopt-source` preserves
  and replaces an old independent source tree.
- Author in a worktree (`git -C ~/src/boilerplate worktree add
  ~/src/boilerplate-wt/<task>`), preview with `chezmoi -S <worktree> diff`,
  commit there, then `merge --ff-only` into the
  checkout. Drafts in the checkout itself hold back or defer every apply on
  that host; only live-state capture (`decent-angl-sync capture`,
  `omarchy-roaming-sync sync`) and `omp-baseline upgrade` write there, so
  commit their result promptly. nous publishes through a repo-scoped deploy key; the
  Mac through its own SSH key.
- Publish reviewed commits, not working files. Unrelated dirty edits are fine:
  `publish` validates an exported HEAD and pushes that exact commit. It leaves
  the index, working tree, and live files alone. Review all outgoing commits.
- Never auto-commit, auto-stash, or reset local work. Diverged history requires
  explicit resolution. Uncommitted upgrades remain local.
- Guard and `reconcile` fast-forward and apply committed state only. Edited
  sources hold back their own targets; edits overlapping incoming commits or
  touching shared inputs (`.chezmoidata`, `.chezmoitemplates`, `.chezmoiignore`,
  shared skills) defer the whole apply. Guard never publishes; `reconcile`
  publishes reviewed commits first. A full apply runs live `omp-baseline apply`
  once per revision to install OMP and companion mise pins and validate; a failure
  leaves `config-drift`. Other hosts converge through their own 15-minute guard.
- `--exclude scripts` skips chezmoi `run_*` hooks, not automatic pin installs.
  Ordinary `executable_*` files still deploy. Use `reconcile --with-scripts`
  only for reviewed hooks such as fonts or native prerequisites.
  Check the destination and PATH before diagnosing a missing wrapper.

- Secrets and runtime state stay outside Git. Use `machine-secrets`. The
  publish scanner matches PEM armor (`-----BEGIN … PRIVATE KEY-----`), not
  wrappers that mention the header in source.

## Workflow

Start with `decent-angl-sync status` or `decent-angl-doctor --fleet`. If
`source=split`, run `adopt-source`. In the worktree, preview with
`chezmoi -S <worktree> diff`, stage only the completed task's paths or hunks,
inspect the staged diff, commit intentionally, land with `git merge --ff-only`,
then run `decent-angl-sync reconcile`: it publishes, applies and installs pins.
`decent-angl-sync publish` alone pushes without applying. Other dirty work in
the checkout does not block publication, which checks the exported commit's
OMP agent policy (`omp-baseline check-source`) with the commit's exact pinned
OMP release, installing it into mise when the host still runs another. A
release-audited publish sets `DECENT_ANGL_PUBLISH_RECEIPT` (the omp-audit
`result.json` whose candidate is the outgoing commit) and
`DECENT_ANGL_PUBLISH_PACKET` (its packet, with one `Audited-Range: BASE..COMMIT`
line); a receipt that is not an accepted PASS for exactly that commit and range
refuses publication. If
`skills=invalid`, dest skill projections are stale or a `references/` file is
unlinked in dest SKILL.md; `decent-angl-skills sync` then re-validate.
`apply=` shows what the next reconcile would do. `config-pending` means held or
deferred unfinished work; `config-drift` means a failed
operation. Shared mutating sync commands use a kernel lock.

Capture an intentional live-file change with:

```sh
decent-angl-sync capture ~/.config/example/file
```

Like `omp-baseline upgrade`, `capture` writes into `~/src/boilerplate` itself,
so review, validate and commit its result there promptly, then run
`decent-angl-sync reconcile`. Never capture secrets or runtime state.

For source edits, validate affected platforms in the worktree before landing,
then reconcile. Use `python3 utils/scripts/check_baseline.py` and the sync
regression tests for sync changes. Record offline hosts as unverified.
Publishing scans outgoing
history for credential paths (raw names, any encoding) and signatures, refuses
if a scan errors or ripgrep does not work, and checks the committed source
skills. Runtime paths are whatever `private_agent/.chezmoiignore` and
`private_dot_codex/.chezmoiignore` declare (union with the published base, by
chezmoi target name); keep new runtime files listed there.

Omarchy changes must pass `omarchy-roaming-sync validate --strict`; OMP changes
must pass `omp-baseline validate --strict`.

Install the scheduled guard with `decent-angl-sync install-guard`. A
`~/.local/state/decent-angl/config-drift` marker requires review.
