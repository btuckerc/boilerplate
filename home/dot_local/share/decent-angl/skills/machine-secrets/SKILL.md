---
name: machine-secrets
description: Add, rotate, read, or materialize a machine secret (API key, restic password, SSH key) from 1Password with op-secret, or enroll a host. Not for Grok Bots items, local keys, or generic secret-hygiene talk.
---

# Machine secrets (1Password)

Machine secrets live in 1Password and are read by `op-secret` with a
per-host, read-only service account. Shared code holds item names, field
mappings and retrieval logic. Values, tokens and generated env files stay
machine-local.

| Scope | Vault | Read by |
|---|---|---|
| `general` | Machine Secrets | every enrolled host |
| `backup` | Machine Secrets - Backup | backup hosts only (restic, backup escrow) |

Host tokens: `~/.local/share/decent-angl/secrets/op-machine.env` (dir 0700,
file 0600, `OP_SERVICE_ACCOUNT_TOKEN=…`). Service account per host:
`machine-secrets-<machine_id>`; a copy of each token is in the owner's
Personal vault as "Service account token: machine-secrets-<host>". Enrolled:
nous (general), macmini (general + backup).

## Reading (agents and jobs)

1. Prefer `op-secret exec ITEM FIELD ENV_KEY -- COMMAND ...`.
2. `op-secret write-env ITEM FIELD ENV_KEY FILE` only when a durable file is
   required: keeps other keys, atomic, mode 0600, prints no value.
3. `op-secret field ITEM FIELD` only for trusted command substitution (for
   example `RESTIC_PASSWORD_COMMAND`). Its output must not enter chat, logs,
   arguments, tracing or diagnostics.
4. `op-secret status` (vaults this host can read) and `op-secret ref ITEM
   FIELD` (the `op://` path) never print values; use them to check access.

Fields: `username`, `password`, `notes`, `custom:NAME`. Reads never use the
1Password app, Touch ID or `op signin`. Missing token, item or field fails
closed. The service accounts are rate-limited: never call `op-secret` in a
loop; materialize once instead.

## Adding or rotating an item (the only human step)

The user runs, in their own terminal on any enrolled host:

    op-secret add --scope general|backup [--replace] [--url URL] ITEM FIELD[=SOURCE]...

It signs in with the 1Password account password (no app, no Touch ID),
writes the item, signs out, and reads it back through that host's service
account. SOURCE: omitted = hidden prompt, `@PATH` = file, `env:NAME` =
environment variable, `-` = stdin. `--replace` updates only the named fields
(creates the item if absent). Agents never run `add`; give the user the
command. Then re-run each consumer's materializer (for example
`opnsense-api sync`, `omp-env`, `restic-local-password sync`).

Naming: item titles are lowercase kebab-case `<service>-<purpose>`
(`opnsense-api`, `restic-decent-angl`), unique across both vaults. A
key/secret pair is `username`/`password`; one token is `password`; multi-line
material (SSH keys) is `notes`; extras are `custom:NAME`. Pick `backup` only
for secrets that decrypt or reach backups; everything else is `general`.

App wrappers (`opnsense-store-secret`, `opnsense-agent-key store`,
`restic-bootstrap-secret`, `obsidian-livesync-store-secret`) are `add` with a
schema; extend `op-secret` only for behaviour several consumers share.

## Enrolling a host

Service account vault grants cannot change after creation, so a host that
needs another scope gets a new account. The user runs, on a host with SSH to
the target:

    op-secret enroll HOST --scope general [--scope backup] [--ssh DEST]

It creates missing vaults, creates `machine-secrets-HOST` with `read_items`
on those vaults only, installs the token (via SSH stdin when `--ssh`), saves
a copy in Personal, and checks the host sees exactly those vaults. Re-running
reuses a working token. Revoke a lost host's service account on
1password.com.

Grok Bots is separate: bots use `bw_bot.py` (op-secret pinned to the "Grok
Bots" vault and `op-grok-bots.env`).
