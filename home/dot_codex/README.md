# Codex Baseline

This directory is the shared Codex baseline managed by chezmoi.

## Canonical Paths

- Working repo: `~/src/boilerplate/home/dot_codex/`
- Applied source: `~/.local/share/chezmoi/home/dot_codex/`
- Live config: `~/.codex/`

Edit the source tree, then apply targeted files with `chezmoi`.

## What Is Shared

- `config.toml`: portable Codex defaults
- `AGENTS.md`: short global working rules rendered by chezmoi for the current platform or known machine
- `skills/`: reusable Codex workflow knowledge rendered the same way

Current shared skills:

- `codex-config`: maintain the shared Codex baseline itself
- `platform-ops`: handle Omarchy/Linux and macOS system settings, hardware preferences, and shared-vs-local config decisions

## What Is Not Shared

- `auth.json`
- session history, caches, sqlite files, logs
- machine-local trust entries in `~/.codex/config.toml`

## Install Standard

- OS packages: native package manager
- User CLIs: `mise`
- Network identity: Tailscale
- Dotfiles sync: `chezmoi`

For this setup, the standard hosts are `omarchy`, `macbook`, and `macmini`, and the home Git mirror lives on `macmini`.
Use chezmoi templating for platform or machine-specific Codex context. Do not teach Codex to infer host identity by shelling out in shared instructions.
