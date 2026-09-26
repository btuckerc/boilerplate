---
name: omp-config
description: Change the shared OMP baseline in chezmoi - upgrades, omp-baseline, provider/model defaults, auth-broker login, config.yml/models.yml. Explicit requests only; never run omp update.
---

# OMP config

## Boundary

- Source: `~/src/boilerplate/home/`
- Live config: `~/.omp/agent/`
- Version pin: `home/dot_config/mise/config.toml`
- Runtime databases, tokens, sessions, caches, logs, usage state, installation
  IDs, and tiny-model weights stay machine-local.

## Invariants

- Pin OMP to the exact reviewed mise release (currently 18.3.1); do not combine
  the shared pin with `omp update`. Use `omp-baseline upgrade` to move the three
  pin sites together.
- Prefer native OMP config and features. Keep native skill discovery enabled.
- Use independent native OAuth logins per machine (Codex, Anthropic); never
  copy refresh credentials. Account count and quota state are machine-local.
  A host without an Anthropic login cannot run the shared Opus default: run
  `omp auth-broker login anthropic` there before `omp-baseline pull`. The
  Codex pool is session-sticky and quota-aware; use `/session pin` when needed.
- Default routing is Claude Opus medium as director. The director owns
  requirements, integration and acceptance; trivial work stays direct. Prefer
  nous for bounded work with runnable checks. The `task`, `commit`, `smol` and
  `tiny` roles (so `task`, `scout`, `sonic`) run on nous Qwen to save Codex
  quota; `vision` stays Luna (text-only local model). The `luna` agent is the
  explicit Codex worker when local capability, context or images are unsuitable.
  Use fresh compact briefs, not the full parent transcript or pre-solved implementations.
- Escalation lanes: Astra medium (`architect` read-only, `astra`
  implementation; both `@plan`) is the default. It matches or beats Fable on
  vendor coding benchmarks (Opus 5.5 system card; OpenAI Astra post) and draws
  from the Codex pool, not the director's. Fable medium (`fable`, `@fable`) is
  used when Codex has less than 20% remaining, or as a second opinion from a
  different model family after Astra fails. Trigger on concrete evidence:
  unresolved high-consequence design, conflicting evidence after focused
  investigation, or a failed check after one focused repair. The director runs
  `omp-quota` first. `@slow` is Astra xhigh. Escalation is scoped child
  delegation, not a parent-model switch. There is no compulsory classifier or
  routine review.
- Fable shares the Anthropic weekly pool with the Opus director. It can use at
  most half of that pool and costs about 2x Opus on the real token mix, so it is not extra
  capacity. For multi-hour frontier work, `cycleOrder` (default → fable → task)
  lets the user make Fable the director; delegated workers still run on nous or
  Codex. Leave `providers.anthropic.serverSideFallback` off because it would
  silently move Fable to Opus 4.8.
- Keep `task.enableEffort: true` for per-task choices without an extra classifier.
  Omit effort to retain configured medium; `lo` is for routine cloud work.
  Coarse `med` selects high on every cloud model. Keep local implementation
  medium; lower effort is not automatically faster. Recheck mappings against
  native discovery after catalog changes.
- Native `llama.cpp` serves the promoted Qwen3.8-27B-UD-Q4_K_XL worker
  (131,072 context / 8,192 output, medium reasoning). Keep
  `retry.modelFallback: false` so local work never silently moves to cloud
  inference. Use task defaults (`eager: default`, recursion depth 1,
  40-request soft budget, 10-minute runtime cap) and keep prewalk and
  background advisors off.
- Native nous handles bounded implementations with explicit contracts, mechanical
  transforms and extraction under the `local-workers` acceptance protocol.
  The `luna` agent is the explicit cloud worker; uncertain design stays with
  Opus or Astra.
  Smaller llama.cpp models remain explicit choices. Keep the OpenCode
  `nous-worker` Codex/T3 path available with fresh briefs and its full privacy
  bounds. Bonsai is retired from the active catalog and launcher; historical
  records and host weights remain untouched. All inference stays on nous or
  cloud; do not add Mac background inference or model downloads.
- Keep local child agents background-capable for native steering. At natural
  model/tool boundaries, the director may send one failed-check repair, then
  cancel/escalate a remaining failure or budget overrun; ordinary clarification
  and requirement steering is not artificially capped.
  Avoid transcript polling, custom watchdogs and advisor loops.
  For a bounded local job with no independent parent work, prefer the native
  eval spawn/wait/check path in `local-workers`, with a finite handle wait.
  Keep `blocking: false`; an eval cell timeout does not bound agent waiting.
