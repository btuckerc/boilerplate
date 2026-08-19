---
name: bitwarden-secrets
description: Use the shared Bitwarden/Vaultwarden CLI boundary to provision or consume machine-local secrets without copying credentials into Git, commands, logs, or chat. Use for new secret-backed tools, rotating credentials, materializing protected env files, or running a command with a vault value.
---

# Bitwarden Secrets

Shared code stores only item names, field mappings, templates, and retrieval
logic. Secret values, `BW_SESSION`, OAuth tokens, generated env files, and vault
exports remain machine-local and must be excluded from Git and transcripts.

## Workflow

1. Inspect `bw-ensure-auth`. Authentication is interactive and per machine.
   Never automate a master password or persist `BW_SESSION` in shared config.
2. Prefer `bw-secret exec ITEM FIELD ENV_KEY -- COMMAND ...` when the consumer
   can receive an environment variable without a file.
3. Use `bw-secret write-env ITEM FIELD ENV_KEY FILE` only when the application
   requires a durable env file. The helper atomically preserves unrelated keys,
   writes mode `0600`, and never prints the value.
4. `bw-secret field` is for trusted command substitution only. Do not invoke it
   through agent tools or paste its output into chat, logs, command arguments,
   shell tracing, or diagnostics.
5. Keep app-specific wrappers when they encode a real schema or post-write
   action. Implement simple retrieval wrappers by calling `bw-secret` rather
   than duplicating CLI discovery, lock checks, and file-write logic.

Supported fields are `username`, `password`, `notes`, and `custom:NAME`.

## Provisioning and Rotation

Use hidden prompts or a user-supplied `0600` import file for initial storage.
Never pass values as command-line arguments. A one-shot `/tmp` script is only a
bootstrap aid: keep the durable importer in chezmoi, remove the temporary file
after success, sync the vault, materialize each consumer, and validate using
presence/permissions or an authenticated API call that cannot echo credentials.

Before adding a new importer, check whether `bw-secret`,
`opnsense-store-secret`, `obsidian-livesync-store-secret`, or the Restic helpers
already cover the data shape. Extend the common helper only for behavior shared
by multiple consumers.

## Safety Invariants

- Fail closed when `bw` is locked, unauthenticated, missing, or ambiguous.
- Do not silently switch vault servers or create/edit items without the user's
  authorization for that external write.
- Use item names or IDs in shared config; do not use secret values as lookup
  identifiers.
- Validate Git and chezmoi boundaries after every new integration.
- Redact tool output at the source; post-hoc transcript redaction is not a
  substitute for avoiding disclosure.
