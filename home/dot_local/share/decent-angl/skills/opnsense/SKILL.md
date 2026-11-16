---
name: opnsense
description: Home network sites (clt Charlotte, elsie Rhode Island) - OPNsense routers via REST API and SSH, Wi-Fi APs (TP-Link, OpenWrt barn-ap), Zyxel switch, channel plans, firewall, DHCP, DNS, firmware, router Tailscale, visitor names, WAN shaper, LAN traffic. Not workstation networking.
---

# OPNsense

Use `opnsense-api` for appliance state. Default target is clt at `10.77.77.1`;
for elsie (`10.77.78.1`) set
`OPNSENSE_CONFIG_FILE=~/.config/decent-angl/opnsense-elsie.env`. Workstation
network settings stay in `platform-ops`.

## Sites and devices

Read the site page before touching anything at a site; it has the inventory (every
device, its IP, how to reach it, its secret item) and the open items.

- [references/sites.md](references/sites.md): conventions, the site page template,
  change rules, new-site and new-AP checklists. Follow it when adding anything.
- Sites: [references/clt.md](references/clt.md), [references/elsie.md](references/elsie.md).
- Wi-Fi standard and per-site channel plans: [references/wifi.md](references/wifi.md).
- Devices: [references/openwrt-ap.md](references/openwrt-ap.md) (barn-ap),
  [references/tplink-archer.md](references/tplink-archer.md) (BE9700s),
  [references/zyxel-xmg1915.md](references/zyxel-xmg1915.md) (elsie switch).
- Build and recovery files: `~/hearth/src/homenet` (OpenWrt AP images, R7800 TFTP kit).

Every change updates the site page in the same session: the fact in its section and a
dated change-log line with the before/after measurement.

## Boundary

- Shared config contains the host and TLS pins, never credentials or appliance
  backups.
- 1Password item `opnsense-api` materializes to a machine-local `0600` env file.
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

## Traffic shaper

This section is clt. elsie uses FQ-CoDel pipes, see
[references/elsie.md](references/elsie.md); the loaded-ping test method is in
[references/wifi.md](references/wifi.md).

Live WAN share recipe and the Steam multi-flow failure are in
[references/shaper.md](references/shaper.md). Do not put FQ-CoDel on a pipe
and a host mask on its queue. That does not isolate LAN IPs. Current share
recipe is WFQ pipes at 85/21 Mbit, queue mask `dst-ip` down and `src-ip` up,
CoDel on the queues. Two bulk WAN hosts split the pipe. They cannot each
get 85 Mbit on this circuit. Since 2026-11-11 a per-host Interactive queue
on each pipe takes ICMP and non-443 UDP ahead of the catch-all rules, so a
host's games and DNS do not queue behind its own downloads.

## Safety

- Never print API keys, secrets, or vault values.
- Reboot, halt, firmware changes, and factory reset require an explicit request
  and `--i-mean-it`.
- WAN/LAN addressing, default routes, and admin lockout paths require a rollback
  plan before apply.
- API filter endpoints may omit legacy GUI-only rules. Inspect before assuming
  the API sees every rule.
- Do not expose management, API, or SSH on WAN unless explicitly requested.
- Do not `auth/user/set` on `root`. That API reassigns uid 0.
- Anything that drops a site's internet or Wi-Fi (modem Apply, AP radio reload or
  reboot, switch reboot, firmware) needs the user's go-ahead first; see `sites.md`.

## Fleet shell

Never copy `~/.ssh/opnsense_agent` through chat, scp, or Git. Item
`opnsense-agent-ssh` is the only distribution path.

Reads use the machine's read-only 1Password service account (`op-secret`,
see `machine-secrets`); no unlock. Writes need the user's 1Password session,
so give the user the store command; they run it. `opnsense-agent-key status`
only reports local key mode and fingerprint.

1. Wrappers on PATH. `command -v opnsense-agent-key` and
   `command -v opnsense-ssh`. If missing, pull published master and
   `chezmoi apply ~/.local/bin/opnsense-agent-key ~/.local/bin/opnsense-ssh`.
   Scheduled reconcile skips scripts.
2. One writer. On a host that already has `~/.ssh/opnsense_agent`, the user
   runs `opnsense-agent-key store --from ~/.ssh/opnsense_agent`.
   Expect `stored:opnsense-agent-ssh`.
3. Each consumer runs `opnsense-agent-key` (agents may run it once the host is
   enrolled). It writes mode 600. Expect `materialized:...`.
4. `opnsense-ssh 'id -un; hostname'` prints `agent` and `router.home.arpa`.

Do not run step 3 before step 2. Do not run step 4 if step 3 failed.
1Password errors: wait and retry once; never print item contents.

## LAN clients

`opnsense-lan-clients` joins `dnsmasq/leases/search` with ARP vendors.
That is the agent view. Do not scrape the GUI. DHCP is dnsmasq, not Kea.

Unbound `regdhcp` is ISC-only and stays off. DHCP names live in dnsmasq
on port 53053. Unbound forwards `home.arpa` and the site's reverse zone
(`77.77.10.in-addr.arpa`, `78.77.10.in-addr.arpa`)
to `127.0.0.1:53053`, with `private-domain: home.arpa` so RFC1918
answers are not stripped. `dnsmasq.no_resolv=1`. LAN DHCP range domain
is `home.arpa`. Do not enable Unbound global forwarding.

Kernel ARP has no hostname column. Names come from DHCP option 12 and
from Unbound/dnsmasq (`dig @<router> host.home.arpa`,
`diagnostics/dns/reverse_lookup`). `*` is no name, usually a
randomized MAC. Manufacturer is the MAC OUI, not a model. OPNsense
does not know "Pixel 9" or "Galaxy S26" unless the device said so.

Static entries (dnsmasq hosts) per site are in the site page's inventory. A
host that must wake over Wi-Fi also needs a static ARP neighbor
(`interfaces/neighbor_settings`); see wincube in `clt.md`.

Default-deny packet logging is Firewall > Settings > Advanced
(`syslog.nologdefaultblock`). No REST API in 26.7. Do not add a WAN
catch-all block to fake it; that can steal last-match from WAN DHCP.

Per-host bytes come from local Netflow (Insight). Live config:
LAN+WAN capture, WAN egress-only (avoid NAT double count), v9 (IPv6),
local collector only at `127.0.0.1:2056`, `collect.enable=1`,
`activeTimeout=1800`, `inactiveTimeout=15`. No remote destinations.
Confirm with `diagnostics/netflow/isEnabled` (`netflow=1 local=1`) and
`diagnostics/netflow/status` (`active`). Top talkers:
`diagnostics/networkinsight/top/FlowSourceAddrTotals/<from>/<to>/src_addr/octets/15`
with unix timestamps. Per-IP aggregations start at 300s resolution.
Do not dump destination lists or DNS queries into chat.

Interface RRD is still LAN/WAN totals. Packet capture is on-demand at
`diagnostics/packet_capture`. Do not leave a capture running.

Do not install ntopng, Zenarmor, or Sensei. Do not add a remote Netflow
collector. Do not listen for Netflow on WAN.



