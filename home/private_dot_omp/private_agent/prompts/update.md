---
description: Update the pinned OMP release in the shared baseline
argument-hint: "[version]"
model: xai-oauth/grok-4.6
restore: true
---
Update OMP for this workstation baseline. Use `$1` when provided; otherwise discover the latest stable release and pin that exact version.

- Inspect Git status first and preserve unrelated changes.
- Review the target release and its checksums or attestations.
- Update every intentional OMP version pin in `~/src/boilerplate`.
- Sync the changed files to the active chezmoi source and apply only the affected targets.
- Install through mise; do not use OMP's self-updater for this pinned setup.
- Verify the version, configuration parse, provider registry, Python dependency check, and that `omp models xai-oauth --json` still lists Grok 4.6 thinking efforts. Download `lfm2-350m` on the machine if session titles need a local model.
- Never copy `~/.omp/agent/agent.db`, tokens, sessions, caches, or logs into Git.
