---
name: decent-angl-config
description: Reconcile the shared chezmoi baseline across MacBook, Mac Mini, and T14. Use for config drift, publishing from any machine, capturing live changes, fleet rollout, or convergence checks.
---

# Decent Angl config

Published `master` is authoritative. Any fleet machine may author a reviewed
commit; no mutable live filesystem silently wins.

## Invariants

- The only editable checkout is `~/src/boilerplate`.
- `~/.local/share/chezmoi` resolves to that checkout. `adopt-source` preserves
  and replaces an old independent source tree.
- Dirty trees that are not publishing commits are stashed around a
  fast-forward, then restored. Never auto-commit, never `reset --hard` onto
  local work, never publish a dirty tree. Diverged history still blocks.
  An uncommitted OMP pin upgrade is local only. Leave it dirty and the
  scheduled guard stashes it, applies published master, and the fleet stays
  on the old pin.
- Clean commits flow both ways: remote commits fast-forward and apply; local
  commits apply and publish.
- Scheduled applies exclude scripts. Use `reconcile --with-scripts` only for a
  reviewed change that needs script effects. New
  `home/dot_local/bin/executable_*` dest files are scripts. After publish,
  each machine needs a targeted `chezmoi apply` of those paths or
  `reconcile --with-scripts`. `command not found` on a new wrapper is
  "the dest file was never applied" until you have checked PATH and the
  dest path.

- Secrets and runtime state stay outside Git. Use `bitwarden-secrets`.

## Workflow

Start with `decent-angl-sync status`. If `source=split`, run `adopt-source`. If
`dirty=yes` while publishing local commits, stop and commit or stash. If
`skills=invalid`, dest skill projections are stale or a `references/` file is
unlinked in dest SKILL.md; `decent-angl-skills sync` then re-validate. If the
machine is only behind or already matches origin, reconcile stashes, applies,
then restores. A stash apply conflict leaves work in the stash and writes the
drift marker.

Capture an intentional live-file change with:

```sh
decent-angl-sync capture ~/.config/example/file
```

Review the source diff and platform scope, validate, commit intentionally, then
run `decent-angl-sync reconcile`. Never capture secrets or runtime state.

For source edits, change `~/src/boilerplate`, validate every affected platform,
commit, and reconcile. Reconciliation fails closed on unsafe Git, secret, skill,
or live-file state.

Omarchy changes must pass `omarchy-roaming-sync validate --strict`; OMP changes
must pass `omp-baseline validate --strict`.

Install the scheduled guard with `decent-angl-sync install-guard`. A
`~/.local/state/decent-angl/config-drift` marker requires review.
