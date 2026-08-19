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
