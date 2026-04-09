# imsg

Standalone personal messaging bridge bundle for `decent-angl`.

## Layout

- `imsg_app.py`: shared app entrypoint
- `~/.local/bin/imsg`: cross-platform client surface
- `~/.local/bin/imsgd`: local bridge/index surface on `macmini`
- `~/.local/bin/imsg-tui`: fullscreen TUI frontend
- `tui/`: Rust `ratatui` + `crossterm` frontend source
- `~/.config/decent-angl/imsg.env`: rendered machine-specific config
- `IMSG_STATE_ROOT`: local bridge state root

## Baseline

- `macmini` is the only Apple-dependent bridge host
- `chat.db` stays local to `macmini`
- the indexed read model lives under `IMSG_STATE_ROOT`
- other machines use `imsg` over Tailscale/SSH

## Implemented commands

- `imsg doctor`
- `imsg contacts [query]`
- `imsg chats [query]`
- `imsg unreads [query]`
- `imsg show <chat>`
- `imsg tail <chat>`
- `imsg search <query>`
- `imsg attachments <chat>`
- `imsg outbox`
- `imsg send --to <recipient> --text <message>`
- `imsg reply --message <message> --text <message>`
- `imsg retry <job-id>`
- `imsg tui`
- `imsg-tui`
- `imsgd sync`

## Notes

- Replies and reactions are modeled in the read path from day one.
- Send history, idempotency state, and retryable outbox jobs live in the same local state root.
- The active send backend on `macmini` is provider-backed `imsg send`, with AppleScript fallback kept behind the same app surface.
- The remote surface is intentionally simple: `imsg` forwards to `imsgd` over Tailscale/SSH.
- The remote client path is key-only SSH with strict host-key checking, no password fallback, no keyboard-interactive auth, and no forwarded agent state.
- The TUI is the same app surface, not a separate protocol: it shells through `imsg --json` and inherits the same transport and guardrails.
- First launch of `imsg tui` or `imsg-tui` compiles the local Rust binary under `~/.local/share/decent-angl/imsg/tui/target`.
- The shipped list view is conversation-first: it prefers contact names from macOS Contacts, falls back to handles only when needed, and shows recent message previews instead of raw chat identifiers.
- Chat selection is intentionally lazy-loaded: moving through the conversation list does not reload the full transcript on every keypress.
- Core TUI controls:
  - `Tab` switch panes
  - `/` search
  - `c` compose
  - `r` reply to the selected message
  - `o` show outbox
  - `?` help
- The bundle is intentionally shippable on its own: one app directory, one config file, two thin wrappers.
