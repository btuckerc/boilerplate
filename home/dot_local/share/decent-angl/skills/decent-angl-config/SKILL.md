---
name: decent-angl-config
description: Reconcile the shared chezmoi baseline across MacBook, Mac Mini, and T14. Use for config drift, publishing from any machine, capturing live changes, fleet rollout, or convergence checks.
---

# Decent Angl config

Published `master` is authoritative. Any fleet machine may author a reviewed
commit; no mutable live filesystem silently wins.

## Invariants

- The editable checkout is `~/src/boilerplate`. Exported snapshots are for
  validation only; never apply or author changes from them.
- `~/.local/share/chezmoi` resolves to that checkout. `adopt-source` preserves
  and replaces an old independent source tree.
- Publish reviewed commits, not working files. Unrelated dirty edits are fine:
  `publish` validates an exported HEAD and pushes that exact commit. It leaves
  the index, working tree, and live files alone. Review all outgoing commits.
- Never auto-commit, auto-stash, or reset local work. Diverged history requires
  explicit resolution. Uncommitted upgrades remain local.
- The native guard only fast-forwards/applies a clean checkout with no local
  commits. Dirty work defers apply. It never publishes. `reconcile` explicitly
  publishes reviewed commits, then applies only if the checkout is clean.
- `--exclude scripts` skips chezmoi `run_*` hooks. Ordinary `executable_*`
  files still deploy. Use `reconcile --with-scripts` only for reviewed hooks.
  Check the destination and PATH before diagnosing a missing wrapper.

- Secrets and runtime state stay outside Git. Use `bitwarden-secrets`. The
  publish scanner matches PEM armor (`-----BEGIN … PRIVATE KEY-----`), not
  wrappers that mention the header in source.

## Workflow

Start with `decent-angl-sync status` or `decent-angl-doctor --fleet`. If
`source=split`, run `adopt-source`. Stage only the completed task's paths or
hunks, inspect the staged diff, and commit intentionally. Other dirty work
does not prevent `decent-angl-sync publish`. If
`skills=invalid`, dest skill projections are stale or a `references/` file is
unlinked in dest SKILL.md; `decent-angl-skills sync` then re-validate. If the
machine is behind with dirty work, leave it deferred until that work is ready.
`config-pending` means expected unfinished work; `config-drift` means a failed
operation. Shared mutating sync commands use a kernel lock.

Capture an intentional live-file change with:

```sh
decent-angl-sync capture ~/.config/example/file
```

Review the source diff and platform scope, validate, commit intentionally, then
run `decent-angl-sync publish`. Never capture secrets or runtime state.

For source edits, validate affected platforms, then publish. Use
`python3 utils/scripts/check_baseline.py` and the sync regression tests for
sync changes. Record offline hosts as unverified. Publishing scans outgoing
history for credential signatures and checks the committed source skills.

Omarchy changes must pass `omarchy-roaming-sync validate --strict`; OMP changes
must pass `omp-baseline validate --strict`.

Install the scheduled guard with `decent-angl-sync install-guard`. A
`~/.local/state/decent-angl/config-drift` marker requires review.
