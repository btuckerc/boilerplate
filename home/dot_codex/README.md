# Codex Baseline

This directory is the shared Codex baseline managed by chezmoi.

## Canonical Paths

- Working repo: `~/src/boilerplate/home/dot_codex/`
- Applied source: `~/.local/share/chezmoi/home/dot_codex/` (the same tree via symlink)
- Live config: `~/.codex/`

Edit the source tree, then apply targeted files with `chezmoi`.

## Astra policy across accounts

The shared model policy is `home/.chezmoitemplates/codex/model-policy.toml.tmpl`.
It selects `gpt-6-astra`, enables experimental context management, and leaves
context and compaction limits to the model.
Chezmoi applies that policy to each runtime's own parsed TOML, preserving its
other settings. TOML comments and formatting are normalized on apply.

- Primary CLI and desktop: `~/.codex/config.toml`.
- T3 second account: `~/.codex-t3/second/config.toml` links to the primary config.
- T3 last account: `~/.codex-t3/last/config.toml` links to the primary config.
- Second desktop: `~/.codex-gui/second/config.toml` stays independent and uses
  the same policy template. It is managed only on macOS after initialization.
- Third desktop: `~/.codex-gui/last/config.toml` uses the same policy template.
  Creating `~/.codex-gui/last` on macOS opts in to its managed config.

Apply on a machine with all three desktop runtimes initialized:

```sh
mise exec -- chezmoi apply ~/.codex/config.toml ~/.codex-gui/second/config.toml ~/.codex-gui/last/config.toml
```

For another
independent Codex home, add a config adapter that calls the same policy template
and ignores the target until initialized. Never link desktop runtime directories
or copy one account's complete config into another. Auth and runtime data remain
local. OMP model configuration is separate and is not changed by this policy.

The policy manages the default model and experimental context flag, and removes
root context overrides on each
apply. Reasoning effort, service tier, plugins, MCP connections, and project trust
remain local. Explicit task selections, project config, profiles, or CLI overrides
can supersede these defaults. Start a new session after applying.

### Experimental context management

```toml
[features.context_management]
experimental_mode = true
```