- Treat OMP model discovery as authoritative before changing shared model IDs.
  Weigh any new model with `/skill:model-eval` (price, token mix, benchmarks,
  quota) before it takes a lane.
- Keep cloud model IDs centralized: `config.yml` roles/enabledModels, plus the
  Anthropic 272K `contextWindow` overrides in `models.yml` (1M only through
  `/extended-context on`). Agents, RULES and skills name model families, not
  generations. For a generation upgrade: run `omp models`, change those IDs,
  then run `omp-baseline validate`. It checks role families and efforts, that
  every role model is discovered, and the Anthropic budget. Then confirm the
  exact `provider`/`model` in a fresh `omp -p --mode json` response; a fuzzy
  match or successful exit alone does not prove the new model.
- Keep `private_models.yml` focused on catalog overrides plus necessary tested
  custom providers; do not remove those providers under an override-only rule.
  Retain the custom `ghostty` theme.
- User agents live in `home/private_dot_omp/private_agent/agents/`. They use
  `@smol` / `@task` aliases where possible, with local agents explicitly
  pinned to their discovered `llama.cpp` model. Keep model-specific thinking
  settings compatible with the selected provider.

## Workflow

1. Inspect Git state, the mise pin, `omp --version`, and source/live paths.
2. Review release and provider compatibility, then edit the canonical checkout.
3. Apply targeted files; run `mise install` and `mise reshim` when the pin moves.
4. Validate parsed config, native Codex provider/model discovery, local-provider
   discovery, Python setup, and native skill discovery in a new OMP session.
5. Run `omp-baseline validate --strict`. Commit and publish only when the user
   asks. An uncommitted pin is local only. The native guard defers dirty source
   files and never publishes or stashes them; scheduled apply leaves those files
   untouched. After publish, other hosts run `omp-baseline pull`.

The hourly OMP guard checks the focused baseline without overwriting source.
It also compares the published pin to GitHub latest and writes
`~/.local/state/decent-angl/omp-upstream` when a newer tag exists. That marker
is a reminder, not drift. Investigate
`~/.local/state/decent-angl/omp-baseline-drift` before declaring convergence.
The whole-tree guard owns Git reconciliation.

## Upgrade

Do not run `omp update`. That mutates the live binary off the shared pin.
The three pin sites must move together:

- `home/dot_config/decent-angl/omp-baseline-manifest.tsv` (`# omp-version`)
- `home/dot_config/mise/config.toml`
- `home/run_onchange_after_04-setup-omp.sh.tmpl`

Preconditions: those three files are Git-clean. Other dirty work in
`~/src/boilerplate` is fine and must be preserved. `upgrade` refuses dirty pin
files. Auth, `agent.db`, `.env`, and sessions stay machine-local.

```sh
omp-baseline check-upstream
omp-baseline upgrade --dry-run
omp-baseline upgrade            # or: omp-baseline upgrade 18.3.0
omp --version                   # new shells; the running session stays old
omp-baseline validate --strict  # commit gate, not a pin-install rollback
```

`upgrade` rewrites the pin sites, applies the mise file and manifest, `mise
install`s that exact GitHub release, reshims, writes
`~/.omp/agent/last-changelog-version`, refreshes the hourly guard, and runs
OMP config/discovery checks. It does not commit, reconcile, or fail closed on
an unrelated skill audit (opnsense, Omarchy, …). A failed OMP install or
`check_omp_config` restores the previous pin.

After a green pin install, review the three-file diff and any config changes
required by the release notes. Commit and publish only when requested. Scheduled
apply defers dirty source files without stashing them; it skips run_* hooks. On
every other host: `omp-baseline pull` (reconcile + `mise install` missing pins).
`omp-baseline fleet` checks t14, macbook, and macmini.

Rollback the pin with `omp-baseline upgrade <previous>` (same clean-pin-file
rule). After every pin move, treat live `omp models` as authoritative before
keeping shared model IDs. OMP 18.3.1 is the reviewed release. 18.3.0 deprecated
the `hub` tool: use `wait`, `read proc://`, `write proc://<id>/kill` and
`write agent://<id>`; RULES and skills use those forms.
Recheck callers before changing provider compatibility. Foreign `~/.cursor`,
`~/.codex`, `~/.claude`, and `~/.gemini` configs are opt-in. Keep native Pi
skills on. Never copy OAuth tokens between machines.
