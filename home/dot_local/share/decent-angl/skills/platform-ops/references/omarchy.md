# Omarchy operations

- Install OS packages with `omarchy-pkg-add`.
- Inspect relevant `hyprctl` values and systemd unit status before changing them.
- Durable desktop source lives under `~/src/boilerplate/home/dot_config/`; live
  state lives under `~/.config/`.

Quattro uses Hyprland Lua overrides and Omarchy Quickshell. Use `omarchy bar`,
`omarchy plugin`, and `omarchy restart shell`; pre-Quattro Waybar, Mako, and
Walker configuration is retained history, not the active desktop.

Bar popup motion, panel copy, and workspace indicators live in
`~/.local/share/omarchy-shell-overlay/`, mirroring paths under
`/usr/share/omarchy/shell/`. Packaged files stay untouched.
`omarchy-launch-shell` copies the packaged shell to a runtime tree,
overlays every path listed in `upstream.sha256`, and retargets
first-party plugin scan at that tree so overlay bar widgets load.
Do not wrap the shell in `bwrap`: a user namespace remaps root to
65534 and sets `NoNewPrivs`, which breaks sudo and lock-screen passwords.
Use `omarchy-shell-overlay disable` to run stock popups and numbers,
`enable` to put the overlay back, and `reset` after an Omarchy upgrade
if you want the new packaged QML as the overlay base. A changed packaged
hash skips the overlay until you reset or update the hashes.

Packaged Omarchy owns `/usr/share/omarchy`, `OMARCHY_PATH`, Hyprland bootstrap,
shell launch, idle/lock, battery services, and generated state below
`~/.local/state/omarchy/`. Never export `OMARCHY_PATH` from chezmoi or prepend
`~/.local/share/omarchy/bin`.

Before a roaming change, run `omarchy-roaming-sync preflight`. Afterward, run
`omarchy-roaming-sync validate`; use `--strict` before publishing. The validator
checks the generation contract, source/live state, legacy ownership, SSH config
modes, syntax, UWSM, Hyprland parsing, and shell layers. Use
`omarchy-roaming-sync repair-ssh` for its exact passwordless-sudo repair.

Generated `hyprland.lua`, `monitors.lua`, `shell.json`, and
`~/.local/state/omarchy/current/*` remain outside the portable manifest unless
deliberately promoted.

For Hyprland changes, reload with `hyprctl reload` and require an empty
`hyprctl configerrors` result before completion.
