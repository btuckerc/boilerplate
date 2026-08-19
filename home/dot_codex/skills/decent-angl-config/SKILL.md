---
name: decent-angl-config
description: Maintain and reconcile the complete shared decent-angl/chezmoi configuration across MacBook, Mac Mini, and T14. Use for cross-machine drift, publishing config from any machine, adopting live changes, fleet rollout, or validating that platform-specific templates remain converged.
---

# Decent Angl Config

Published `master` history is the authority. MacBook is not permanently
privileged: MacBook, Mac Mini, or T14 may author a change, but no machine's
mutable live filesystem silently wins. Chezmoi renders platform and machine
differences from one Git tree.

## Invariants

- The only editable checkout is `~/src/boilerplate`.
- `~/.local/share/chezmoi` is a symlink to that checkout, making the historical
  two source paths the same inode tree. Use `decent-angl-sync adopt-source` to
  preserve and replace an old independent chezmoi clone.
- Never auto-commit working-tree or live changes. Dirty state and diverged Git
  history block reconciliation and preserve both sides for review.
- Clean committed changes may flow in either direction: remote commits
  fast-forward and apply; local commits apply and publish.
- Scheduled applies exclude scripts. Run `decent-angl-sync reconcile
  --with-scripts` interactively when a reviewed change requires packages,
  service installation, or other script effects.
- Credentials, auth databases, sessions, caches, build outputs, and host-local
  state stay outside Git. Use the `bitwarden-secrets` skill for secret-backed
  integrations.

## Workflow

Start with `decent-angl-sync status`. If `source=split`, adopt the canonical
source before doing other work. If `dirty=yes`, inspect the existing changes;
do not stash, reset, or overwrite them without understanding ownership.

For an explicit live-file change, use:

```sh
decent-angl-sync capture ~/.config/example/file
```

Review the generated source diff and platform scoping, run relevant validators,
scan the secret boundary, commit intentionally, then run
`decent-angl-sync reconcile`. Do not use capture for secrets or runtime state.

For source edits, edit `~/src/boilerplate`, validate rendered output on every
affected platform, commit, and reconcile. The command will refuse non-`master`
branches, dirty trees, non-fast-forward histories, secret signatures, and
unattended overwrites of modified live files.

## Platform Ownership

Keep common behavior in portable source. Render host-specific paths, package
managers, services, and UI/desktop files from chezmoi data and ignore rules.
Omarchy/Linux desktop state must also pass `omarchy-roaming-sync validate
--strict`; OMP state must pass `omp-baseline validate --strict`. Those focused
validators complement rather than replace the whole-tree guard.

After initial convergence, install the guard with
`decent-angl-sync install-guard`. A marker at
`~/.local/state/decent-angl/config-drift` is an actionable stop condition, not
permission to overwrite or auto-merge.
