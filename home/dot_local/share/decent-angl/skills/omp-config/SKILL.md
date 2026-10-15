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

- Pin OMP to the exact reviewed mise release (currently 18.10.4); do not combine
  the shared pin with `omp update`. Use `omp-baseline upgrade` to move the three
  pin sites together.
- Prefer native OMP config and features. Keep native skill discovery enabled.
- Use independent native OAuth logins per machine (Codex, Anthropic); never
  copy refresh credentials. Account count and quota state are machine-local.
  A host without an Anthropic login cannot run the shared Opus default: run
  `omp auth-broker login anthropic` there before `omp-baseline pull`. The
  Codex pool is session-sticky and quota-aware; use `/session pin` when needed.
- Default routing is Claude Opus high as director (raised from medium on
  2026-10-08: weekly Anthropic use was ~19% on medium; high costs ~1.7–2.8x
  per prompt through more tool calls, not longer thinking). Drop back to
  medium for the week if `omp-quota` shows <40% Anthropic 7d left before
  day 5 of the window. The director owns
  requirements, integration and acceptance; trivial work stays direct. The
  `task` role (so the `task` agent) runs on Codex Luna medium, like `vision`,
  because local queuing stalled parallel children. The `commit`, `smol` and
  `tiny` roles (so `scout`, `sonic`) and the explicitly pinned `nous` agent run
  on nous Qwen to save Codex quota.
  Use fresh compact briefs, not the full parent transcript or pre-solved implementations.
- Escalation lanes: GPT-6.1 Sol (`architect` read-only at xhigh, `sol`
  implementation at high; both `@plan`, with no reserve model) is the default.
  It trails GPT-6 Astra by 1–5 points on coding/agentic benchmarks at about 1/8
  the blended token price (model-eval benchmarks, 2026-09-29) and draws from the
  Codex pool, not the director's. Astra is a manual reserve; it stays in
  `enabledModels`. Fable medium (`fable`, `@fable`) is only a second opinion
  from a different model family after Sol fails. `@slow` is Opus high.
  Escalation is scoped child delegation, not a parent-model switch. When to
  escalate, consult or audit is the RULES.md policy; this section covers only
  the mechanics.
- The "Sol xhigh council" (the Sol high council until 2026-10-14) is one
  `architect` at xhigh, and the release `auditor` (read-only, strict verdict
  schema) is the same model and effort: both use `@plan:xhigh`, because the
  `plan` role's `:high` suffix beats a frontmatter `thinkingLevel`. Run release
  audits through `/review` or `omp-audit NAME PACKET CANDIDATE`, never a plain
  `task` call: an ordinary child inherits MCP servers and the xd:// write
  transport. `omp-audit` dispatches from a hardened project (no MCP, no
  device write, structured results) that serves a read-only copy of the
  deployed `~/.omp/agent/agents/AGENT.md` as its only project agent, which
  outranks every other same-name definition. It sends the caller schema in
  strict mode, then accepts the verdict only if the child served that project
  copy on `openai-codex/gpt-6.1-sol` at xhigh without fallback, with exactly
  the five read-only tools, a system prompt holding the hashed definition's
  body, and the packet's candidate id, the copy and the read-only packet copy
  it read are unchanged, and a PASS lists no blocker/major finding or missing
  evidence. It refuses to run with `PI_CODING_AGENT_DIR`, `OMP_PROFILE`,
  `PI_PROFILE` or `PI_CONFIG_DIR` set. Auth fallback can still substitute a
  model, so that serving check stays even with no reserve listed.
  `--agent-file`/`--model` runs are model-admission controls
  (`release: false`; see `model-eval`), never release verdicts.
  Results stay under `~/.local/state/omp-audit/runs/`. Codex quota per xhigh
  decision is unmeasured; the price ratios above are per token.
- Fable shares the Anthropic weekly pool with the Opus director. It can use at
  most half of that pool and costs about 2x Opus on the real token mix, so it is
  not extra capacity. `cycleOrder` (default → fable → task) is kept for manual
  cycling. Leave `providers.anthropic.serverSideFallback` off because it would
  silently move Fable to Opus 4.8.
- Keep `task.enableEffort: true` for per-task choices without an extra classifier.
  Omit effort to retain the agent default (medium; high for `sol`, xhigh for
  `architect` and `auditor`). Always omit it for those two: a task
  `effort: med` was observed to drop `architect` to high. `lo` is for routine cloud work.
  Coarse `med` selects high on every cloud model. Keep local implementation
  medium; lower effort is not automatically faster. Recheck mappings against
  native discovery after catalog changes.
- Native `llama.cpp` serves the promoted worker, the Heretic-abliterated
  Qwen3.8-27B-RVN-Heretic-Q4_K_M since 2026-10-09 (stock UD-Q4_K_XL is the
  rollback preset; 163,840 context / 8,192 output, text and image input, medium reasoning). Keep
  `retry.modelFallback: false` so local work never silently moves to cloud
  inference. Use task defaults (`eager: default`, recursion depth 1,
  40-request soft budget, 10-minute runtime cap) and keep prewalk and
  background advisors off.
