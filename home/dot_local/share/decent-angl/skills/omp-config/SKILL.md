---
name: omp-config
description: Maintain the shared Oh My Pi baseline in chezmoi. Use for OMP upgrades, omp-baseline upgrade, provider or model defaults, auth-broker configuration, skills, prompts, or cross-platform rollout. Never run omp update.
---

# OMP config

## Boundary

- Source: `~/src/boilerplate/home/`
- Live config: `~/.omp/agent/`
- Version pin: `home/dot_config/mise/config.toml`
- Runtime databases, tokens, sessions, caches, logs, usage state, installation
  IDs, and tiny-model weights stay machine-local.

## Invariants

- Pin OMP to the exact reviewed mise release (currently 18.2.6); do not combine
  the shared pin with `omp update`. Use `omp-baseline upgrade` to move the three
  pin sites together.
- Prefer native OMP config and features. Keep native skill discovery enabled.
- Use independent native Codex OAuth logins; never copy refresh credentials
  from Codex homes. Account count and quota state are machine-local. The native
  pool is session-sticky and quota-aware; use `/session pin` when needed.
- Default routing is Luna medium. Astra is reserved for `@plan:medium` and
  `@slow:xhigh` work. Routine edits and tests do not require an obligatory
  planning or review stage. Consult the native `architect` agent (read-only
  Astra plan consultation) only for ambiguous architecture, conflicting
  evidence, or stalled diagnosis.
- Native `llama.cpp` and `bonsai` providers are available for bounded local
  workers. Keep `retry.modelFallback: false` so local work never silently moves
  to cloud inference. Use task defaults (`eager: default`, recursion depth 1,
  40-request soft budget, 10-minute runtime cap) and keep prewalk and
  background advisors off.
- Native nous children are limited to mechanical small transforms, extraction,
  and predetermined edits. Use Luna for ordinary code and tests. Ornith and
  Gemma failed novel algorithmic edge cases; do not auto-route algorithmic work
  to them. Keep the OpenCode `nous-worker` Codex/T3 path available with fresh
  briefs and its full privacy bounds. All inference stays on nous or cloud; do
  not add Mac background inference or model downloads.
- Treat OMP model discovery as authoritative before changing shared model IDs.
- Keep `private_models.yml` focused on catalog overrides plus necessary tested
  custom providers; do not remove those providers under an override-only rule.
  Retain the custom `ghostty` theme.
- User agents live in `home/private_dot_omp/private_agent/agents/`. They use
  `@smol` / `@task` aliases where possible, with local agents explicitly
  pinned to their discovered `llama.cpp` or `bonsai` model. Keep model-specific
  thinking settings compatible with the selected provider.

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
omp-baseline upgrade            # or: omp-baseline upgrade 18.2.6
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
keeping shared model IDs. OMP 18.2.6 is the reviewed release; read its release
notes before changing provider compatibility. Foreign `~/.cursor`, `~/.codex`,
`~/.claude`, and `~/.gemini` configs are opt-in. Keep native Pi skills on.
Never copy OAuth tokens between machines.
