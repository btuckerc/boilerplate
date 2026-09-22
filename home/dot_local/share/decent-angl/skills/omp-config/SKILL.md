---
name: omp-config
description: Maintain the shared Oh My Pi baseline in chezmoi. Use only when the user explicitly asks for an OMP upgrade, omp-baseline change, provider or model default, auth-broker login, or OMP config.yml/models.yml rollout. Never run omp update. Not for application work or merely using a skill.
---

# OMP config

## Boundary

- Source: `~/src/boilerplate/home/`
- Live config: `~/.omp/agent/`
- Version pin: `home/dot_config/mise/config.toml`
- Runtime databases, tokens, sessions, caches, logs, usage state, installation
  IDs, and tiny-model weights stay machine-local.

## Invariants

- Pin OMP to the exact reviewed mise release (currently 18.2.8); do not combine
  the shared pin with `omp update`. Use `omp-baseline upgrade` to move the three
  pin sites together.
- Prefer native OMP config and features. Keep native skill discovery enabled.
- Use independent native Codex OAuth logins; never copy refresh credentials
  from Codex homes. Account count and quota state are machine-local. The native
  pool is session-sticky and quota-aware; use `/session pin` when needed.
- Default routing is Astra medium as director. Prefer `nous` for bounded
  implementation with clear scope, contract and independent acceptance checks,
  as well as mechanical edits and extraction. Settle risky design decisions;
  do not write a full solution. Use a fresh compact brief with owned files,
  contract, invariants and acceptance command. Use Luna medium
  for unresolved design, novel algorithms, uncertain debugging, broad/tool-rich
  changes, large context or a failed focused local repair. Ordinary requirement
  clarification and steering remains available. Use
  `@slow:xhigh` for sustained frontier work. Routine edits do not require
  an obligatory classifier, swarm or duplicate planning stage. Consult the
  native `architect` agent only for an unresolved ambiguity the director cannot
  settle.
- Keep `task.enableEffort: true` for per-task choices without an extra classifier.
  Omit effort to retain configured medium; `lo` is for routine cloud work.
  Coarse `med` currently selects high on Astra/Luna. Keep local implementation
  medium; lower effort is not automatically faster. Recheck mappings against
  native discovery after catalog changes.
- Native `llama.cpp` serves the promoted Qwen3.8-27B-UD-Q5_K_M worker
  (65,536 context / 8,192 output, medium reasoning). Keep
  `retry.modelFallback: false` so local work never silently moves to cloud
  inference. Use task defaults (`eager: default`, recursion depth 1,
  40-request soft budget, 10-minute runtime cap) and keep prewalk and
  background advisors off.
- Native nous handles bounded implementations with explicit contracts, mechanical
  transforms and extraction under the `local-workers` acceptance protocol.
  Keep Luna as the generic `task` alias; Astra chooses the explicit local lane
  when eligible. Do not automatically route unresolved algorithmic work locally.
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
omp-baseline upgrade            # or: omp-baseline upgrade 18.2.8
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
keeping shared model IDs. OMP 18.2.8 is the reviewed release. Its 18.2.7
transition removed bash `env` and changed eval `judge()` to return awaited
answers directly (no `JudgmentHandle` or judgment handles in `wait()`).
Recheck callers before changing provider compatibility. Foreign `~/.cursor`, `~/.codex`,
`~/.claude`, and `~/.gemini` configs are opt-in. Keep native Pi skills on.
Never copy OAuth tokens between machines.
