---
description: Update pinned Pi version in boilerplate/chezmoi and install it
argument-hint: "[version]"
model: openai-codex/gpt-5.4
thinking: medium
restore: true
---
Update Pi for this setup. Use version `$1` if provided; otherwise discover the latest stable Pi release and use that exact version.

Work carefully and do not make assumptions:
- First inspect how Pi is installed and managed here.
- Treat `~/.pi/agent` as live state managed by chezmoi. Edit the shared source tree instead of the live files.
- Use `chezmoi source-path` to find the active source for shared Pi files. Keep `~/src/boilerplate/...` and `~/.local/share/chezmoi/...` aligned when both copies exist.
- Remember that `pi update` is for Pi packages and pinned package sources; it does **not** update the pinned Pi CLI version in this setup.
- Review the target version changelog before editing. Use the release page if helpful: `https://github.com/badlogic/pi-mono/releases/latest` and `https://raw.githubusercontent.com/badlogic/pi-mono/main/packages/coding-agent/CHANGELOG.md`.
- Update every intentional Pi version pin you find for this setup, including:
  - `home/dot_config/mise/config.toml`
  - `home/run_onchange_after_04-setup-pi-agent.sh.tmpl`
  - `home/dot_pi/agent/settings.json.tmpl` if `lastChangelogVersion` should move with the upgrade
  - any matching mirrored copy under the other shared source tree
- Keep Pi package versions unchanged unless required.
- After editing, run `chezmoi apply`, install the target Pi version with `mise install` or a more specific equivalent, and verify with `pi --version`.
- End with a concise summary of the version change, changed files, commands run, and any follow-up.
