# macOS operations

- Shared CLI and dotfile behavior goes through Homebrew, mise, and chezmoi.
- Native preferences normally remain machine-local unless the user asks to
  standardize them.
- Inspect before writing with `defaults`, `pmset`, `scutil`, `networksetup`,
  `systemsetup`, or `launchctl` as appropriate.
- For trackpads, inspect both built-in and Bluetooth domains plus
  `NSGlobalDomain`; mirror a setting only where the hardware applies.
- Prefer clear, reversible CLI changes. If a setting is UI-only, say so rather
  than guessing.
- Treat Mac Mini as server-first; avoid user-facing UI changes unless requested.
