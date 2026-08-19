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
- Codex is primary, with OMP as the pinned cross-platform terminal harness. Shared config goes through `decent-angl-config`, OMP changes through `omp-config`, platform/OS settings through `platform-ops`, and the home router through `opnsense`.
- Published `master` is authoritative. MacBook, Mac Mini, and T14 may author reviewed commits; use `decent-angl-sync` so dirty or diverged state is preserved instead of overwritten.
- Keep `~/.local/share/chezmoi` linked to `~/src/boilerplate`; the two historical source paths must resolve to the same checkout.
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
