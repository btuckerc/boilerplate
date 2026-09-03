---
description: Upgrade the pinned OMP release with omp-baseline, never omp update
argument-hint: "[version]"
model: xai-oauth/grok-4.6
restore: true
---
Upgrade the shared OMP pin. `$1` is an exact version when given. Otherwise use GitHub latest from `omp-baseline check-upstream`.

Do not run `omp update`. That command installs an unreviewed binary and fights the fleet pin.

1. Read the `omp-config` skill.
2. Inspect Git status. Leave unrelated dirty files alone. Pin files must be Git-clean.
3. Run `omp-baseline check-upstream`.
4. Read the target GitHub release notes.
5. Run `omp-baseline upgrade --dry-run`, then `omp-baseline upgrade VERSION`.
6. Re-read live `omp models`. Rewrite any dead catalog IDs in `config.yml` and `omp-baseline` checks. 18.1.5 collapsed Antigravity Gemini 3.8 to `google-antigravity/gemini-3.8-flash` plus `:high`/`:low`.
7. Run `decent-angl-skills sync`. `validate` audits source and live dest; a dest `references/` file without a dest SKILL.md link fails even when source is linked.
8. Run `omp-baseline validate --strict`. That is the commit gate. It does not roll back the pin. Unrelated dest skill drift fails it.
9. Stop unless the user asked to publish. An uncommitted pin is local only. Scheduled reconcile stashes dirty trees and applies published master, so the fleet stays on the old pin until you commit.
10. When publishing: commit the pin files plus catalog/config follow-ups, then `decent-angl-sync reconcile --with-scripts`. Other hosts: `omp-baseline pull`.

Report pin before and after, the three pin-file diff, catalog ID changes, validate result, and whether the pin is published.
