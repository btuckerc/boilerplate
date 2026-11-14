# Game streaming from winbox

winbox is the second Apollo host: a gaming PC at the Rhode Island house (Ryzen 9 9950X3D,
RTX 4090, NVENC), on the same LAN as the Mac mini. The full record is in
`~/hearth/src/game-streaming/winbox/README.md`, with its setup script and measurements.
Client settings follow `wincube-streaming.md` except the bitrates below.

## Host facts

- LAN `192.168.1.30` (wired, 1 Gbps), MAC `10:FF:E0:B9:A8:21`. Tailscale
  `winbox.tail4d5aec.ts.net`, `100.99.42.94`, unattended.
- `ssh winbox` from nous (user `brigg`, PowerShell). Keys from nous only, tailnet only.
- Wake: `wake winbox` on nous (`~/hearth/bin/wake`). It sends the magic packet from the Mac mini.
- Computer use: Claude Code MCP server `winbox` on nous (windows-mcp over HTTP, bearer key,
  nous only). Someone has to be signed in to Windows.
- Apollo: same build and display policy as wincube. NVENC P1. No host bitrate cap.

## Bitrate (measured 2026-11-14, not copied from wincube)

- At RI on the wired LAN: 400 Mbit/s UDP with 0% loss and no added delay, so the network is not
  the limit. Choose for picture quality.
- From Charlotte (RI upload to Charlotte download over Tailscale): clean to 40 Mbit/s, +3-7 ms.
  Use about 30. Base RTT is about 52 ms.
- RI's router has bufferbloat on upload (about 190 ms under load). Avoid other uploads at RI
  while streaming from away.
- Not measured yet: RI Wi-Fi clients.
