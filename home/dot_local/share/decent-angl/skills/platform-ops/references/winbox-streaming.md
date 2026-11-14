# Game streaming from winbox

winbox is the second Apollo host: a gaming PC at the Rhode Island house (Ryzen 9 9950X3D,
RTX 4090, NVENC), on the same LAN as the Mac mini. The full record is in
`~/hearth/src/game-streaming/winbox/README.md`, with its setup script and measurements.
Client settings follow `wincube-streaming.md` except the bitrates below.

## Host facts

- LAN `192.168.1.30` (wired, 2.5 Gbps), MAC `10:FF:E0:B9:A8:21`. Tailscale
  `winbox.tail4d5aec.ts.net`, `100.99.42.94`, unattended.
- `ssh winbox` from nous (user `brigg`, PowerShell). Keys from nous only, tailnet only. While a
  session is open, the Apollo watchdog holds the system awake.
- Wake: `wake winbox` (in `~/hearth/bin`, from the game-streaming repo). It sends the magic
  packet from the Mac mini and winbox is up in 6-8 s (verified). Wake from shutdown: untested.
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
- RI's Orbi has bufferbloat on upload and no SQM. Avoid other uploads at RI while streaming from
  away.
