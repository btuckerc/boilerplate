# Codex Baseline

This directory is the shared Codex baseline managed by chezmoi.

## Canonical Paths

- Working repo: `~/src/boilerplate/home/dot_codex/`
- Applied source: `~/.local/share/chezmoi/home/dot_codex/` (the same tree via symlink)
- Live config: `~/.codex/`

Edit the source tree, then apply targeted files with `chezmoi`.

## What Is Shared

- `config.toml`: portable Codex defaults
- `AGENTS.md`: short global working rules rendered by chezmoi for the current platform or known machine
- `skills/`: reusable Codex workflow knowledge rendered the same way

Current shared skills:

- `decent-angl-config`: reconcile and publish the complete cross-machine baseline
- `bitwarden-secrets`: provision and consume vault-backed machine-local secrets safely
- `codex-config`: maintain the shared Codex baseline itself
- `platform-ops`: handle Omarchy/Linux and macOS system settings, hardware preferences, and shared-vs-local config decisions

## Fast Paths

- Omarchy desktop and shell/bar tweaks: start with `platform-ops`; Quattro uses Hyprland Lua plus `~/.config/omarchy/shell.json`
- Omarchy roaming baseline: run `omarchy-roaming-sync preflight` before capture/apply and `omarchy-roaming-sync validate` afterward; both refuse an unsupported Omarchy generation
- Before committing or publishing the baseline, use `omarchy-roaming-sync validate --strict` so pending new source files fail validation
- `omarchy-roaming-sync sync --apply` captures only portable user overrides; package-owned bootstrap, shell state, monitor state, and generated theme state remain local
- The managed `post-update.d/10-decent-angl-compat` hook validates that contract after `omarchy update` and leaves a durable marker under `~/.local/state/decent-angl/` if a future release is incompatible

## What Is Not Shared

- `auth.json`
- session history, caches, sqlite files, logs
- machine-local trust entries in `~/.codex/config.toml`

## Install Standard

- OS packages: native package manager
- User CLIs: `mise`
- Network identity: Tailscale
- Dotfiles sync: `chezmoi`

For this setup, the standard hosts are `t14`, `btcaw`, `macbook`, and `macmini`, and the home Git mirror lives on `macmini`.
Use chezmoi templating for platform or machine-specific Codex context. Do not teach Codex to infer host identity by shelling out in shared instructions.
