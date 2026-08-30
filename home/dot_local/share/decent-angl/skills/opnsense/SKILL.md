---
name: opnsense
description: Manage the home OPNsense router through its REST API. Use for firewall, interfaces, DHCP, DNS, firmware status, services, WireGuard, Unbound, or router GUI changes.
---

# OPNsense

Use `opnsense-api` for appliance state at `10.77.77.1`. Workstation network
settings stay in `platform-ops`.

## Boundary

- Shared config contains the host and TLS pins, never credentials or appliance
  backups.
- Bitwarden item `opnsense-api` materializes to a machine-local `0600` env file.
- Use `opnsense-api`; do not paste credentials into `curl` or disable TLS checks.

If `opnsense-api status` reports `api=unconfigured`, read
[references/bootstrap.md](references/bootstrap.md). If a certificate changes,
confirm the new certificate, update both shared pins, re-apply, and revalidate.

## Change workflow

1. Run `opnsense-api status`; require `tls_pin=ok` and `api=ok`.
2. Read the current object through the API.
3. Submit the narrow mutation.
4. Apply or reconfigure the subsystem. A `saved` response alone is not active
   state.
5. Read the same object again and report the live fields.

Use `opnsense-api --help` and official endpoint documentation instead of
copying a command catalog into this skill. Live paths often use camelCase where
documentation uses snake_case.

- API guide: https://docs.opnsense.org/development/how-tos/api.html
- Endpoint index: https://docs.opnsense.org/development/api.html

## Safety

- Never print API keys, secrets, or vault values.
- Reboot, halt, firmware changes, and factory reset require an explicit request
  and `--i-mean-it`.
- WAN/LAN addressing, default routes, and admin lockout paths require a rollback
  plan before apply.
- API filter endpoints may omit legacy GUI-only rules. Inspect before assuming
  the API sees every rule.
- Do not expose management, API, or SSH on WAN unless explicitly requested.

## CLT node

This site's firewall is Tailscale name `clt` (`clt.tail4d5aec.ts.net`,
`100.109.139.83`). LAN is still `10.77.77.1` / `router.home.arpa`. Future
sites get their own Tailscale name. Do not reuse `clt`.

`opnsense-api` stays on `https://10.77.77.1` with the TLS pin. The GUI/API
does not listen on the Tailscale address. Off-LAN API access needs the
advertised `10.77.77.0/24` subnet route approved in the Tailscale admin
console.

Shell user is `agent` (wheel, uid 2001), keys only. Vault item
`opnsense-agent-ssh` materializes to `~/.ssh/opnsense_agent` via
`opnsense-agent-key`. sshd listens on LAN only, no password, no root.
`ssh clt` is Tailscale SSH and may prompt. Unattended shell is
`opnsense-ssh`.

Do not `auth/user/set` on `root`. That API reassigns uid 0.

Tailscale plugin: `acceptDNS` stays off so Unbound remains LAN DNS. Do not
open 22/443 on WAN.
