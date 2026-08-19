---
name: opnsense
description: Inspect or change the home OPNsense router over its REST API. Use for firewall aliases/rules, interfaces, DHCP/DNS, firmware status, services, WireGuard, Unbound, or any OPNsense GUI change that should be done programmatically instead of computer-use.
---

# OPNsense

Prefer this skill over browser/computer-use for the LAN router at `10.77.77.1`.

## Boundary

- Shared, non-secret host pin: `~/src/boilerplate/home/.chezmoidata/decentangl.yaml` → `~/.config/decent-angl/opnsense.env`.
- Machine-local credentials: Bitwarden item `opnsense-api`, synced to `~/.local/share/decent-angl/secrets/opnsense-api.env` (mode 0600). Never Git or chezmoi.
- Live appliance state is local. Do not try to store `config.xml` or API secrets in the boilerplate.
- Workstation/OS settings stay in `platform-ops`. Router/firewall/DNS/DHCP stay here.

## Tooling

Use `opnsense-api`. Do not call `curl` with `-k` and pasted secrets.

```bash
opnsense-api status
opnsense-store-secret
opnsense-api sync
opnsense-api get core/firmware/info
opnsense-api get core/system/status
opnsense-api get interfaces/overview/interfacesInfo
opnsense-api get firewall/alias/searchItem
opnsense-api post firewall/filter/searchRule '{"current":1,"rowCount":50,"searchPhrase":""}'
opnsense-api apply-filter
```

Auth is HTTP Basic: API key as username, API secret as password. JSON in and out.

URL form: `https://10.77.77.1/api/<module>/<controller>/<command>/[<param>/...]`

Command names in docs are often snake_case; the live path is usually camelCase. When unsure, read the official endpoint list or copy the `/api/...` path from the GUI network tab, then replay it with `opnsense-api`.

- Docs: https://docs.opnsense.org/development/how-tos/api.html
- Index: https://docs.opnsense.org/development/api.html

## First-time bootstrap

SSH is closed. The first API key cannot be created over the API.

1. In the GUI: System → Access → Users.
2. Prefer a dedicated user `agent-api`, not `root`. Grant only the privileges needed for the work (Firewall, Interfaces, Unbound/Dnsmasq, Firmware status). Editing a privilege shows the API endpoints it covers.
3. On that user, API → `+`. Download the one-time `key=` / `secret=` file. The secret is not stored on the firewall.
4. Run `opnsense-store-secret` (or `/tmp/bw-store-opnsense.sh`). It unlocks Bitwarden if needed, prompts for key then secret (hidden), writes vault item `opnsense-api`, and runs `opnsense-api sync`.
5. If you still have the one-time download: `opnsense-store-secret --from ~/Downloads/apikey.txt`
6. `opnsense-api status` must report `tls_pin=ok` and `api=ok`. Delete the downloaded `apikey.txt` after sync.

Live user on this box: `agent-api` (not `root`). Vault item name stays `opnsense-api`.

If the self-signed cert is replaced, update `decentangl.network.opnsense.tls_fingerprint_sha256` and `tls_pinned_pubkey_sha256`, then re-apply `~/.config/decent-angl/opnsense.env`. Do not weaken the pin.

## Change workflow

1. `opnsense-api status`. If `api=unconfigured`, stop and run bootstrap. Do not fall back to computer-use unless the API cannot express the change.
2. GET the current object (`get`, `search`, `searchItem`, `searchRule`).
3. POST the mutation (`set`, `addItem`, `setItem`, `addRule`, `setRule`, `delItem`).
4. Apply/reconfigure the subsystem. Staged filter changes are inert until `opnsense-api apply-filter` or the matching `.../reconfigure` POST.
5. GET again and report the live fields. Do not claim apply from a `saved` response alone.

## Safety

- Never print `OPNSENSE_API_KEY`, `OPNSENSE_API_SECRET`, or the vault item.
- Reboot, halt, firmware update/upgrade, and factory reset require an explicit user request and `opnsense-api ... --i-mean-it`.
- WAN, LAN addressing (`10.77.77.0/24`), default route, and admin lockout paths need a rollback plan before apply.
- The firewall API filter endpoints manage automation/filter-model rules. Legacy GUI-only rules may not appear in `searchRule`. Inspect before assuming the API sees every rule.
- Do not enable WAN management, WAN API, or SSH unless the user asks.

## Common modules

| Task | Read | Write | Activate |
| --- | --- | --- | --- |
| Firmware / version | `GET core/firmware/info` | — | — |
| System health | `GET core/system/status` | — | — |
| Interfaces | `GET interfaces/overview/interfacesInfo` | module `set`/`setItem` | `POST .../reconfigure` |
| Aliases | `GET firewall/alias/searchItem` | `addItem` / `setItem` | `POST firewall/alias/reconfigure` |
| Filter rules | `GET|POST firewall/filter/searchRule` | `addRule` / `setRule` | `opnsense-api apply-filter` |
| Unbound | `/api/unbound/...` | `set` | `reconfigure` |
| Dnsmasq / Kea | `/api/dnsmasq/...`, `/api/kea/...` | `set` | `reconfigure` |
| WireGuard | `/api/wireguard/...` | `set` | `reconfigure` |
| Services | `GET core/service/search` | `start` / `stop` / `restart` | the POST itself |

## Verification

- After bootstrap: `opnsense-api status` → `tls_pin=ok`, `api=ok`.
- After a write: read-back of the same UUID/name plus the apply/reconfigure response.
- After chezmoi changes: `opnsense-api status` still pins `20915FA97BB4B3E59F1B41563D7F13C07643BDFD55DFE85F8A703456BA13459E`.
