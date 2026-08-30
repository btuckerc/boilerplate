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

1. On a machine that already has `~/.ssh/opnsense_agent`, unlock bw and run
   `opnsense-agent-key store --from ~/.ssh/opnsense_agent`.
2. On every other fleet machine, unlock bw and run `opnsense-agent-key`.
3. `opnsense-ssh` should print a remote `uname` line. Never copy the private
   key through chat, scp, or Git.
