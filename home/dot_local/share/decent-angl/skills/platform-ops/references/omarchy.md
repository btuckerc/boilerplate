# Omarchy operations

- Install OS packages with `omarchy-pkg-add`.
- Inspect relevant `hyprctl` values and systemd unit status before changing them.
- Durable desktop source lives under `~/src/boilerplate/home/dot_config/`; live
  state lives under `~/.config/`.

Quattro uses Hyprland Lua overrides and Omarchy Quickshell. Use `omarchy bar`,
`omarchy plugin`, and `omarchy restart shell`; pre-Quattro Waybar, Mako, and
Walker configuration is retained history, not the active desktop.

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
