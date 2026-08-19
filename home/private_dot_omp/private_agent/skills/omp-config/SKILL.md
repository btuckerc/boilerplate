---
name: omp-config
description: Update the shared Oh My Pi (OMP) baseline managed by chezmoi, including the pinned mise release, config.yml, native instructions, rules, skills, prompts, local authentication boundary, and cross-platform rollout. Use for OMP upgrades, provider/model defaults, auth-broker configuration, or migration from another coding harness.
---

# OMP Config

## Canonical Layout

- Working repo: `~/src/boilerplate/home/private_dot_omp/`
- Applied source: `~/.local/share/chezmoi/home/private_dot_omp/`
- Live native config: `~/.omp/agent/`
- Version pin: `~/src/boilerplate/home/dot_config/mise/config.toml`

## Rules

- Edit the working repo first. The applied-source path is a symlink into the same checkout; never maintain an independent copy.
- Keep `agent.db`, OAuth tokens, sessions, caches, logs, usage state, and installation identifiers machine-local.
- Pin `github:can1357/oh-my-pi` to an exact reviewed release. Do not combine a pinned baseline with `omp update`.
- Prefer native OMP features and config over compatibility extensions from Pi, Codex, Claude, or OpenCode. Native skills live in `~/.omp/agent/skills/<name>/SKILL.md` and are gated by `skills.enablePiUser` / `skills.enablePiProject` (legacy names). Do not set those false. `disabledProviders: agents` only blocks `.agent[s]/skills`, not native OMP skills.
- Authenticate SuperGrok per machine with `omp auth-broker login xai-oauth`; never export or print the resulting token.
- OpenRouter is overflow only. Default roles stay `xai-oauth/grok-4.6`. Fallback is `openrouter/x-ai/grok-4.6` (not `:nitro`). Keep `providers.openrouterVariant: default`. `openrouter/x-ai/grok-4.6:nitro` is a manual model-picker option only. After unlocking Bitwarden, run `omp-openrouter-env` once per machine to write `OPENROUTER_API_KEY` into `~/.omp/agent/.env` (mode 0600) from vault item `omp-openrouter`. Never print the key, never put it in `models.yml`/`config.yml`/Git. Re-run after rotating the vault item.
- Treat OMP model discovery as authoritative for newly released xAI model IDs before changing shared model roles.
- Keep `models.yml` as an override-only catalog file. Use it to restore missing xAI metadata, not to invent extra providers. 17.3.4 still needs the Grok 4.6 thinking override.
- Keep the custom `ghostty` theme in source. Tiny-model weights stay machine-local under `~/.omp/agent/cache/`.

## Workflow

1. Inspect Git status, the active mise pin, `omp --version`, and the live/source config paths.
2. Review the target OMP release and provider/model compatibility changes.
3. Edit `~/src/boilerplate/home/...` and preserve unrelated worktree changes.
4. Confirm `~/.local/share/chezmoi` resolves to `~/src/boilerplate`; run `decent-angl-sync adopt-source` if it does not.
5. Run targeted `mise x -- chezmoi apply` commands; avoid whole-tree applies when unnecessary.
6. Run `mise install`, `mise reshim`, and verify `omp --version`.
7. Validate config parsing, `omp auth-broker list --json`, `omp models xai-oauth --json` (confirm `grok-4.6` thinking efforts), `omp setup python --check --json`, and `omp tiny-models list --json`. Confirm `skills.enablePiUser` is true. `omp read skill://<name>` is not a valid check: that CLI path does not load session skills. Verify in a new session that the system prompt `<skills>` list includes `platform-ops`, `omp-config`, and `opnsense`.
8. Confirm live files match the rendered source and credentials remain local.

## Fleet Convergence

- Published Git `master` is canonical. Any fleet machine may author reviewed OMP commits; no mutable machine filesystem is permanently privileged.
- Run `omp-baseline validate --strict` before committing. Use `decent-angl-sync reconcile --with-scripts` to publish or consume the complete baseline without creating subset drift.
- `omp-baseline apply` installs the exact pin, applies only manifest-owned files, validates the runtime boundary, and installs the hourly guard.
- The focused OMP guard validates every machine without overwriting source. The whole-tree `decent-angl-sync` guard owns cross-machine Git reconciliation.
- A failed guard persists `~/.local/state/decent-angl/omp-baseline-drift`; inspect it before treating a machine as converged.

Use Tailscale SSH targets `omarchy`, `macbook`, and `admin@macmini` when inspecting or rolling out another machine.
