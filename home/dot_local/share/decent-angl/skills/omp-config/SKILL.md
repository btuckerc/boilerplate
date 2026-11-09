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

- Pin OMP to the exact reviewed mise release (currently 18.16.0); do not combine
  the shared pin with `omp update`. Use `omp-baseline upgrade` to move the two
  pin sites together.
- Prefer native OMP config and features. Keep native skill discovery enabled.
- OMP's Codex OAuth logins live on the one auth broker on nous
  (`omp-auth-broker.service`, tailnet port 8747). Other hosts
  are clients through host-local `OMP_AUTH_BROKER_URL` in
  `~/.omp/agent/.env` and `~/.omp/auth-broker.token`, both copied from nous and
  never committed. Never log in locally: two holders of one refresh token
  rotate it away from each other (the Mac lost its logins daily that way), so
  `omp-baseline validate` fails on any local OAuth row. Add accounts on the broker (the
  `platform-ops` nous reference); move a stray local login with `omp
  auth-broker migrate --from-local --include-oauth`, then delete the local
  `oauth` rows. The Codex pool is session-sticky and quota-aware; use
  `/session pin` when needed.
- Legacy OMP defaults and `@slow` use Codex Sol high. The `task` role
  (so the `task` agent) runs on Codex Luna medium, like `vision`.
  The `commit`, `smol` and `tiny` roles (so `scout`, `sonic`) and the
  explicitly pinned `nous` agent run on nous Qwen. The browser agent is
  pinned to Sol high through `@plan:high`.
  Use fresh compact briefs, not the full parent transcript or pre-solved implementations.
- Escalation lanes: GPT-6.1 Sol (`architect` read-only at xhigh, `sol`
  implementation at high; both `@plan`, with no reserve model) is the default.
  Astra (role and read-only agent `astra`) remains a manual reserve in
  `enabledModels`. Seat lifecycle: the `council` skill.
  Escalation is scoped child delegation, not a parent-model switch. When to
  escalate, consult or audit is the RULES.md policy; this section covers only
  the mechanics.
- The director's consult is one `architect` at xhigh (the "Sol xhigh council"
  in records from 2026-10-14 on; "Sol high council" now triggers a one-seat
  `council`). The release `auditor` (read-only, strict
  verdict schema) is the same model and effort: both use `@plan:xhigh`, because the
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
  decision is unmeasured.
- Cloud inference is Codex-only; `cycleOrder` is default → task.
  Do not restore retired cloud providers or their removed agents. The optional
  `agent-triage` decision helper (formerly `omp-triage`; labels are agent-run
  lanes) is separate from OMP model routing and keeps its OpenRouter key
  plumbing (`omp-env`).
- Keep `task.enableEffort: true` for per-task choices without an extra classifier.
  Omit effort to retain the agent default (medium; high for `sol` and `browser`, xhigh for
  `architect` and `auditor`). Always omit it for those two: a task
  `effort: med` was observed to drop `architect` to high. `lo` is for routine cloud work.
  Coarse `med` selects high on every cloud model. Keep local implementation
  medium; lower effort is not automatically faster. Recheck mappings against
  native discovery after catalog changes.
- The nous production provider is native `vllm`, serving only
  `Qwen3.8-27B-Swift-Heretic-MXFP4` (262,144 context / 8,192 output, text and
  image input, medium reasoning). Keep `retry.modelFallback: false` so local
  work never silently moves to cloud inference. Use task defaults (`eager:
  default`, recursion depth 1, 100-request soft budget, 30-minute runtime cap)
  and keep prewalk and background advisors off.
- Native nous handles bounded implementations with explicit contracts,
  mechanical transforms and extraction under the `local-workers` acceptance
  protocol. vLLM batches up to 8 sequences; the shared 399,968-token VRAM KV
  pool replaces the old serialized slot/host prompt cache, so bound task
  concurrency at 4. The `task` agent is the cloud worker; uncertain design
  stays with Sol. Keep the OpenCode `nous-worker` path available with
  fresh briefs and its privacy bounds. All inference stays on nous or cloud;
  do not add Mac background inference or model downloads.
- `omp-local` (`omp --profile local`, source
  `home/private_dot_omp/private_profiles/local/`) is Tucker's fully local lane:
  every role runs on the promoted Swift Heretic Qwen, every cloud provider is
  disabled, and it has its own short `RULES.md`; skills, extensions and themes
  are symlinked from the default profile. Keep its `models.yml` vLLM block in
  step with the default one. Cloud sessions do not route work to it.
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
- Keep cloud model IDs centralized in `config.yml` roles/enabledModels.
  For a generation upgrade: run `omp models`, change those IDs, then run
  `omp-baseline validate`. It checks role families, efforts, and discovery.
  Confirm the exact `provider`/`model` in a fresh `omp -p --mode json`
  response; a fuzzy match or successful exit does not prove the model.
  A Sol generation also moves its deliberate exact pins together: the
  `architect`, `auditor`, `sol` and `browser` contracts in `omp-agent-policy`,
  `RELEASE_MODEL` in `omp-audit`, and the audit lane text above, after
  model-eval's admission controls pass.
