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

- Edit the working repo first, then sync the same files to the applied source.
- Keep `agent.db`, OAuth tokens, sessions, caches, logs, usage state, and installation identifiers machine-local.
- Pin `github:can1357/oh-my-pi` to an exact reviewed release. Do not combine a pinned baseline with `omp update`.
- Prefer native OMP features and config over compatibility extensions from Pi, Codex, Claude, or OpenCode.
- Authenticate SuperGrok per machine with `omp auth-broker login xai-oauth`; never export or print the resulting token.
- Treat OMP model discovery as authoritative for newly released xAI model IDs before changing shared model roles.

## Workflow

1. Inspect Git status, the active mise pin, `omp --version`, and the live/source config paths.
2. Review the target OMP release and provider/model compatibility changes.
3. Edit `~/src/boilerplate/home/...` and preserve unrelated worktree changes.
4. Sync only changed source files into `~/.local/share/chezmoi/home/...`.
5. Run targeted `mise x -- chezmoi apply` commands; avoid whole-tree applies when unnecessary.
6. Run `mise install`, `mise reshim`, and verify `omp --version`.
7. Validate config parsing, `omp auth-broker list --json`, `omp models xai-oauth --json`, and `omp setup python --check --json`.
8. Confirm live files match the rendered source and credentials remain local.

Use Tailscale SSH targets `omarchy`, `macbook`, and `admin@macmini` when inspecting or rolling out another machine.
