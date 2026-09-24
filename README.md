# Boilerplate dotfiles

This repository is the shared chezmoi source for macOS and Linux hosts. It keeps
shell, editor, terminal, tool, and host-specific configuration in one reviewed
Git baseline.

## Fresh host

```sh
mkdir -p ~/src
git clone https://github.com/btuckerc/boilerplate.git ~/src/boilerplate
cd ~/src/boilerplate
./setup --plan
./setup
```

`setup` installs chezmoi if needed, links `~/.local/share/chezmoi` to this
checkout, initializes host data, runs prerequisite/tool hooks, and verifies OMP,
Codex, and shared skills. Account logins and OS permission prompts remain local.

## Daily workflow

1. Edit the relevant source under `home/`.
2. Preview and apply the target, for example:
   ```sh
   chezmoi diff
   chezmoi apply ~/.zshrc
   ```
3. Review and commit the intended source changes.
4. Publish the committed baseline:
   ```sh
   decent-angl-sync publish
   ```

On another host, `decent-angl-sync reconcile` publishes reviewed local commits
when needed, fast-forwards, and applies committed state. The scheduled `guard`
converges without publishing. See [UPDATING.md](UPDATING.md) for the complete
publish/apply, recovery, and validation workflow.

## Tool ownership

`mise` owns language runtimes and CLI tools through exact pins in
[`home/dot_config/mise/config.toml`](home/dot_config/mise/config.toml). Homebrew
owns system packages, libraries, and GUI applications listed in
[`home/Brewfile`](home/Brewfile); do not duplicate mise tools there. Install a
changed pin explicitly on each host with `mise install TOOL@VERSION`.

## Where things live

| Path | Contents |
| --- | --- |
| [`setup`](setup) | Fresh-host bootstrap and plan mode |
| [`home/`](home) | Chezmoi source tree (`.chezmoiroot` points here) |
| `home/dot_config/` | XDG configuration: shell, mise, terminals, editors, and tools |
| `home/dot_local/bin/` | Installed local commands, including `decent-angl-sync` |
| `home/.chezmoidata/` | Fleet roles, package managers, and UI data |
| `home/dot_codex/` | Codex configuration and baseline README |
| `home/private_dot_omp/` | OMP configuration |
| [`utils/`](utils) | Baseline checks and maintenance scripts |
| [`docs/`](docs) | Reference and operational notes |
| [`UPDATING.md`](UPDATING.md) | Publish, reconcile, guard, recovery, and validation |

Host names, fleet roles, and package managers are in
`home/.chezmoidata/decentangl.yaml`.

## Troubleshooting

Start with the sync and health summaries:

```sh
decent-angl-sync status
decent-angl-doctor
decent-angl-doctor --fleet
chezmoi diff
mise doctor
```

Useful verified gotchas:

- `~/.local/share/chezmoi` must point to `~/src/boilerplate`; on an existing
  host, `decent-angl-sync adopt-source` preserves the old source before linking.
- The guard excludes `run_*` hooks. Use `decent-angl-sync reconcile --with-scripts`
  for a reviewed hook installation; ordinary `executable_*` files still apply.
- Working edits are never deployed: ordinary targets are held back, while edits
  to shared chezmoi inputs defer the whole apply. Inspect `decent-angl-sync status`.
- Secrets, auth, history, caches, and databases stay machine-local; do not add
  them to the source checkout.

## References

- [Shell cheatsheet](docs/reference/shell-cheatsheet.md)
- [VS Code shortcuts](docs/reference/vscode-shortcuts.pdf)
- [macOS development storage](docs/macos-development-storage.md)
- [Codex baseline](home/dot_codex/README.md)