- Keep `private_models.yml` focused on catalog overrides plus necessary tested
  custom providers; do not remove those providers under an override-only rule.
  Retain the custom `ghostty` theme.
- User agents live in `home/private_dot_omp/private_agent/private_agents/`. They use
  `@smol` / `@task` aliases where possible, with local agents explicitly
  pinned to their discovered `vllm` model. Keep model-specific thinking
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
2. Review release and provider compatibility, then edit in a worktree of the
   canonical checkout (`decent-angl-config`); preview with
   `chezmoi -S <worktree> diff`.
3. Check the candidate: `omp-baseline check-source <worktree>` runs the agent
   policy and native probes with the candidate's own pinned omp.
4. Commit only when the user asks. Land with `git merge --ff-only`, then
   `decent-angl-sync reconcile` publishes, applies and installs a moved pin;
   other hosts converge through their own guard.
5. Validate parsed config, native Codex provider/model discovery, local-provider
   discovery, Python setup, and native skill discovery in a new OMP session, then
   run `omp-baseline validate --strict`. Validate only observes; `omp-baseline
   repair` (or apply) fixes runtime permissions. The native guard defers dirty
   source files and never publishes or stashes them.

The hourly OMP guard checks the focused baseline without overwriting source.
It also compares the published pin to GitHub latest and writes
`~/.local/state/decent-angl/omp-upstream` when a newer tag exists. That marker
is a reminder, not drift. Investigate
`~/.local/state/decent-angl/omp-baseline-drift` before declaring convergence.
The whole-tree guard owns Git reconciliation.

## Upgrade

Do not run `omp update`. That mutates the live binary off the shared pin.
The two pin sites must move together:

- `home/dot_config/decent-angl/omp-baseline-manifest.tsv` (`# omp-version`)
- `home/dot_config/mise/config.toml`

Preconditions: those two files are Git-clean. `upgrade` edits
`~/src/boilerplate` itself, not a worktree, because it applies the pins live from
the chezmoi source: like `decent-angl-sync capture`, it is an exception to the worktree rule, so commit its
result promptly. Other dirty work there is preserved. `upgrade` refuses dirty
pin files. Auth, `agent.db`, `.env`, and sessions stay machine-local.

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

After a green pin install, review the two-file diff and any config changes
required by the release notes. Commit and publish only when requested, using
`decent-angl-sync reconcile`. Scheduled apply defers dirty source files without
stashing them; OMP and companion mise pins install without run_* hooks. Other
hosts converge through their own 15-minute guard; no per-host step is needed.
`omp-baseline fleet` checks t14, macbook, and macmini.

Roll back by reverting the upgrade commit in a worktree (the pins and the
version-pinned `omp-agent-policy`/`omp-agent-smoke` mirror move together),
previewing with `chezmoi -S <worktree> diff`, landing the revert with
`git merge --ff-only`, and running `decent-angl-sync
reconcile`: it applies every changed target, then runs `omp-baseline apply`,
which installs the reverted pin and syncs skills. After
every pin move, treat live `omp models` as authoritative before keeping shared
model IDs. OMP 18.16.0 is the reviewed release. Since 18.10.2 `task.structured`
defaults off, which drops `yield` and output schemas unless the agent declares
`structured: true`; both profiles set it true. 18.11-18.12.1 adds fail-closed
agent tools, per-agent structured results, safer discovery roots, automatic
prewalk, and the bundled `seance` agent. 18.16.0 gives the bundled `scout`
`ast_grep`, brings back per-call task models as the opt-in `task.perCallModel`
(keep it off: `omp-agent-policy` fails closed otherwise) and lets an unserved
thinking level alias through the catalog's `effortMap`, which the checker
cannot see and so fails closed. 18.10.4 removed Codex Code Mode,
18.8.2 per-call task model overrides. 18.3.0 deprecated
the `hub` tool: use `wait`, `read proc://`, `write proc://<id>/kill` and
`write agent://<id>`; RULES and skills use those forms.
Recheck callers before changing provider compatibility. Foreign `~/.cursor`,
`~/.codex`, `~/.claude`, and `~/.gemini` configs are opt-in. Keep native Pi
skills on. Never copy OAuth tokens between machines.