[Codex 0.153.0 release notes](https://learn.chatgpt.com/docs/changelog) describe
token-budget context, history notes, and the `new_context` tool for eligible
ChatGPT Plus, Pro, and Pro Lite sessions using the Codex backend. API-key sessions,
custom providers, and temporary structured threads are excluded. The feature is
off by default upstream; this baseline opts in. Both T3 accounts reported Pro
subscriptions during validation. Restart app-server sessions to load the change.
There is no documented subscription-savings guarantee. To roll back, change the
shared template's `experimental_mode` value to false and reapply both configs.

### One Codex version pin

The version lives in `home/dot_config/mise/config.toml`. All T3 instances use
`/Users/tucker/.local/bin/codex-baseline` on this Mac, or `$HOME/.local/bin/codex-baseline`
on another host. This wrapper resolves the applied mise version from the home
directory, avoiding project version overrides, then launches it in the original
working directory with the original account environment. It fails if the pin is
not installed. It never falls back to an arbitrary installed version.

`codex-t3-second` and `codex-t3-last` use the same wrapper. The official desktop
app has its own bundled runtime; changing the CLI pin does not upgrade the
desktop app.

For an upgrade, check the official changelog and npm `@openai/codex` stable tag,
install that exact version with `mise install codex@VERSION`, update the one source
pin, apply `~/.config/mise/config.toml`, and verify `codex-baseline --version` and
all T3 provider health checks. Commit and publish via `decent-angl-sync publish`.
Unrelated working edits may remain. Each fleet host must install the new pin.
The wrapper is an ordinary managed executable and deploys even when chezmoi
`run_*` hooks are excluded. Use a targeted apply for an actively edited checkout,
or `decent-angl-sync reconcile` on a clean host.
No automatic release updater is installed. A reviewed exact pin keeps machines
consistent; a floating `latest` choice changes independently on each machine.

On September 7, 2026, official npm and GitHub release metadata both reported
0.153.4 as latest stable. `mise latest codex` reported an older 0.152.0, so it was
not used to downgrade the existing installation. The 0.153.4 source pin had not
been applied locally, leaving the shell on 0.148.0 until this audit.

On September 10, 2026, the pin was upgraded to 0.154.0 after checking the official
changelog, npm stable tag and GitHub stable release. T3's `main`, `two` and `last`
providers all reported 0.154.0 and authenticated status after the targeted apply.

### Model context defaults

As of September 7, 2026, local Astra metadata advertises a 272,000-token Codex
context window. The [official configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
defines `model_context_window` and `model_auto_compact_token_limit`, with an unset
compaction threshold using model defaults. It does not recommend 400k / 360k as
an Astra quality preset.

[Astra's API model page](https://developers.openai.com/api/docs/models/gpt-6-astra)
lists a 1,050,000-token maximum and higher API pricing above 272k input tokens.
API pricing does not establish the multiplier for ChatGPT subscription usage.
A larger context can delay summaries, but does not establish better task quality.
The two accounts' extended-context entitlement was not tested.

The shared policy removes explicit context and compaction overrides. Keep model
defaults unless a separate, measured experiment justifies changing them.

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

- `auth.json` in `~/.codex` and in T3 shadow homes under `~/.codex-t3/`
- session history, caches, sqlite files, logs
- machine-local trust entries in `~/.codex/config.toml`

## Second ChatGPT/Codex GUI

The official Codex GUI is `/Applications/ChatGPT.app` (`com.openai.codex`).
It is the computer-use surface for Astra 3D. T3 Code is a CLI wrapper, not
this app.

The default ChatGPT.app profile lives in
`~/Library/Application Support/Codex` and uses `~/.codex` (exhausted first
sub). Do not sign that window into the second account.

Launch the second GUI with `codex-gui-second`. That is OpenAI's extra-instance
pattern (`CODEX_HOME` + `CODEX_ELECTRON_USER_DATA_PATH` + `--user-data-dir`):

- Desktop `CODEX_HOME`: `~/.codex-gui/second`
- Electron user data: `~/Library/Application Support/Codex-second/user-data`
- Sign in as the active Pro account, choose Codex, model `gpt-6-astra`
- Enable Plugins > Computer Use in that window

Never copy `~/.codex` or the primary `Application Support/Codex` tree into
the second paths.

`codex-gui-second-prepare` migrates the existing second-account login and takes
SQLite backups of task history on the first launch after quitting the old
desktop instance. Settings, databases, plugin caches, browser state, and IPC
then belong to the desktop profile. Existing session files and workspace
artifacts remain accessible through explicit links. The T3 CLI retains its
existing `~/.codex-t3/second` home. Do not use that shadow home for the desktop:
T3 links its mutable config and plugin runtime back to the primary home.

The launcher ignores an inherited `CODEX_HOME`. Override its dedicated path
only with `CODEX_GUI_SECOND_HOME`.

## T3 Code second account

Keep the exhausted ChatGPT/Codex sub in `~/.codex`. T3 isolates CLI login in
a shadow directory. Never copy `~/.codex` into the shadow path. Never launch
the Codex binary by itself for this account; that ignores the shadow overlay
and uses the first login in `~/.codex`.

T3 instance fields:

- Binary path: `/Users/tucker/.local/bin/codex-baseline` for both instances.
- CODEX_HOME path: `~/.codex`
- Shadow home path: `~/.codex-t3/second`
- Launch arguments: empty
- Model: `gpt-6-astra`

CLI for this account is `codex-t3-second`. Login and status:
`codex-t3-second login` then `codex-t3-second login status`.
The wrapper defaults `CODEX_HOME` to `~/.codex-t3/second` and uses the shared mise pin.

## Third account: last / Codex Third

Launch the third desktop with `codex-gui-third` or
`~/Applications/Codex Third.app`. Both select these paths even when launched
from another account's shell:

- Desktop `CODEX_HOME`: `~/.codex-gui/last`
- Electron user data: `~/Library/Application Support/Codex-last/user-data`
- T3 shadow home: `~/.codex-t3/last`

The desktop has independent config, login, databases, plugins and browser state.
Only `AGENTS.md`, `skills` and `rules` link to the primary shared guidance.
The initial config uses Astra, xhigh reasoning, default service tier and file
credential storage. Later policy applies preserve other local settings.

Initialize a new Mac before the first desktop launch:

```sh
mkdir -p ~/.codex-gui/last
chmod 700 ~/.codex-gui/last
mise exec -- chezmoi apply --exclude scripts ~/.local/bin/codex-t3-last ~/.local/bin/codex-gui-third ~/.codex-gui/last/config.toml ~/Applications/'Codex Third.app'
codex-gui-third
```

Sign in with the third account in the new desktop window. Keep all credentials
and runtime data machine-local. The launcher uses the installed ChatGPT.app, so
it follows desktop updates without maintaining another copy of the app.

T3's local provider entry is named `last`, with instance ID `codex_last`:

- Binary path: `$HOME/.local/bin/codex-baseline`, expanded to an absolute path.
- CODEX_HOME path: `~/.codex`
- Shadow home path: `~/.codex-t3/last`
- Launch arguments: empty
- Model: `gpt-6-astra`

T3 maintains its shadow links. Never copy the primary Codex home into this path.
For terminal login use `codex-t3-last login`, then `codex-t3-last login status`.
Sign in separately so T3 and the desktop have independent refresh sessions.
This wrapper ignores inherited `CODEX_HOME`, clears desktop login routing, and
always selects the last account.
T3 provider entries are app settings and remain local to each machine.

## Install Standard

- OS packages: native package manager
- User CLIs: `mise`
- Network identity: Tailscale
- Dotfiles sync: `chezmoi`

For this setup, the standard hosts are `t14`, `btcaw`, `macbook`, and `macmini`, and the home Git mirror lives on `macmini`.
Use chezmoi templating for platform or machine-specific Codex context. Do not teach Codex to infer host identity by shelling out in shared instructions.
