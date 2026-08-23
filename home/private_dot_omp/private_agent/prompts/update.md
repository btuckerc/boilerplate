---
description: Upgrade the pinned OMP release with omp-baseline, never omp update
argument-hint: "[version]"
model: xai-oauth/grok-4.6
restore: true
---
Upgrade the shared OMP pin. `$1` is an exact version when given. Otherwise use GitHub latest from `omp-baseline check-upstream`.

Do not run `omp update`. That command installs an unreviewed binary and fights the fleet pin.

1. Read the `omp-config` skill.
2. Inspect Git status. Leave unrelated dirty files alone.
3. Run `omp-baseline check-upstream`.
4. Read the target GitHub release notes.
5. Run `omp-baseline upgrade --dry-run`, then `omp-baseline upgrade VERSION`.
6. Run `omp-baseline validate --strict`.
7. Stop. Do not commit or reconcile unless the user asked.

Report pin before and after, the three pin-file diff, validate result, and that fleet follow-up is `decent-angl-sync reconcile --with-scripts` after a reviewed commit.
