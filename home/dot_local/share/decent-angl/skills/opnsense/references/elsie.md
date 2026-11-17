# elsie site (Rhode Island)

## Summary

The Rhode Island house, LAN `10.77.78.0/24`, online since 2026-11-15. The household
(including Tucker's mother) depends on it, so any change that drops internet or Wi-Fi gets
the user's go-ahead first. Router hardware matches clt (GMKtec NucBox M8, Ryzen 5 PRO 6650H,
2x RTL8125 on `os-realtek-re`). The gaming PC `winbox` (Apollo host) sits in the barn.

## Inventory

| Device | Role | IP | MAC | Where | Switch port | Access from nous | Secret | Writes |
|---|---|---|---|---|---|---|---|---|
| Orbi CBR750 | Cox cable modem, bridge mode | admin `192.168.100.1` | - | - | (M8 WAN) | browser on the LAN | user only | user only; every Apply drops the site 2-5 min |
| elsie (M8) | OPNsense 26.7.9_1 router | `10.77.78.1` `elsie.home.arpa` | re0 `70:70:fc:09:0d:2d` | - | 1 (2.5G) | `opnsense-api`, tunnel below | `opnsense-api-elsie` (user `agent-api`) | API |
| xmg1915 | Zyxel XMG1915-10EP switch | `10.77.78.112` | `70:49:a2:21:1e:f5` | - | - | SSH CLI (read), HTTPS forms (write) via mini | `zyxel-elsie` (`admin`) | `zyxel-xmg1915.md` |
| be9700 | house AP, TP-Link (reports Archer BE600 v1.0) | `10.77.78.111` | `68:7f:f0:75:f4:5b` | house | 7 (2.5G) | `tplinkrouterc6u` via mini tunnel | `be9700-elsie` | untested, `tplink-archer.md` |
| barn-ap | barn AP, NETGEAR R7800 on OpenWrt 25.12.6 | `10.77.78.110` (static) | `b0:b9:8a:73:7a:5c` | barn | 5 (1G, barn cable) | `ssh barn-ap` | root password file on nous (see Open items) | `uci`, `openwrt-ap.md` |
| winbox | gaming PC, Apollo host; Tailscale `accept-routes=false` | `10.77.78.120` | `10:ff:e0:b9:a8:21` | barn, barn-ap `lan1` (1G) | 5 via barn-ap | `ssh winbox`, MCP `winbox` (Tailscale) | - | `platform-ops` `winbox-streaming.md` |
| macmini | Mac mini M4, jump host, wake sender; Tailscale exit node, `accept-routes=false` | `10.77.78.121` | `d0:11:e5:81:01:6b` | - | 8 (1G) | `ssh mini` (Tailscale) | - | - |
| Arris TM3402 | Cox phone modem | - | - | - | - | - | - | leave alone |

## Access

