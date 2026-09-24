---
name: model-eval
description: Weigh a new or changed model for the OMP lanes (director, escalation, worker, local) using prices, real token mix, benchmarks, and quota before adopting it.
argument-hint: "[provider/model ...]"
disable-model-invocation: true
---

# Model evaluation

Decide whether a candidate model earns a lane. Adoption itself follows the
`omp-config` upgrade path; this skill produces the decision and its evidence.

## Lanes

| Lane | Role/agent | Pool | Current |
| --- | --- | --- | --- |
| Director | `default` | Anthropic | Opus medium |
| Escalation | `plan` → `architect`/`astra` | Codex | Astra medium |
| Escalation, second opinion | `fable` | Anthropic, capped at half | Fable medium |
| Cloud worker | `task`, `smol` | Codex | Luna medium/low |
| Local worker | `nous` | nous GPU, no quota | Qwen3.8 27B |

A candidate must beat the incumbent for one lane on quality per unit of that
lane's pool. Near-equal quality on a different pool can still win for
escalation, because it spreads load.

## Steps

1. **Discover.** Run `omp models` after `omp-baseline check-upstream`. A model
   absent from discovery needs an OMP pin, auth, or `enabledModels` change first.
2. **Price and shape.** Run
   `python3 ~/.local/share/decent-angl/skills/model-eval/scripts/compare.py CANDIDATE [INCUMBENT]`.
   The script blends catalog prices by the real 14-day OMP token mix.
   That mix is dominated by cache reads, so read price usually drives the
   blend. `x base` compares cost against the director only within the same
   provider pool; Anthropic and Codex allowances are separate.
3. **Benchmarks.** Record at least two sources in
   (references/benchmarks.md): the vendor system card or post, plus one
   independent or cross-vendor table. Prefer agentic coding benchmarks
   (Terminal-Bench, SWE-bench Pro, DeepSWE, FrontierSWE). Note the effort
   level for every number; vendor tables mix efforts.
4. **Quota fit.** Run `omp-quota`. A lane that exhausts its pool before the
   weekly reset loses to a slightly weaker model on a pool with headroom.
5. **Smoke.** Run `omp -p --mode json --no-session --model CANDIDATE --thinking medium "Reply OK"`
   and confirm the exact `provider`/`model` in the response. For a worker or
   director candidate, also run one real bounded task with an independent check.
6. **Decide.** Write a one-line verdict per lane (adopt / trial / reject) with
   the deciding number. Then adopt through `omp-config`: change the IDs in
   `config.yml` roles/`enabledModels`, and for Anthropic models add a 272K
   `contextWindow` override in `models.yml`. Run `omp-baseline validate`.
   Update (references/benchmarks.md) with the new snapshot and date.

## Rules of thumb

- Medium effort is the default; raise it only on a measured gain. On
  CursorBench, Opus 5.5 high scored +3.5 points for about +33% cost per task.
- Local first: a nous model that passes the worker's contracts costs no
  subscription quota.
- One lane per model family per pool is enough. Do not add a lane that no rule
  routes to.
