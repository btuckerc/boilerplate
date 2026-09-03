---
name: opnsense
description: Manage the home OPNsense router through its REST API, fleet SSH to clt, and LAN client inventory via opnsense-lan-clients. Use for firewall, DHCP, DNS, firmware, Tailscale on the router, visitor/device names, WAN traffic shaper, Steam vs other hosts, or traffic questions.
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

## Traffic shaper

Live WAN share recipe and the Steam multi-flow failure are in
[references/shaper.md](references/shaper.md). Do not put FQ-CoDel on a pipe
and a host mask on its queue. That does not isolate LAN IPs. Current share
recipe is WFQ pipes at 85/21 Mbit, queue mask `dst-ip` down and `src-ip` up,
CoDel on the queues. Two bulk WAN hosts split the pipe. They cannot each
get 85 Mbit on this circuit.

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

Shell user is `agent` (wheel, uid 2001), keys only. sshd listens on LAN
only, no password, no root. `ssh clt` is Tailscale SSH and may prompt.
Unattended shell is `opnsense-ssh` after the fleet key steps below.

Do not `auth/user/set` on `root`. That API reassigns uid 0.

Tailscale plugin: `acceptDNS` stays off so Unbound remains LAN DNS. Do not
open 22/443 on WAN.

## Fleet shell

Never copy `~/.ssh/opnsense_agent` through chat, scp, or Git. Item
`opnsense-agent-ssh` is the only distribution path.

Agents do not unlock Bitwarden. `BW_SESSION` is per shell. Give the user
the commands; they run them. `opnsense-agent-key status` is safe without
unlock. It only reports local key mode and fingerprint.

1. Wrappers on PATH. `command -v opnsense-agent-key` and
   `command -v opnsense-ssh`. If missing, pull published master and
   `chezmoi apply ~/.local/bin/opnsense-agent-key ~/.local/bin/opnsense-ssh`.
   Scheduled reconcile skips scripts.
2. One writer. On a host that already has `~/.ssh/opnsense_agent`, the user
   unlocks bw in that shell and runs
   `opnsense-agent-key store --from ~/.ssh/opnsense_agent`.
   Expect `stored:opnsense-agent-ssh`.
3. Each consumer. The user unlocks bw in that machine's shell and runs
   `opnsense-agent-key`. The wrapper syncs the CLI cache, then writes
   mode 600. Unlock does not pull. Expect `materialized:...`.
4. `opnsense-ssh 'id -un; hostname'` prints `agent` and `router.home.arpa`.

Do not run step 3 before step 2. Do not run step 4 if step 3 failed.
Vault 5xx: wait and retry. The wrapper retries sync and must not print
origin error bodies.

## LAN clients

`opnsense-lan-clients` joins `dnsmasq/leases/search` with ARP vendors.
That is the agent view. Do not scrape the GUI. DHCP is dnsmasq, not Kea.

Unbound `regdhcp` is ISC-only and stays off. DHCP names live in dnsmasq
on port 53053. Unbound forwards `home.arpa` and `77.77.10.in-addr.arpa`
to `127.0.0.1:53053`, with `private-domain: home.arpa` so RFC1918
answers are not stripped. `dnsmasq.no_resolv=1`. LAN DHCP range domain
is `home.arpa`. Do not enable Unbound global forwarding.

Kernel ARP has no hostname column. Names come from DHCP option 12 and
from Unbound/dnsmasq (`dig @10.77.77.1 host.home.arpa`,
`diagnostics/dns/reverse_lookup`). `*` is no name, usually a
randomized MAC. Manufacturer is the MAC OUI, not a model. OPNsense
does not know "Pixel 9" or "Galaxy S26" unless the device said so.

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



