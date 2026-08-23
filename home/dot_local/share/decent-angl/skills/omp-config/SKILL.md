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
- OpenRouter is overflow only. Materialize its key with `omp-openrouter-env`;
  keep the value out of config, Git, commands, and output.
- Treat OMP model discovery as authoritative before changing shared model IDs.
- Keep `models.yml` override-only and retain the custom `ghostty` theme.
- On Linux, OMP headless Chromium must launch through `~/.local/bin/omp-chromium`
  (`PUPPETEER_EXECUTABLE_PATH`). Do not point that variable at `/usr/bin/chromium`
  (Omarchy `--load-extension`) or the raw `/usr/lib/chromium/chromium` binary
  (OMP strips `--disable-extensions`; dirty profiles then abort in SafeBuiltins).
  The baseline manifest marks that wrapper `linux`; macOS must not install it.

## Workflow

1. Inspect Git state, the mise pin, `omp --version`, and source/live paths.
2. Review release and provider compatibility, then edit the canonical checkout.
3. Apply targeted files; run `mise install` and `mise reshim` when the pin moves.
4. Validate parsed config, auth-broker state, model discovery and thinking
   efforts, Python setup, tiny models, and native skill discovery in a new OMP
   session.
5. Run `omp-baseline validate --strict`, commit, then
   `decent-angl-sync reconcile --with-scripts` when script effects are required.
   Scheduled fleet apply skips scripts, so pin upgrades need `omp-baseline pull`
   on every other host after publish.

The hourly OMP guard checks the focused baseline without overwriting source.
It also compares the published pin to GitHub latest and writes
`~/.local/state/decent-angl/omp-upstream` when a newer tag exists. That marker
is a reminder, not drift. Investigate
`~/.local/state/decent-angl/omp-baseline-drift` before declaring convergence.
The whole-tree guard owns Git reconciliation.

## Upgrade

Do not run `omp update`. The three pin sites must move together:

- `home/dot_config/decent-angl/omp-baseline-manifest.tsv` (`# omp-version`)
- `home/dot_config/mise/config.toml`
- `home/run_onchange_after_04-setup-omp.sh.tmpl`

```sh
omp-baseline check-upstream
omp-baseline upgrade --dry-run
omp-baseline upgrade 17.4.2
omp-baseline validate --strict
```

`upgrade` rewrites the pin sites, installs that mise release, and validates.
It does not commit or reconcile. Review the pin diff, commit, then
`decent-angl-sync reconcile --with-scripts` so the fleet follows. On each
other machine run `omp-baseline pull`.
