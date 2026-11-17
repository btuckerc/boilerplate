# Game streaming from winbox

winbox is the second Apollo host: a gaming PC in the barn at the Rhode Island house (Ryzen 9
9950X3D, RTX 4090, NVENC), on the same LAN as the Mac mini. The full record is in
`~/hearth/src/game-streaming/winbox/README.md`, with its setup script and measurements.
Client settings follow `wincube-streaming.md` except the bitrates below.

## Host facts

- LAN `10.77.78.120` (dnsmasq reservation on elsie), MAC `10:FF:E0:B9:A8:21`. Wired at 1 Gbps
  into barn-ap `lan1` (OpenWrt R7800), which bridges in hardware to the barn cable and switch
  port 5; it was 2.5 Gbps straight into the switch before 2026-11-16. Network facts: `opnsense`
  skill, `references/elsie.md`. Tailscale `winbox.tail4d5aec.ts.net`, `100.99.42.94`,
  unattended; path from nous direct via `70.175.223.206:41641` (verified 2026-11-16).
- NIC (Realtek 2.5GbE): EEE, Green Ethernet, flow control, interrupt moderation and power
  saving all off. Latency to elsie med 0.35 ms, p95 0.64 ms. Windows firewall drops inbound
  ping (Public profile), so measure from winbox outwards.
- `ssh winbox` from nous (user `brigg`, PowerShell). Keys from nous only, tailnet only. While a
  session is open, the Apollo watchdog holds the system awake.
- Wake: `wake winbox` (in `~/hearth/bin`, from the game-streaming repo). It sends the magic
  packet from the Mac mini and winbox is up in 6-8 s (verified). Wake from shutdown: untested.
  Same-LAN wake must be broadcast: asleep, the NIC does not answer ARP (2026-11-17, ARP offload
  on). Moonlight broadcasts (255.255.255.255, subnet broadcast, ff02::1) and has the right MAC;
  a broadcast from barn-ap's bridge woke it in 8 s. Never sleeps on its own (AC standby 0).
  Off-site: Moonlight's unicast to `10.77.78.120` goes through elsie's Tailscale route and its
  static neighbor entry (verified 6 s); the client must accept subnet routes.
- Pairing: `apollo-pair winbox pin PIN NAME` (Moonlight shows the PIN), or
  `apollo-pair winbox otp NAME` for Artemis. It grants launch, input and clipboard.
  wincube needs SSH first (`winbox/setup/wincube-ssh-setup.cmd`).
- Computer use: Claude Code MCP server `winbox` on nous (windows-mcp over HTTP, bearer key,
  nous only). Someone has to be signed in to Windows.
- Balanced power plan on purpose: the X3D V-Cache optimizer needs core parking.

## Bitrate (measured 2026-11-14, not copied from wincube)

- At RI, wired: not limited by the network (0% loss to 400 Mbit/s). 1080p: 50-80.
- At RI, Wi-Fi (Orbi, good 5 GHz signal): clean to 150 Mbit/s. Use up to 100.
- In Charlotte (RI upload to Charlotte download over Tailscale): clean to 40 Mbit/s, +3-7 ms.
  Use about 30. Base RTT is about 52 ms.
- Since 2026-11-15 RI runs OPNsense (elsie) with FQ-CoDel SQM, 800/90 Mbit since 2026-11-16.
  winbox ping to 1.1.1.1: idle about 16 ms; med 20 ms under full upload, med 24 / max 34 ms
  under full download. Other uploads share the 90 Mbit fairly with a stream, so keep remote
  stream bitrates well under it. Outbound NAT has static port 41641 for winbox and
  endpoint-independent UDP mapping, so Tailscale paths from away are direct. The bitrates
  above were measured on the old Orbi network. Re-measure.
