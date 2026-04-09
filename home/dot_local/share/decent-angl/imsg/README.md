# imsg

Standalone personal messaging bridge bundle for `decent-angl`.

## Layout

- `imsg_app.py`: shared app entrypoint
- `~/.local/bin/imsg`: cross-platform client surface
- `~/.local/bin/imsgd`: local bridge/index surface on `macmini`
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
- `imsgd sync`

## Notes

- Replies and reactions are modeled in the read path from day one.
- Send history, idempotency state, and retryable outbox jobs live in the same local state root.
- The active send backend on `macmini` is provider-backed `imsg send`, with AppleScript fallback kept behind the same app surface.
- The remote surface is intentionally simple: `imsg` forwards to `imsgd` over Tailscale/SSH.
- The bundle is intentionally shippable on its own: one app directory, one config file, two thin wrappers.