- elsie is on Tailscale as `elsie` (`100.114.139.94`). The GUI/API does not listen there and nous
  does not accept routes (clt's route covers its own LAN), so nous still reaches the LAN through
  the Mac mini. Router API:
  `ssh -o ExitOnForwardFailure=yes -f -N -L 127.0.0.1:18443:10.77.78.1:443 mini`, then
  `OPNSENSE_CONFIG_FILE=~/.config/decent-angl/opnsense-elsie.env OPNSENSE_HOST=https://127.0.0.1:18443 opnsense-api ...`.
  The TLS pin still applies. An empty fingerprint in `opnsense-api status` means the tunnel
  died: kill the old `ssh -L` (match `^ssh .*18443:`) and start it again.
- `ssh barn-ap` is a host-local `~/.ssh/config` entry on nous: `root@10.77.78.110`,
  `ProxyJump mini`, key `~/.ssh/id_ed25519_fleet` (`id_ed25519` also authorized). Key-only.
- Config backup: `opnsense-api get core/backup/download/this > elsie-config.xml` (0600; it
  holds password hashes). barn-ap: `ssh barn-ap 'sysupgrade -b -'`.

## Topology

```
Cox coax -> Orbi CBR750 (bridge) -> M8 re1 WAN (right port, power side), public DHCP + DHCPv6 /128
M8 re0 LAN (left port, HDMI side) -> xmg1915 port 1
  port 7 -> be9700 (house)
  port 8 -> macmini
  port 5 -> barn cable -> barn-ap wan (yellow); barn-ap lan1 -> winbox
```

barn-ap bridges wan, lan1-4 and both radios, all on DSA conduit eth0 (`openwrt-ap.md`).
winbox <-> uplink is switched in the R7800's switch chip and never touches the AP CPU.

## Router

- LAN `10.77.78.1/24`, dnsmasq DHCP pool `.41-.245`, domain `home.arpa`. Host entries:
  barn-ap .110, be9700 .111, xmg1915 .112, winbox .120, macmini .121.
- DNS as clt: dnsmasq on 53053, Unbound forwards `home.arpa` and `78.77.10.in-addr.arpa`
  to it, `private-domain home.arpa`, DNSSEC, prefetch, aggressive NSEC, serve-expired
  (TTL 86400, client timeout 1800 ms), msg/rrset cache 64m/128m.
- Shaper: FQ-CoDel pipes 800 down / 90 up Mbit, quantum 300, ECN, one maskless queue
  each, rules WAN in/out. Pipe UUIDs: down `596234c5-83d3-46b4-b2b4-646109c2d361`, up
  `42d53d14-a647-4f92-9029-c0c3685a2d2c`. Interactive queues and rules 10-15 exist,
  disabled. clt's per-host WFQ recipe made upload latency worse here (376 ms).
- Outbound NAT hybrid: UDP static port 41641 for winbox (Tailscale direct paths), LAN UDP
  endpoint-independent mapping. After a NAT change, delete old UDP states
  (`diagnostics/firewall/del_state/<id>`) or peers stay on DERP.
- Tunable `hw.re.flow_control=0` (boot time). Check that the WAN media string has no
  `rxpause,txpause`. Hardware offloads off.
- WAN: block private networks and bogons on. Gateway `WAN_DHCP` monitored (1.1.1.1, host
  route on, failover/failback states off); default gateway switching off and no rule sets a
  gateway, so a down status cannot move routes. Read `routes/gateway/status` (about 19 ms).
- Netflow as clt: LAN+WAN capture, WAN egress-only, v9, local collector only.
- IPv6: re0 gets a Cox PD prefix (track interface), but nothing advertises it, so LAN
  clients have no global IPv6 or IPv6 default route. On purpose until the Realtek IPv6
  concern is checked. Macs also hold a ULA from another source on the LAN (probably an Apple
  home hub; not identified).
- Plugins: `os-realtek-re`, `os-tailscale`.
- Tailscale `elsie` (`elsie.tail4d5aec.ts.net`, `100.114.139.94`), key expiry off: listen port
  set to 41642 (WAN 41641 belongs to winbox's static NAT), acceptDNS off, accept routes off, SSH
  on, SNAT on, route `10.77.78.0/24` approved. Peers see it on port 31642 (why not 41642: not
  checked; no shell on elsie yet). winbox keeps its direct path on 41641.
- Static neighbor (Interfaces > Neighbors): winbox `10.77.78.120` = `10:ff:e0:b9:a8:21`, so a
  routed magic packet reaches it asleep (its NIC does not answer ARP in S3).

## Wi-Fi

Plan and rules: `wifi.md` (elsie rows). The house BE9700 reaches the barn at -72 dBm
(5 GHz) and -67 to -82 dBm (2.4 GHz), so barn clients can stick to it. Barn-ap is
configured from `homenet/openwrt-ap/sites/elsie-barn-ap.env`.

## Switch

xmg1915, firmware V4.80(ACGP.0) 07/2023. Ports in the inventory; 2-4, 6, 9, 10 empty.
Flow control, EEE and auto power down off; loop guard on all ports; RSTP and IGMP snooping
off; telnet/FTP/HTTP/SNMP off. All counters clean on 2026-11-16 (0 CRC, pause, collisions).

## Open items

| Item | Who | Notes |
|---|---|---|
| Phones with Tailscale on this LAN | agent | Not checked whether iOS keeps LAN traffic local once the route is approved (macOS does). |
| Delete root's two GUI-made API keys on elsie | user (GUI: System > Access > Users > root) | The API cannot delete them. Also delete `lcri.home.arpa_root_apikey.txt` from the MacBook's Downloads. |
| Store barn-ap secrets in 1Password | user | `! op-secret add barn-ap-r7800 password=@/home/tux/.local/share/decent-angl/secrets/barn-ap-root.txt` and `! op-secret add wifi-elsie password`. Then the AP can be rebuilt without the live AP. |
| BE9700: pin 5 GHz 149 and 2.4 GHz 11 | agent after a tested write, or user in the GUI | Writes untested (`tplink-archer.md`). |
| Firmware: BE9700 update offered; switch ACGP.0 -> ACGP.3 | user decides when | Each drops Wi-Fi or the whole site for minutes. |
| `agent` SSH user on elsie; automatic recovery from a re1 TX stall | agent | Not built. |

## Gotchas

- Any Orbi Apply restarts it: the site loses internet for 2-5 min. Never stack it with an AP change.
- The CBR750 has no radio switch; only bridge mode ("Router Mode: NO") turns its Wi-Fi off.
- A TP-Link AP in Router mode with its uplink in a LAN port runs a second DHCP server.
- The Orbi satellite left powered on beacons a hidden network on 2.4 GHz ch 5 and 5 GHz
  ch 157 next to barn-ap. Keep it unplugged.
- The R7800's stock web server died after a firmware update; it runs OpenWrt now (`openwrt-ap.md`).
- winbox ignores ping (Windows firewall, Public profile). Measure from winbox outwards, or
  `wget -qO- http://10.77.78.120:47989/serverinfo` (Apollo). BusyBox `nc` on barn-ap cannot test ports.
- Asleep, winbox's Realtek NIC does not answer ARP (ARP offload on, still nothing). Same-LAN
  wake must be broadcast (Moonlight and `wake winbox` send broadcasts); routed wake needs the
  static neighbor on elsie.
- A Windows host on this LAN with `accept-routes=true` would send its LAN traffic through the
  tunnel (Tailscale route metric 0 beats Ethernet 256); winbox and macmini have it off. macOS is
  fine: the tunnel route is interface-scoped (`UCSI`), and the MacBook stays on en0 (checked).

## Change log

- 2026-11-17 elsie joined Tailscale (user login, key expiry off, route approved). MacBook on barn Wi-Fi still reaches winbox over en0 (connect median 4.3 ms before and after). Routed wake verified: unicast-only magic from the MacBook bound to utun4 woke winbox in 6 s via elsie.

- 2026-11-17 Tailscale on elsie configured (port 41642, route 10.77.78.0/24, SSH on), waiting for login; old auth key rejected. `accept-routes=false` on winbox and macmini first. Static neighbor for winbox. LAN ping during the Tailscale start: 40/40, max 0.47 ms.
- 2026-11-17 Wake verified with real sleeps: broadcast from barn-ap's bridge (Wi-Fi side) wakes winbox in 8 s; unicast-only fails (no ARP reply while asleep). Moonlight sends broadcasts and has the right MAC.
- 2026-11-17 barn-ap: Wi-Fi clients and the AP could not reach winbox (lan1 -> CPU unicast dropped: lan ports on conduit eth1, wan on eth0, one bridge). All lan ports moved to conduit eth0 (`network.lanN_dev`), reload with 0/45 pings lost. Moving the uplink to lan2 first had taken barn Wi-Fi offline; moved back to the yellow port.

- 2026-11-16 Switch: telnet/FTP/HTTP off, loop guard on all ports, saved to config 1. Latency across it unchanged (elsie 0.4 ms, barn-ap 0.5 ms from macmini).
- 2026-11-16 barn-ap: 802.11k/v on, 2.4 GHz 20 dBm (was 30), packet steering on, ULA removed. Reloading the radios moved 3 of 4 barn clients to the house AP; 2 came back on their own.
- 2026-11-16 Shaper download 860 -> 800: winbox ping under download med 22 -> 24, p95 33 -> 29, max 58 -> 34 ms; 816 -> 765 Mbit (one run each). Upload-only 88 Mbit with ping med 20 ms; idle 16 ms.
- 2026-11-16 barn-ap online: R7800 on OpenWrt 25.12.6 (stock web server dead after update). Barn clients went from 16-51 Mbit links to 433-867 Mbit at -45 to -60 dBm. winbox moved behind it (lan1, 1G).
- 2026-11-15 Gateway monitoring on (GUI). Netflow on. DNS serve-expired and larger caches. Hostname lcri -> elsie.
- 2026-11-15 Cut-over: Orbi to bridge mode, M8 on the WAN, BE9700 in AP mode. `hw.re.flow_control=0` after a 19-minute re1 TX watchdog stall.
