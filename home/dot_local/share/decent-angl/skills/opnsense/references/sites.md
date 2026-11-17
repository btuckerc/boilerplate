# Sites: model, conventions, checklists

One page per site (`clt.md`, `elsie.md`), one page per device type (`openwrt-ap.md`,
`zyxel-xmg1915.md`, `tplink-archer.md`), one cross-site Wi-Fi standard (`wifi.md`).
Site pages hold facts about that site; device pages hold how to operate that kind of
device anywhere. Build and recovery files live in the `homenet` repo
(`~/hearth/src/homenet`), never in a scratch directory or on a desktop.

## Conventions

| Item | Rule |
|---|---|
| LAN | `10.77.<N>.0/24` per site (clt 77, elsie 78). Never reuse a site's subnet: sites meet over Tailscale. |
| Router | `10.77.<N>.1`, OPNsense on GMKtec M8, dnsmasq DHCP + Unbound, domain `home.arpa`. |
| Infra addresses | `.110-.119` APs and switches, `.120-.129` fixed hosts, each with a dnsmasq host entry, even when the device is static (dnsmasq never leases a reserved address to anyone else). clt predates this for hosts (wincube .100, nous .157). |
| Tailscale | One node name per site router (`clt`, `elsie`), advertising only its own `/24`, acceptDNS off. Same-LAN hosts run `accept-routes=false`. |
| Secrets | 1Password vault Machine Secrets via `op-secret`: `<device>-<site>` (`zyxel-elsie`, `be9700-elsie`, `opnsense-api-elsie`). Agents read; only the user writes (`! op-secret add ITEM password`). Never print values. |
| Wi-Fi | One SSID per site on 2.4+5 GHz, WPA2/WPA3 mixed on every AP. Details and channel plans: `wifi.md`. |
| APs | AP mode only (no NAT, no DHCP), wired uplink only. A Wi-Fi-meshed AP repeats airtime and latency. |

## Site page template

Every site page has these sections, in this order. Keep each one current; history goes
in the change log, not in the facts.

1. **Summary**: one paragraph. What the site is, who depends on it, how disruptive changes are.
2. **Inventory**: one table, one row per device: name, role, IP, MAC, location, port on the
   switch, access method, secret item, write method. An agent should reach any device from here.
3. **Topology**: the cable path from the ISP to each AP and fixed host.
4. **Router**: addressing, DNS, DHCP reservations, NAT, shaper, tunables, monitoring.
5. **Wi-Fi**: this site's row of the `wifi.md` channel plan and any site exceptions.
6. **Switch**: port map and settings.
7. **Open items**: what is pending, who must act (user or agent), and why.
8. **Gotchas**: things that broke here and how to avoid them.
9. **Change log**: dated one-liners, newest first, with the measurement that justified the change.

## Rules for changes

- Measure before and after; record both in the change log (`ping med/p95/max`, throughput,
  RSSI). A change without a measurement is a guess.
- Change one thing at a time. Radio, mode and modem changes drop clients: say so before
  doing them, and never stack two (an Orbi Apply plus an AP mode change killed a site for minutes).
- Firmware upgrades and reboots of shared gear (router, switch, house AP) need the user's go-ahead.
- Update the site page in the same session as the change.

## New site checklist

1. Pick the next `10.77.<N>.0/24` and a Tailscale name. Add a site page from the template.
2. Router: OPNsense image, `os-realtek-re` (M8), `hw.re.flow_control=0`, LAN, dnsmasq + Unbound
   per `SKILL.md`, gateway monitoring (monitor 1.1.1.1), Netflow local only.
3. API user `agent-api`, key into `opnsense-api-<site>` (`references/bootstrap.md`), shared env
   file `~/.config/decent-angl/opnsense-<site>.env` with the TLS pins.
4. Shaper: measure the line with `networkQuality`, start FQ-CoDel pipes near 90% and tune with the
   loaded-ping method in `wifi.md`.
5. Tailscale enrollment (`os-tailscale`): `accept-routes=false` on same-LAN hosts first, listen
   port not used by a static-port NAT rule for a LAN host, then approve the route. For routed
   Wake-on-LAN add a static neighbor for the host on the router.
6. APs per `wifi.md`, switch per its device page, every secret in 1Password.

## New AP checklist

1. Give it a `.11x` address and a dnsmasq host entry.
2. Wired uplink to the switch. Record the switch port.
3. AP mode, same SSID and password as the site, WPA2/WPA3 mixed.
4. Pick channels from the site's plan in `wifi.md` (5 GHz on a different 80 MHz block from its
   neighbors, 2.4 GHz on 1/6/11). No auto channel on a multi-AP site.
5. Scan from the new AP and from a client at the cell edge; record RSSI of every same-SSID AP.
6. Put the admin password in 1Password as `<name>-<site>`. Add an inventory row and a change-log line.
