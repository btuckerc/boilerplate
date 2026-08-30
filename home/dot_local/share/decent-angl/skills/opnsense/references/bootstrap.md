# OPNsense API bootstrap

The first key must be created in the GUI because SSH is closed and the API
cannot create its own initial credential.

1. Open System > Access > Users.
2. Use dedicated user `agent-api`. Grant only the endpoint privileges required
   for the task.
3. Create an API key and keep the one-time key/secret download local.
4. Run `opnsense-store-secret`, or pass its `--from` option a local `0600`
   download. It writes Bitwarden item `opnsense-api` and synchronizes the local
   env file without printing values.
5. Require `tls_pin=ok` and `api=ok` from `opnsense-api status`, then delete the
   one-time download.

## SSH key

Item `opnsense-agent-ssh`: private key in notes, public key in custom
field `public`. Unlock is per shell. The agent cannot use another
terminal's `BW_SESSION`.

1. Wrappers must exist. If `opnsense-agent-key` is not on PATH, pull
   published master and
   `chezmoi apply ~/.local/bin/opnsense-agent-key ~/.local/bin/opnsense-ssh`.
   Scheduled reconcile skips scripts.
2. Writer (already has `~/.ssh/opnsense_agent`):
   `export BW_SESSION="$(bw unlock --raw)"`
   `opnsense-agent-key store --from ~/.ssh/opnsense_agent`
   Expect `stored:opnsense-agent-ssh`.
3. Consumer (every other fleet machine): same unlock, then
   `opnsense-agent-key`. The wrapper runs `bw sync` first. Unlock alone
   does not pull. Expect `materialized:~/.ssh/opnsense_agent`.
4. `opnsense-ssh 'id -un; hostname'` prints `agent` and
   `router.home.arpa`.

Never copy the private key through chat, scp, or Git. If
vault.weavedweb.com returns 5xx, wait and retry. Do not paste vault
error JSON into chat.
