# LCRI node (Rhode Island)

Second site, online since 2026-11-15. Same hardware as `clt` (GMKtec NucBox M8,
Ryzen 5 PRO 6650H, 2x RTL8125 on `os-realtek-re`), OPNsense 26.7.

## Topology

```
Cox coax -> Orbi CBR750 (bridge mode, modem only) -> re1 WAN (right port, power side)
re0 LAN (left port, HDMI side) -> Zyxel XMG1915-10EP -> BE9700 AP + wired hosts
```

- WAN: Cox public DHCP (70.175.222.0/23 at cut-over), plus a DHCPv6 /128 on WAN.
  LAN has no IPv6 yet on purpose.
- LAN `10.77.78.0/24`, router `10.77.78.1` = `lcri.home.arpa`. dnsmasq DHCP
  pool .41-.245 (wizard default, kept to avoid renumbering).
- Static dnsmasq hosts: be9700 .111 (`68:7f:f0:75:f4:5b`, reports "ArcherBE600",
  AP mode), xmg1915 .112, winbox .120 (`10:ff:e0:b9:a8:21`), macmini .121
  (`d0:11:e5:81:01:6b`). Hosts move to their reservation on next renewal.
- Orbi admin in bridge mode: `http://192.168.100.1`. Its router-mode DMZ and
  reservation are dead config. Orbi Wi-Fi is off in bridge mode; satellite unplugged.
- Cox phone is on a separate Arris TM3402. Leave it alone.
- DNS is the clt design via the wizard's "Automatic DHCP/DNS registration": dnsmasq
  on 53053, Unbound forwards `home.arpa` and `78.77.10.in-addr.arpa` to it,
  `private-domain home.arpa`, DNSSEC, prefetch on.

## Access

- Targeting: `OPNSENSE_CONFIG_FILE=~/.config/decent-angl/opnsense-lcri.env opnsense-api ...`.
  Secret item `opnsense-api-lcri` (user `agent-api`, page-all). The local secret file is
  `~/.local/share/decent-angl/secrets/opnsense-api-lcri.env`.
- Until lcri joins Tailscale, nous reaches it through the wired Mac mini:
  `ssh -f -N -L 127.0.0.1:18443:10.77.78.1:443 mini`, then add
  `OPNSENSE_HOST=https://127.0.0.1:18443`. The TLS pin still applies.
- `os-tailscale` is installed but not enrolled (needs an auth key). Plan: Tailscale
  name `lcri`, advertise `10.77.78.0/24`, acceptDNS off, same as clt. Before
  approving the route, set `accept-routes=false` on RI LAN hosts (winbox, macmini).
  Otherwise their own LAN traffic rides WireGuard (the wincube lesson).
- No `agent` SSH user yet. root has two GUI-made API keys that the API cannot
  delete. Remove them in the GUI.

## Tuning (all verified 2026-11-15)

- Shaper: FQ-CoDel pipes 860 down / 90 up Mbit, quantum 300, ECN, one maskless
  queue each, rules WAN in/out. Measured 800/85 with ping +0-3 ms under full
  bidirectional load. The clt per-host WFQ recipe made upload latency worse here
  (376 ms), so it is not used. The Interactive queues and rules 10-15 exist but
  are disabled.
- Outbound NAT hybrid, with clt's pair: UDP static port 41641 for winbox, and LAN UDP
  endpoint-independent mapping. After a NAT change, kill old UDP states
  (`diagnostics/firewall/del_state/<id>`) or peers stay on DERP.
- Tunable `hw.re.flow_control=0` (boot time; OPNsense writes tunables into
  `/boot/loader.conf`). Before it, re1 logged `TX watchdog: stalled` for 19 minutes
  while the Orbi restarted, and WAN was dead until a reboot. Verify by
  checking that the WAN media string has no `rxpause,txpause`.
- WAN "Block private networks" stays off until someone ticks it in the GUI. It was
  needed off while WAN was behind the Orbi.

## Gotchas

- Any Apply on the Orbi restarts it, and the whole site loses internet for 2-5 min.
  Never stack an Orbi change with a BE9700 mode change.
- The CBR750 web UI has no radio off switch. "Enable AX / 2.4 / 5 GHz" toggles AX
  mode. Only bridge mode ("Router Mode: NO") disables Wi-Fi.
- The BE9700 in Router mode with its uplink in a LAN port runs a second DHCP server
  (192.168.0.x). Check with a DHCPDISCOVER probe, not leases.
