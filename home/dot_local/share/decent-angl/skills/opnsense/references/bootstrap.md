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
