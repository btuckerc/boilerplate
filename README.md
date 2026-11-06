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

1. Author in a worktree of this checkout:
   `git -C ~/src/boilerplate worktree add ~/src/boilerplate-wt/<task>`.
   Uncommitted edits in `~/src/boilerplate` itself hold back applies.
2. Preview: `chezmoi -S ~/src/boilerplate-wt/<task> diff`.
3. Review and commit there, then land with `git merge --ff-only` in
   `~/src/boilerplate`.
4. Publish and apply the committed baseline:
   ```sh
   decent-angl-sync reconcile
   ```

On another host, `decent-angl-sync reconcile` publishes reviewed local commits
when needed, fast-forwards, and applies committed state. The scheduled `guard`
converges without publishing. See [UPDATING.md](UPDATING.md) for the complete
publish/apply, recovery, and validation workflow.

## Tool ownership

`mise` owns language runtimes and CLI tools through exact pins in
[`home/dot_config/mise/config.toml`](home/dot_config/mise/config.toml). Homebrew
owns system packages, libraries, and GUI applications listed in
[`home/Brewfile`](home/Brewfile); do not duplicate mise tools there. Changed
pins install through `decent-angl-sync reconcile` and each host's guard.

## Herdr

Herdr is pinned through mise and configured at `~/.config/herdr/config.toml`.
Run `herdr` once, start each `omp` session in its own workspace or tab, and
detach with `Ctrl-b q`; running sessions stay attached to the local Herdr
server. The managed OMP integration supplies working/blocked/idle state and
native session restore. Runtime sessions and saved SSH-machine profiles remain
machine-local.

## Terminal font

macOS Ghostty uses [Obel Mono](https://typographic.systems/obel-mono) 1.000
(SIL OFL 1.1): regular at 400, bold at the ExtraBold instance, and cell height
16% to keep Meslo's line rhythm. `run_onchange_after_07-install-obel-mono`
installs pinned, hash-checked TTFs on macOS and Linux desktops, into
`~/Library/Fonts` or `~/.local/share/fonts/obel-mono`; existing hosts get it
through `decent-angl-sync reconcile --with-scripts` (the reviewed font hook).
The always-masked "Obel Mono Masked" family is installed for apps without font
feature settings. Linux Ghostty and kitty stay on JetBrains Mono until Obel
Mono is verified on screen there. macOS kitty keeps Meslo because CoreText does
not flag Obel Mono as monospace, so kitty there falls back to Menlo.

Feature `ss01` masks recognised secrets (`ghp_`, `sk-`, `TOKEN=`,
`Authorization: Bearer`, …) after their first four characters. Only pixels
change: copy, paste, files, and history keep the real value. The part of a key
that wraps onto the next line, and unrecognised formats, stay visible. For one
unmasked window, run `open -na Ghostty --args --font-feature=-ss01`.

## Where things live

| Path | Contents |
| --- | --- |
| [`setup`](setup) | Fresh-host bootstrap and plan mode |
| [`home/`](home) | Chezmoi source tree (`.chezmoiroot` points here) |
| `home/dot_config/` | XDG configuration: shell, mise, terminals, editors, and tools |
| `home/dot_local/bin/` | Installed local commands, including `decent-angl-sync` |
| `home/.chezmoidata/` | Fleet roles, package managers, and UI data |
| `home/private_dot_codex/` | Codex configuration and baseline README |
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
- The guard excludes `run_*` hooks but runs `omp-baseline apply` once per revision,
  installing OMP and companion mise pins. Use `decent-angl-sync reconcile --with-scripts`
  only for reviewed hook installations, such as fonts or native prerequisites.
- Working edits are never deployed: ordinary targets are held back, while edits
  to shared chezmoi inputs defer the whole apply. Inspect `decent-angl-sync status`.
- Secrets, auth, history, caches, and databases stay machine-local; do not add
  them to the source checkout.

## References

- [Shell cheatsheet](docs/reference/shell-cheatsheet.md)
- [VS Code shortcuts](docs/reference/vscode-shortcuts.pdf)
- [macOS development storage](docs/macos-development-storage.md)
- [Codex baseline](home/private_dot_codex/README.md)