- Native nous handles bounded implementations with explicit contracts, mechanical
  transforms and extraction under the `local-workers` acceptance protocol.
  The `task` agent is the cloud worker; uncertain design stays with Opus or Sol.
  Smaller llama.cpp models remain explicit choices. Keep the OpenCode
  `nous-worker` Codex/T3 path available with fresh briefs and its full privacy
  bounds. Bonsai is retired from the active catalog and launcher; historical
  records and host weights remain untouched. All inference stays on nous or
  cloud; do not add Mac background inference or model downloads.
- `omp-local` (`omp --profile local`, source
  `home/private_dot_omp/private_profiles/local/`) is Tucker's fully local lane:
  every role runs on the promoted Heretic Qwen, every cloud provider is
  disabled, and it has its own short `RULES.md`; skills, extensions and themes
  are symlinked from the default profile. Keep its `models.yml` llama.cpp block
  in step with the default one. Cloud sessions do not route work to it.
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
  Anthropic 272K `contextWindow` overrides in `models.yml` (1M only through a
  per-session `/extended-context on`). Keep 1M off by default: replaying 19,774
  Opus 5.5 turns (2026-09-29) showed cache reads were 52% of API-equivalent
  spend, and compacting near 860K instead of 232K would multiply cache-read
  tokens 3.3x (about 2.2x total usage) while saving only about $0.35 per
  avoided compaction. Use 1M only for a session that needs one huge working
  set. Agents, RULES and skills name model families, not
  generations. For a generation upgrade: run `omp models`, change those IDs,
  then run `omp-baseline validate`. It checks role families and efforts, that
  every role model is discovered, and the Anthropic budget. Then confirm the
  exact `provider`/`model` in a fresh `omp -p --mode json` response; a fuzzy
  match or successful exit alone does not prove the new model.
- Keep `private_models.yml` focused on catalog overrides plus necessary tested
  custom providers; do not remove those providers under an override-only rule.
  Retain the custom `ghostty` theme.
- User agents live in `home/private_dot_omp/private_agent/private_agents/`. They use
  `@smol` / `@task` aliases where possible, with local agents explicitly
  pinned to their discovered `llama.cpp` model. Keep model-specific thinking
  settings compatible with the selected provider. A selector suffix outranks
  `thinkingLevel`, and a bare `@default` inherits the parent's suffix: write the
  effort into the selector (`@default:medium`). `omp-baseline validate` runs
  `omp-agent-policy`, which resolves every agent's model, effort and tools
  against the pinned OMP version and native `omp models --json` and
  `omp config list --json` evidence (`--root .` alone leaves contract efforts
  and the settings merge UNVERIFIED). It certifies static policy for a fresh
  depth-1 dispatch; the serving model (auth fallback) and MCP proxy names are
  runtime-deferred to `omp-agent-smoke` (paid), which checks them with real
  spawns and proves each proxy's server from the prompt's route or inventory
  label. It fails closed on hooks, custom tools and extensions not in its
  `REVIEWED_EXTENSIONS` digests, on custom command modules (`commands/*/index.*`
  in every config root) not in `REVIEWED_COMMANDS`, on a default profile
  without the `/review` override `commands/review/index.ts`, on unmirrored `OMP_*`/`PI_*` variables,
  launch-dir dotenv keys, settings and MCP sources, when a contract agent
  arms prewalk or retry model fallback or takes its model only from the
  parent, and when the default profile leaves `task.structured` off. Validate
  runs its native probes in a scratch HOME under a shell jail (bwrap on Linux,
  sandbox-exec on macOS), so `!command` config values and stored keys never
  execute; it fails when the jail is unavailable or any settings layer or
  models file holds a `!command` value. A new OMP version needs the checker
  mirror re-verified first.

## Workflow

1. Inspect Git state, the mise pin, `omp --version`, and source/live paths.
2. Review release and provider compatibility, then edit the canonical checkout.
3. Apply targeted files; run `mise install` and `mise reshim` when the pin moves.
4. Validate parsed config, native Codex provider/model discovery, local-provider
   discovery, Python setup, and native skill discovery in a new OMP session.
5. Run `omp-baseline validate --strict`. Validate only observes; `omp-baseline
   repair` (or apply) fixes runtime permissions. Commit and publish only when the user
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

Roll back by reverting the upgrade commit (the pins and the version-pinned
`omp-agent-policy`/`omp-agent-smoke` mirror move together), then `chezmoi
apply` every target that commit changed outside the manifest (such as
`~/.local/bin/omp-baseline` and canonical skills under
`~/.local/share/decent-angl/skills`), then `omp-baseline apply`: it applies
only manifest paths and syncs skills from the live canonical copies. After
every pin move, treat live `omp models` as authoritative before keeping shared
model IDs. OMP 18.10.4 is the reviewed
release. Since 18.10.2 `task.structured` defaults off, which drops `yield` and
every output schema; both profiles set it true. 18.10.4 removed Codex Code
Mode, 18.8.2 per-call task model overrides. 18.3.0 deprecated
the `hub` tool: use `wait`, `read proc://`, `write proc://<id>/kill` and
`write agent://<id>`; RULES and skills use those forms.
Recheck callers before changing provider compatibility. Foreign `~/.cursor`,
`~/.codex`, `~/.claude`, and `~/.gemini` configs are opt-in. Keep native Pi
skills on. Never copy OAuth tokens between machines.
