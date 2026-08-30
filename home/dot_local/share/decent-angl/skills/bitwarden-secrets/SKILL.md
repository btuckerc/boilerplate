---
name: bitwarden-secrets
description: Keep secrets out of Git, commands, logs, and chat with the shared Bitwarden/Vaultwarden CLI boundary. Use when provisioning, rotating, materializing, or consuming a secret.
---

# Bitwarden secrets

Shared code may store item names, field mappings, templates, and retrieval logic.
Values, sessions, generated env files, and exports stay machine-local.

## Workflow

1. Authenticate interactively with `bw-ensure-auth` on each machine. Never
   automate a master password or persist `BW_SESSION` in shared config.
2. Prefer `bw-secret exec ITEM FIELD ENV_KEY -- COMMAND ...` when a process can
   consume an environment variable.
3. Use `bw-secret write-env ITEM FIELD ENV_KEY FILE` only when a durable file is
   required. It preserves unrelated keys, writes atomically with mode `0600`,
   and does not print the value.
4. Reserve `bw-secret field` for trusted local command substitution outside
   agent tools. Its output must not enter chat, logs, arguments, tracing, or
   diagnostics.
5. Keep an app wrapper only when it adds a schema or post-write action. Reuse
   `bw-secret` for authentication, lock handling, and safe writes.

Supported fields: `username`, `password`, `notes`, and `custom:NAME`.

## Sessions and cache

`BW_SESSION` is per shell. Unlocking Ghostty does not unlock an agent
shell. Ask the user to run secret commands in their terminal. Do not
capture `BW_SESSION` from a PTY, logs, or chat.

Each machine has its own CLI database. `bw unlock` does not pull. After a
write on another host, `bw sync` before `get` or `list`. Wrappers that
materialize from the vault must sync themselves.

Vault HTTP 5xx: retry, fail closed, do not print the origin error body.

## Provisioning and rotation

Use hidden prompts or a user-supplied `0600` import file. A one-shot `/tmp`
script is a bootstrap aid, not durable configuration. After success, remove it,
sync the vault, materialize each consumer, and validate without echoing values.

Before adding an importer, search existing wrappers. Extend the common helper
only for behavior shared by multiple consumers.

## Safety invariants

- Fail closed when `bw` is locked, unauthenticated, missing, ambiguous, or
  returns non-JSON or HTTP 5xx.
- Creating or editing a vault item requires authorization for that external write.
- Use item names or IDs as shared lookup identifiers.
- Validate Git and chezmoi boundaries after every new integration.
- Prevent disclosure at the source; later redaction is not a substitute.
