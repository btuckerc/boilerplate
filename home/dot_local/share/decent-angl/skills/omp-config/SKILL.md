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

- Pin OMP to an exact reviewed mise release; do not combine the shared pin with
  `omp update`. Use `omp-baseline upgrade` to move the three pin sites together.
- Prefer native OMP config and features. Keep native skill discovery enabled.
- Authenticate SuperGrok locally with `omp auth-broker login xai-oauth`.
- Authenticate Google AI Pro Gemini Flash locally with
  `omp auth-broker login google-antigravity`. Do not use `google-gemini-cli`
  or set `GOOGLE_CLOUD_PROJECT` for that subscription.
- OpenRouter GLM-5.3-Flash is tiny/commit and the Antigravity 429 fallback.
  Materialize its key with `omp-openrouter-env`; keep the value out of config,
  Git, commands, and output.
- Role routing: SuperGrok serves default/slow/plan; Antigravity Gemini 3.8
  Flash serves vision/smol/task; OpenRouter GLM-5.3-Flash materializes
  tiny/commit and acts as the Antigravity 429 fallback.
- Treat OMP model discovery as authoritative before changing shared model IDs.
- Keep `models.yml` override-only and retain the custom `ghostty` theme.
- User agents live in `home/private_dot_omp/private_agent/agents/`. They use
  `@smol` / `@task`, never a vendor model id. `thinkingLevel` must exist on
  both Grok and Flash: `low` or `high`. Do not pin `medium`.

## Workflow

1. Inspect Git state, the mise pin, `omp --version`, and source/live paths.
2. Review release and provider compatibility, then edit the canonical checkout.
3. Apply targeted files; run `mise install` and `mise reshim` when the pin moves.
4. Validate parsed config, auth-broker state, model discovery and thinking
   efforts, Python setup, tiny models, and native skill discovery in a new OMP
   session.
5. Run `omp-baseline validate --strict`, commit, then
   `decent-angl-sync reconcile --with-scripts` when script effects are required.
   An uncommitted pin is local only. Scheduled reconcile stashes dirty trees
   and applies published master, so the fleet stays on the old pin until you
   commit. Scheduled apply also skips scripts; after publish, other hosts run
   `omp-baseline pull`.

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
omp-baseline upgrade            # or: omp-baseline upgrade 18.1.5
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
required by the release notes. Then commit, then
`decent-angl-sync reconcile --with-scripts` so the fleet follows. Scheduled
apply skips scripts. On every other host: `omp-baseline pull` (reconcile +
`mise install` missing pins). `omp-baseline fleet` checks t14, macbook, and
macmini.

Rollback the pin with `omp-baseline upgrade <previous>` (same clean-pin-file
rule). After every pin move, treat live `omp models` as authoritative before
keeping shared model IDs. 18.1.5 collapsed Antigravity Gemini 3.8 to
`google-antigravity/gemini-3.8-flash` plus `:high`/`:low`; the old
`-tiered`/`-high`/`-low` SKUs are gone. 18.x also removed the bundled
`designer` role; foreign `~/.cursor` / `~/.codex` / `~/.claude` / `~/.gemini`
user configs are opt-in. Keep native Pi skills on. Never copy OAuth tokens
between machines.
