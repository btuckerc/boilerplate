# OpenWrt dumb AP (NETGEAR R7800 and similar)

Used for: elsie `barn-ap`. Site facts (IP, SSID, channels) are on the site page and in
`homenet/openwrt-ap/sites/<site>-<ap>.env`; this page is how to build, flash and run one.

## Why OpenWrt

The R7800's stock firmware (last release V1.0.2.92, 2022) left the web server dead after an
update; factory resets and TFTP reflashes of V1.0.2.92 and V1.0.2.90 did not fix it, so it
could not be put in AP mode. OpenWrt 25.12 supports it (ipq806x, DSA ports `lan1-4`, `wan`),
gets security updates, and supports WPA2/WPA3 mixed and 802.11k/v.

## Build

`~/hearth/src/homenet/openwrt-ap/build.sh openwrt-ap/sites/<site>-<ap>.env`

- Verifies OpenWrt's signed `sha256sums` with the openwrt/keyring repo, then the ImageBuilder.
- Secrets in order: env `AP_PSK`/`AP_ROOT_HASH`, 1Password (`AP_PSK_ITEM`, `AP_ROOT_ITEM`),
  then the live AP over SSH (`AP_LIVE_SSH`). Output `out/<host>/` (700): factory `.img`
  and `sysupgrade.bin`. Both contain the Wi-Fi key and root hash.
- The image boots configured: static IP, all ports in `br-lan`, DHCP/RA/firewall off
  (done first in `/etc/uci-defaults/99-dumb-ap`), SSH key-only, packet steering on.
  Wi-Fi is set by `/etc/rc.local` on first boot, because radios appear only after ath10k loads.
- To change a setting permanently, change the site `.env` and rebuild, then also apply it
  live with `uci` so the device and the recipe agree.

## Flash from stock or a dead firmware (TFTP recovery)

`homenet/r7800-recovery/Flash-Netgear.ps1` on a Windows PC wired to a LAN port, uplink
unplugged: `-Image <factory.img> -Sha256 <hash> -WatchIp <AP IP> -TempIp <free IP in that subnet>`.
It sets the PC to 192.168.1.10, waits while you power on holding Reset until the Power LED
flashes white, uploads, then watches the AP's own IP. Plug in the uplink only when it says
SUCCESS. STOP means the AP booted with OpenWrt defaults (192.168.1.1 with a DHCP server):
keep it off the LAN and reflash. The bootloader accepts both stock Netgear and OpenWrt factory
images (same `netgear-dni` header, HW ID `29764958+0+128+512+4x4+4x4+cascade`).

## Upgrade

Rebuild with the new `OWRT_VERSION`, copy the sysupgrade image to the AP, then
`sysupgrade -v /tmp/<image>.bin` (keeps settings). The image's first-boot scripts are
written to be idempotent, so it does not matter whether OpenWrt runs them again after the
upgrade (unverified which it does). Barn Wi-Fi is down about 3 minutes, and clients may
stick to the house AP afterwards (`wifi.md`).

## Operate

- Shell: `ssh <host>` (site page has the alias). Web UI (LuCI): `http://<AP IP>`, user root,
  password in the site's secret item or file.
- Clients: `iwinfo phy0-ap0 assoclist` (5 GHz) and `phy1-ap0` (2.4 GHz). Map MACs with the
  router's leases.
- Radio state: `iwinfo phy0-ap0 info`. Settings: `uci show wireless`.
- Logs: `logread | grep hostapd`. Timestamps before NTP sync show the build date.
- Ports: `ethtool lan1`, `ethtool -S wan`, `ethtool --show-eee wan`. Traffic between wired
  ports is switched in the QCA8337 and never hits the CPU counters.
- Backup: `ssh <host> 'sysupgrade -b -' > <host>-$(date +%F).tar.gz` (contains secrets: 0600).

## Gotchas

- `wifi reload` and radio changes kick every client for about 10 s; see sticky clients in `wifi.md`.
- ath10k `scan` from the AP often returns 0 results on the first try.
- `stat` is missing (BusyBox); use `ls -ld`.
- Do not run `wifi config` on a configured AP: it only adds radios, but `wifi` without
  arguments restarts them.
