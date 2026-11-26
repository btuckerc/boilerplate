# Wi-Fi standard and channel plans

Applies to every site. Site pages link here; device pages say how to set each item.

## Standard

| Setting | Value | Why |
|---|---|---|
| SSID | One name per site on 2.4 and 5 GHz, identical on every AP. 6 GHz may have its own name. | Clients only roam between APs with the same name, band set and password. |
| Security | WPA2/WPA3 mixed (OpenWrt `sae-mixed`, TP-Link `psk_sae`) on every AP. | The R7800 (Wi-Fi 5) and old clients need WPA2; mismatched security between APs breaks roaming. |
| AP mode | Bridge/AP mode only. The router (OPNsense) does DHCP, DNS, NAT and shaping. | A second NAT or DHCP server hides clients and splits the network. |
| Uplink | Ethernet only. | Wireless backhaul halves airtime and adds latency. |
| 2.4 GHz | 20 MHz on 1, 6 or 11. Lower power than 5 GHz on multi-AP sites (barn-ap 20 dBm). | 40 MHz has no room; high 2.4 power pulls distant clients onto a weak AP. |
| 5 GHz | 80 MHz on non-DFS blocks: 36-48 or 149-161. Neighbouring APs on different blocks. No 160 MHz (it needs DFS 52-64; radar forces channel drops). | Two non-overlapping 80 MHz blocks without DFS waits. |
| Channels | Fixed on multi-AP sites. Auto only on a single-AP site. | Auto can move an AP onto its neighbour's block. |
| Roaming aids | 802.11k + 802.11v on OpenWrt APs. No 802.11r across vendors. | k/v help clients find the next AP; FT needs both APs to share keys. |
| Queueing | Airtime fairness on. OpenWrt keeps mac80211 AQL/FQ-CoDel (default). | Stops one slow client from bloating everyone's latency. The router shaper cannot reach an AP's radio queue. |

## Channel plans

| Site | AP | Location | 2.4 GHz | 5 GHz | 6 GHz | Notes |
|---|---|---|---|---|---|---|
| clt | be9700 (Archer BE9700 v1.0) 10.77.77.111 | house | ch 1, 20 MHz | auto (149), 80 MHz | `Craig_CLT_6G`, auto (37), 160 MHz | single AP, SSID `Craig_CLT`, Smart Connect off |
| elsie | be9700 (reports Archer BE600 v1.0) 10.77.78.111 | house | ch 11, 20 MHz | ch 149, 80 MHz | `Craig Wifi 6G`, auto (69), 320 MHz | SSID `Craig WiFi`, Smart Connect on. Pinned 2026-11-26 |
| elsie | barn-ap (R7800, OpenWrt) 10.77.78.110 | barn | ch 1, 20 MHz, 20 dBm | ch 36, 80 MHz, 23 dBm | none | 802.11k/v on |

Values read from the devices on 2026-11-16. Re-read before relying on an `auto` channel.

## Sticky clients (multi-AP sites)

A client picks its AP; neither AP can move it. Clients roam only when their current
signal falls below their own threshold (about -70 to -75 dBm for Apple devices).

- In the elsie barn the house BE9700 still reaches -72 dBm on 5 GHz and -67 to -82 dBm on
  2.4 GHz, so a barn client that joins the house AP may stay there.
- Restarting an AP's radios (`wifi reload`, a channel change, a reboot) sends its clients
  to the other AP, and stationary ones (HomePods, TVs, cameras) stay. Change radios rarely,
  and afterwards check where clients ended up.
- Fix one stuck client by toggling its Wi-Fi or power-cycling it. Do not add a blocklist
  on the far AP.
- Find which AP a client is on: OpenWrt `iwinfo <iface> assoclist`, TP-Link client list
  (`tplink-archer.md`), and map MACs to names with the router's dnsmasq leases.

## Measuring

- Signal: RSSI from the AP's client list. Under -70 dBm means a roaming candidate;
  under -80 dBm is unusable.
- Neighbours: scan from an OpenWrt AP (`iw dev phy0-ap0 scan ap-force`, or
  `iwinfo <iface> scan`). ath10k often returns nothing on the first try, so retry.
- Latency under load: one wired host saturates the line (`networkQuality -c`, `-u` for
  download only, `-d` for upload only) while the client under test pings 1.1.1.1
  (Windows: `ping -n 30 1.1.1.1`) and you record median, p95 and max. Compare with
  the idle numbers. Run each setting at least once; note when it was a single run.
- Wi-Fi throughput: `iperf3` (installed on barn-ap) between the AP and a client,
  so the internet is not in the path.
