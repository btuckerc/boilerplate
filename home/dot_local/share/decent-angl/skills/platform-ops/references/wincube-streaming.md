# Game streaming from wincube

wincube is the Apollo host (a Sunshine fork) on Windows, with an RX 9070 XT encoding over AMF.
Clients run Moonlight, or Artemis on Android. Priority: latency first, at 1080p.
The host side lives on wincube in `C:\Tools\stream\README.md`.

## Host facts

- LAN `10.77.77.100`, `wincube.home.arpa`. Wi-Fi only (Intel AX201, 5 GHz). Reserved on `clt`.
- Tailscale `wincube.tail4d5aec.ts.net`, `100.118.64.44`. Runs unattended, so it's up before login.
- Wake-on-LAN over Wi-Fi works with directed and broadcast magic packets. Apollo answers about
  4.5 s after the packet (measured 2026-11-12). MAC `a4:b1:c1:05:85:11`.
  Manual wake: `ssh nous wakeonlan -i 10.77.77.100 a4:b1:c1:05:85:11`.
- Apollo creates a virtual display for every stream, at the client's resolution and frame rate. The
  game renders at 2x the stream FPS (max 240). Each game keeps separate stream and local settings.
- Apollo caps every stream at 30 Mbit/s.

## Why these numbers

- wincube's Wi-Fi uplink (to wired nous) carries 50-60 Mbit/s at most. Queueing adds about +5 ms
  at 20 Mbit/s, +8 at 40 and +16 at 60. So 20 Mbit/s at home.
- Home upload is shaped to 21 Mbit/s on `clt`. So 12-15 Mbit/s away. Stream traffic leaving the
  house goes in the Interactive-Up queue (see the opnsense `shaper.md`).
- At 1080p, 15-20 Mbit/s of HEVC or AV1 is clean. More bitrate only adds queueing delay.
- A client used both at home and away gets one setting, 15 Mbit/s. Moonlight has no per-network
  profiles, and 15 vs 20 costs about 1 ms at home.

## Every client

1. Add the PC at home first, by `10.77.77.100`. That's how the client learns the LAN address and
   the Wi-Fi MAC it needs for Wake-on-LAN. Then also add `wincube.tail4d5aec.ts.net`. Moonlight
   merges it into the same host (same unique ID) and uses it away.
2. Pairing: Apollo gives full permissions only to the first paired client. In the Apollo web UI
   (`https://10.77.77.100:47990`, Clients), give each new client Launch Apps, Mouse Input,
   Keyboard Input and Controller Input.
3. Away and Wake: Tailscale on, with subnet routes accepted. Wake sends a directed packet to
   `10.77.77.100` through `clt`'s subnet route.
4. Settings that are the same everywhere:
   - Resolution 1080p
   - V-Sync off, frame pacing off (lowest latency)
   - HDR off
   - Hardware decoding
   - Stereo audio, no audio on the host
5. Check with the performance overlay (Ctrl+Alt+Shift+S on PC; the stats option on mobile). Look
   for network latency of a few ms at home, decode time under 5 ms, and 0 dropped frames. If frames
   drop, lower the bitrate before anything else.

## Per client

| | PC / Mac / Linux laptop | iPhone | Steam Deck (OLED) | Android TV / Android phone |
|---|---|---|---|---|
| App | Moonlight-qt | Moonlight (iOS) | Moonlight-qt (Flatpak), added to Steam for Game Mode | Artemis (Apollo's Android client), or Moonlight |
| Devices | `btc-mbp14`, `t14` | `iphone181` | `btcsd` | `btc-tv` |
| Resolution | 1920x1080 | 1920x1080 | 1920x1080 (docked or handheld) | 1920x1080 |
| FPS | Display max, up to 120 (MacBook Pro 120) | 120 on ProMotion models, else 60 | 90 (OLED panel; LCD Deck 60) | 60 (TV refresh) |
| Bitrate | 15 Mbit/s (laptops travel) | 15 Mbit/s | 20 Mbit/s at home; 15 if it travels | 20 Mbit/s |
| Codec | AV1 if the GPU decodes it (Apple M3 or newer, recent PCs), else HEVC | AV1 on A17 Pro or newer, else HEVC | Try AV1; keep it if the overlay shows hardware (VAAPI) decoding, else HEVC | HEVC (AV1 only if the TV decodes it in hardware) |
| Window | Fullscreen (exclusive on Windows) | Fullscreen | Fullscreen | Fullscreen |
| Mouse | "Optimize mouse for remote desktop" **off** for games | Controller, or touch mode relative | Steam Input / controller | Controller |
| Tailscale for away | macOS: "Use Tailscale subnets" on. Linux: `sudo tailscale set --accept-routes` | "Use Tailscale subnets" on (default) | `sudo tailscale set --accept-routes` | Home-only |
| Extra | Wired or 5 GHz | 5 GHz at home | Settings > Developer: turn **off** Wi-Fi power management (it causes latency spikes). Quick Access: frame limit off, refresh 90 Hz | Use Ethernet if the TV has it |

A Deck in handheld mode could stream at its native 1280x800. That's fewer pixels to encode and
decode, and it looks the same on a 7.4" screen. Choosing 1080p everywhere is deliberate: one
profile per game, and docking just works.
