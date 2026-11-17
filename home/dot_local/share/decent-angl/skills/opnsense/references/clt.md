# clt site (Charlotte)

## Summary

Tucker's Charlotte home, LAN `10.77.77.0/24`, Spectrum internet. nous (this AI host) and
wincube (Apollo host) live here. Single AP. The router predates the `sites.md` address
convention for hosts.

## Inventory

| Device | Role | IP | MAC | Access from nous | Secret | Writes |
|---|---|---|---|---|---|---|
| clt (M8) | OPNsense router | `10.77.77.1` `router.home.arpa`; Tailscale `clt` `100.109.139.83` | - | `opnsense-api` (default target), `opnsense-ssh` | `opnsense-api`, `opnsense-agent-ssh` | API, shell |
| be9700 | AP, TP-Link Archer BE9700 v1.0 | `10.77.77.111` | `68:7f:f0:76:df:0d` | `tplinkrouterc6u`, `netwatch` | `~/.local/share/decent-angl/secrets/be9700.env` on nous | untested, `tplink-archer.md` |
| gs305e | NETGEAR GS305E switch (5x 1G) | `10.77.77.112` | `28:94:01:8d:30:48` | - | - | - |
| nous | AI host | `10.77.77.157` | `58:11:22:b6:4e:90` | local | - | - |
| wincube | Apollo host, Wi-Fi only | `10.77.77.100` | `a4:b1:c1:05:85:11` (real Wi-Fi MAC) | `ssh` (see `platform-ops`) | - | - |

## Access

- `opnsense-api` targets `https://10.77.77.1` with the TLS pin by default. The GUI/API does
  not listen on the Tailscale address. Off-LAN access needs the advertised `10.77.77.0/24`
  route approved in the Tailscale admin console.
- Shell user `agent` (wheel, uid 2001), keys only; sshd on LAN only, no password, no root.
  `ssh clt` is Tailscale SSH and may prompt; unattended shell is `opnsense-ssh` (fleet key
  steps in `SKILL.md`). `opnsense-ssh 'id -un; hostname'` prints `agent`, `router.home.arpa`.
- Tailscale plugin: name `clt` (never reuse), advertises `10.77.77.0/24`, `acceptDNS` off so
  Unbound stays LAN DNS. Do not open 22/443 on WAN.

## Router

- dnsmasq DHCP range `.100-.199`, domain `home.arpa`; host entries be9700 .111, gs305e .112,
  nous .157, wincube .100. Unbound forwards `home.arpa` and `77.77.10.in-addr.arpa` to
  dnsmasq on 53053 (design in `SKILL.md`).
- Shaper: WFQ pipes 85/21 Mbit with per-host queues and Interactive queues; recipe and the
  Steam multi-flow failure in `shaper.md`.
- Netflow local only (`SKILL.md`). `netwatch` (`~/hearth/src/netwatch`) sampled WAN, per-host
  rates, shaper drops and AP client RSSI every minute; its timer is off since 2026-11-17 (each
  run logged in to the BE9700 and sent ping bursts). Re-enable: `systemctl --user link
  ~/hearth/src/netwatch/systemd/netwatch.service && systemctl --user enable --now
  ~/hearth/src/netwatch/systemd/netwatch.timer`.

## Wi-Fi

Single AP; plan row in `wifi.md` (`Craig_CLT` on 2.4/5 GHz, `Craig_CLT_6G`).

- Wake-on-LAN for wincube over Wi-Fi: static ARP neighbour for `10.77.77.100` /
  `a4:b1:c1:05:85:11` (Interfaces > Neighbors, `interfaces/neighbor_settings`). Moonlight
  off-LAN sends a directed magic packet to `10.77.77.100` through the `clt` route, and the
  sleeping host must still resolve. Verified 2026-11-12: directed and broadcast packets wake
  wincube (WoWLAN); Apollo answers 4.5 s later. Manual: `wakeonlan -i 10.77.77.100 a4:b1:c1:05:85:11`.
- Windows MAC randomization is off for this SSID on wincube, so its reservation holds.

## Switch

GS305E, unmanaged in practice (no agent access recorded).

## Open items

| Item | Who | Notes |
|---|---|---|
| BE9700 firmware update offered (2026-11-16) | user decides when | `netwatch/ap_upgrade.py` installs it at a quiet time. |
| Store the BE9700 password in 1Password (`be9700-clt`) | user | Only a local file today. |
| `netwatch` repo has no commits | owner of netwatch | Code exists only in the working tree. |

## Change log

- 2026-11-17 `netwatch` timer stopped and disabled on nous (no per-minute AP logins or ping bursts); code kept.

- 2026-11-16 Read-only Wi-Fi audit: AP firmware 1.1.1 Build 20260113; 2.4 GHz ch 1 fixed, 5 GHz auto (149), 6 GHz auto (37) 160 MHz; Smart Connect off; OFDMA/MU-MIMO on; TWT off.
- 2026-11-12 wincube Wake-on-LAN over Wi-Fi verified with real sleep cycles.
- 2026-11-11 Interactive queue per host added to the shaper (`shaper.md`).
