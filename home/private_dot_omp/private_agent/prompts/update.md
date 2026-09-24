---
description: Upgrade the pinned OMP release with omp-baseline, never omp update
argument-hint: "[version]"
model: openai-codex/gpt-6-astra
restore: true
---
Upgrade the shared OMP pin. `$1` is an exact version when given. Otherwise use GitHub latest from `omp-baseline check-upstream`.

Do not run `omp update`. That command installs an unreviewed binary and fights the fleet pin.

1. Read the `omp-config` skill.
2. Inspect Git status. Leave unrelated dirty files alone. Pin files must be Git-clean.
3. Run `omp-baseline check-upstream`.
4. Read the target GitHub release notes.
5. Run `omp-baseline upgrade --dry-run`, then `omp-baseline upgrade VERSION`.
6. Re-read live `omp models`. Treat discovered Codex and llama.cpp IDs as
   authoritative; rewrite dead catalog IDs in `config.yml`, `models.yml`, and
   `omp-baseline` checks. Keep OpenRouter models manual-only. Bonsai is
   historical-only and must not be restored to the active catalog or launcher.
7. Run `decent-angl-skills sync`. `validate` audits source and live dest; a dest `references/` file without a dest SKILL.md link fails even when source is linked.
8. Run `omp-baseline validate --strict`. That is the commit gate. It does not roll back the pin. Unrelated dest skill drift fails it.
9. Stop unless the user asked to publish. An uncommitted pin is local only.
   Scheduled apply defers dirty source files without stashing them, so the fleet
   stays on the old pin until you commit.
10. When publishing: commit the pin files plus catalog/config follow-ups, then `decent-angl-sync reconcile --with-scripts`. Other hosts: `omp-baseline pull`.

Report pin before and after, the three pin-file diff, catalog ID changes, validate result, and whether the pin is published.
