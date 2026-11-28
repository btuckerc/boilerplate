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
- Tailscale plugin: name `clt` (never reuse), listen port `41642` (WAN `41641` belongs to
  `nous`'s static outbound NAT), advertises `10.77.77.0/24`, `acceptDNS` off so Unbound stays
  LAN DNS. Do not open 22/443 on WAN.

## Router

- dnsmasq DHCP range `.100-.199`, domain `home.arpa`; host entries be9700 .111, gs305e .112,
  nous .157, wincube .100. Unbound forwards `home.arpa` and `77.77.10.in-addr.arpa` to
  dnsmasq on 53053 (design in `SKILL.md`).
- DHCP Option 121 (RFC 3442 classless static route, UUID `08f67009-5d72-4df1-a48c-83e87b88c8ab` on `lan`):
  `0.0.0.0/0,10.77.77.1,10.77.78.120/32,10.77.77.1,10.77.78.122/32,10.77.77.1,10.77.78.124/32,10.77.77.1`. Pushes `/32` host routes for `winbox` (.120), `vision` (.122), and `vision-ingress` (.124) via `10.77.77.1`
  so macOS/iOS clients with Tailscale `accept-routes=true` route them over `wg0` via longest-prefix
  match while preserving the `0.0.0.0/0` default gateway.
- Unbound `privatedomain`: `home.arpa,plex.direct,local.hexos.com`. Host overrides: `valheim.angl.gg -> 10.77.77.157`, `vision.home.arpa -> 10.77.78.122` (`b0cebe83`), `photos.weavedweb.com -> 10.77.78.124` (`95749f1c`), `drive.weavedweb.com -> 10.77.78.124` (`9e0d4bff`).
- Site-to-site kernel WireGuard (`if_wg.ko`, `wg0`, MTU `1420`, UDP `51820`): server `s2s-elsie`
  (UUID `f118a4a6-c00d-4be2-baba-1118f6f50256`, `10.77.254.1/30`), peer `elsie-s2s`
  (UUID `6f1a8cf5-c639-45ea-af22-5eec036e9f98`, endpoint `70.175.223.206:51820`, `keepalive=25`,
  allowed `10.77.254.2/32,10.77.78.0/24`). Firewall rules: WAN UDP `51820` pass
  (`f6fb716c-6273-4e73-b1af-2cde99aed7b7`), `wireguard` group pass `10.77.78.0/24 -> 10.77.77.0/24`
  (`fda83bc2-7bb1-49ee-b8c9-92cc3497e171`), transit ICMP (`4fc2ebd9-4ae7-401d-aed1-d6193e01cb25`).
  UDP `51820` matches the `Interactive-Down`/`Interactive-Up` WFQ queues (`proto=udp`, port `!= 443`).
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

- 2026-11-28 Added Unbound `privatedomain` `plex.direct,local.hexos.com`, Split-DNS overrides `photos.weavedweb.com`/`drive.weavedweb.com` -> `10.77.78.124` (`95749f1c`, `9e0d4bff`), and `10.77.78.124/32` to DHCP Option 121 (`08f67009`). Verified valid HTTPS to both over `wg0`.
- 2026-11-28 Added Unbound host override `vision.home.arpa -> 10.77.78.122` (UUID `b0cebe83-f93b-4eb4-bb4b-7703ee0f2759`) and added `10.77.78.122/32,10.77.77.1` to DHCP Option 121 (`08f67009-5d72-4df1-a48c-83e87b88c8ab`) so `clt` clients route `Vision` directly over `wg0`. Verified `dig +short @10.77.77.1 vision.home.arpa` -> `10.77.78.122` and HTTP 200 to `Vision` `:7772`/`:7771`/`:43706` over `wg0`.
- 2026-11-26 Site-to-site kernel WireGuard (`if_wg`, `wg0`, UDP `51820`, MTU `1420`, `10.77.254.1/30` <-> `elsie` `10.77.254.2/30`) + RFC 3442 DHCP Option 121 (`08f67009-5d72-4df1-a48c-83e87b88c8ab`: `0.0.0.0/0,10.77.77.1,10.77.78.120/32,10.77.77.1`) enabled hitlessly. Verified DF `1392 B` payload (`1420 B` IP, 0% loss, `47.5-50.2 ms` to `10.77.78.121`), raw DHCP OFFER wire bytes, and 4-rep ABBA `wire_bench` (`winbox -> nous`, 30 Mbps + 256 KiB IDR): at 120 FPS frame-complete RTT dropped `55.67 -> 54.42 ms` p50 (`-1.25 ms`, 4/4 non-overlapping), `77.07 -> 71.01 ms` p95 (`-6.06 ms`), `128.68 -> 106.05 ms` p99 (`-22.63 ms`), IDR max `91.15 -> 84.52 ms`, completion `98.80% -> 99.64%`; at 240 FPS p50 `52.85 -> 51.82 ms`, p99 `128.41 -> 123.58 ms`, IDR max `115.69 -> 104.34 ms`, completion `98.91% -> 99.45%`.
- 2026-11-24 Tailscale `listenPort` moved `41641` -> `41642` (avoiding collision with `nous`'s WAN static NAT `41641`): `btc-mbp14` -> `clt` switched from `DERP(nyc)` to direct `98.26.202.87:41642`, `10.77.77.1` ping dropped from med 261 / max 606 ms to med 57.3 / max 64.3 ms (`nous` kept direct path at 53 ms).
- 2026-11-17 `netwatch` timer stopped and disabled on nous (no per-minute AP logins or ping bursts); code kept.

- 2026-11-16 Read-only Wi-Fi audit: AP firmware 1.1.1 Build 20260113; 2.4 GHz ch 1 fixed, 5 GHz auto (149), 6 GHz auto (37) 160 MHz; Smart Connect off; OFDMA/MU-MIMO on; TWT off.
- 2026-11-12 wincube Wake-on-LAN over Wi-Fi verified with real sleep cycles.
- 2026-11-11 Interactive queue per host added to the shaper (`shaper.md`).
