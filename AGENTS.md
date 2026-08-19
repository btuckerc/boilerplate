# Repository Agent Instructions

chezmoi + mise dotfiles. Source root is `home/` (via `.chezmoiroot`).

## Layout

- `home/dot_config/` → `~/.config/`
- `home/dot_local/bin/` → `~/.local/bin/`
- `home/private_dot_omp/private_agent/` → `~/.omp/agent/` (shared OMP baseline)
- `home/Brewfile` → Homebrew bundle
- Templates end in `.tmpl` (Go templates; OS/machine conditionals)

## Working rules

- Edit the source under `home/`, then `chezmoi apply`. Do not treat live home files as the source of truth.
- Keep credentials, `~/.omp/agent/agent.db`, OAuth tokens, sessions, caches, and machine-local state out of Git.
- Preserve unrelated dirty worktree changes.
- OMP is the primary terminal harness. Shared OMP changes go through the `omp-config` skill; platform/OS settings through `platform-ops`; the home OPNsense router through `opnsense`.
- MacBook is the only OMP authoring source. Run `omp-baseline validate --strict` there before publishing; consumers use `omp-baseline pull` and the hourly guard repairs drift from published `master`.
- On macOS with iCloud Desktop & Documents, keep active repos and build trees under `~/src`, not `~/Documents`.

## Commands

```bash
chezmoi diff
chezmoi apply
chezmoi apply PATH
mise install
mise ls
```

## Longer docs (read on demand)

- `README.md` — bootstrap and overview
- `CHEZMOI.md` — templates, hooks, source layout
- `MISE.md` — tool backends and pins
- `TROUBLESHOOTING.md` — recovery
- `UPDATING.md` — upgrades
