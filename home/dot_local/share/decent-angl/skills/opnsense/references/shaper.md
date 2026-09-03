# WAN traffic shaper

Live objects on `clt`. Read this before changing pipes, queues, or Steam-vs-LAN
behavior.

## Topology

- Firewall: OPNsense `clt` at `10.77.77.1`. No Wi-Fi on this box.
- AP: TP-Link Archer BE9700 `be9700` at `10.77.77.111`.
- Steam hog: `wincube` at `10.77.77.100`, wired.
- Steam Deck: `btcsd` at `10.77.77.185`, Wi-Fi via BE9700, Tailscale
  `100.76.38.59`. LAN SSH to the Deck is closed. Tailscale SSH works after
  `tailscale ssh` auth.

WAN is Spectrum on `re1`. LAN is `re0` `10.77.77.0/24`.

## Live recipe, 2026-08-31

Do not combine FQ-CoDel on the pipe with a host mask on the queue. That was
tried. It does not isolate hosts.

```
pipe 10000 config bw 85Mbit/s type wf2q+
pipe 10001 config bw 21Mbit/s type wf2q+
queue 10000 config pipe 10000 mask dst-ip /32 weight 100 codel ecn
queue 10001 config pipe 10001 mask src-ip /32 weight 100 codel ecn
```

UUIDs:

- Download pipe `c3e2f401-ec6c-4169-a931-d98a80727885`
- Upload pipe `10b63316-606f-46b5-bd4e-4af2f0913cb5`
- Download-Queue `a3093f61-b19c-4bd1-b9c5-05fc178976d9` mask `dst-ip`
- Upload-Queue `2bf2dbfd-1365-4f46-b0ed-a20f426fe2bd` mask `src-ip`
- Rules: WAN `in` -> Download-Queue, WAN `out` -> Upload-Queue, proto `ip`,
  any/any.

GUI pipe names still say `Download-FQCoDel` / `Upload-FQCoDel`. Live scheduler
is `wf2q+`. Ignore the names.

Pipe mask stays `none`. A mask on the pipe clones the full bandwidth per IP.
That oversubscribes. It is a cap recipe, not a share recipe.

IPv4 only. `dst-ip` / `src-ip` do not isolate IPv6. Steam in these captures
was IPv4 `*.valve.net`.

Proof file after reconfigure: `opnsense-ssh 'cat /usr/local/etc/dnctl.conf'`.
API `saved` is not active. `opnsense-api post trafficshaper/service/reconfigure '{}'`
needs a JSON body. Empty POST returns HTTP 400.

## Why FQ-CoDel starved the Deck

Steam opens many parallel HTTPS sessions to Valve CDNs. FQ-CoDel is fair per
TCP 5-tuple, not per LAN host. Ten Steam flows vs one Deck or Mac flow means
Steam takes most of the 85 Mbit pipe. The Deck saw 250 kbps while WAN was
full. Ping stayed fine. This is not a modem failure and not a duplex failure.

Measured 2026-08-31, Steam filling, this Mac idle:

- WAN `re1` MAC-row rx about 94 to 116 Mbit/s
- LAN `re0` MAC-row tx pinned at 85.8 Mbit/s with the 85 Mbit pipe
- Captive portal empty. No per-host limiter.

Do not use the IPv4 address rows on `getInterfaceStatistics`. Those counters
barely move. Use:

- `[WAN] (re1) / 70:70:fc:0b:bb:a4` for ISP arrival
- `[LAN] (re0) / 70:70:fc:0b:bb:a3` for shaper output

Queue mask `dst-ip` with the pipe still `fq_codel` was a no-op for host
fairness. Download-Queue buckets went 1 to 256, so the mask was installed.
This Mac still got 1.1 Mbit/s against Steam. FQ-CoDel kept hashing every
flow.

WFQ plus the same mask plus CoDel on the queues:

- LAN tx still 85.81 Mbit/s, minus 0.05 percent vs the 85.85 baseline
- This Mac curl 38.4 / 39.0 / 39.3 Mbit/s while Valve IPs stayed top talkers
- Ping under that Steam load 31.7 ms avg, 0 percent loss, vs 28.5 ms under
  FQ-CoDel

One host idle still fills the whole pipe. This is share, not a Steam cap.

Official docs:

- Per-flow AQM: https://docs.opnsense.org/manual/how-tos/shaper_bufferbloat.html
- Per-host share: https://docs.opnsense.org/manual/how-tos/shaper_share_evenly.html
- Per-host cap: https://docs.opnsense.org/manual/how-tos/shaper_limit_per_user.html
- Weights, mask must be empty: https://docs.opnsense.org/manual/how-tos/shaper_prioritize_using_queues.html

## Two hosts cannot each get 85

The 38 to 40 Mbit/s result is 85 / 2. Conservation. A second bulk WAN
downloader cannot also get 85 or 100 on this circuit.

WAN NIC rx sits around 114 to 119 Mbit/s while LAN tx sits around 85 to 90.
ISP download is about 100 to 120 Mbit, not gigabit. Raising the pipe from 85
to 100 would give a lone host about 100, and two hosts about 50 each. It does
not produce 85 concurrent. Do not raise the pipe without a loaded ping test.
If avg RTT jumps past about 80 ms or loss appears, put it back to 85.

Paths that can put a second device in the 85 to LAN-gigabit range while
wincube Steam is "running":

1. Steam is idle on WAN. Already true. Lone host LAN tx 85.8 Mbit/s.
2. Steam Deck pulls a depot wincube already has. Steam Downloads, Game File
   Transfer over Local Network. That traffic never hits WAN.
3. Lancache for repeat Steam content. First fill still uses WAN. Later fills
   are LAN. Needs a cache host, disk, and DNS for
   `lancache.steamcontent.com`. Do not put this on `clt`. Do not hijack
   Unbound without a dedicated plan.
4. Weighted queues, mask none, preferred LAN IPs in a high-weight queue,
   everyone else low. Preferred hosts can approach the full pipe by starving
   wincube. That is a policy change. Do not do it unless asked. FQ-CoDel
   ignores weights. Stay on WFQ if you add weights.

Do not cap Steam in the client as the network fix. Do not split SSIDs. Do
not reboot the Spectrum modem for this. Do not force NIC speed/duplex on
wincube. OPNsense LAN is 1000baseT. wincube was already filling 85 Mbit.

## Change checklist

1. `opnsense-api status` with `tls_pin=ok` and `api=ok`.
2. Snapshot LAN tx on the `re0` MAC row, 4 to 5 samples of 4 s, while noting
   whether Steam is filling.
3. `set_pipe` / `set_queue`, then `post trafficshaper/service/reconfigure '{}'`.
4. `cat /usr/local/etc/dnctl.conf` and `search_queues`.
5. Repeat LAN tx. Revert if the lone-host fill drops more than 3 to 4 percent
   while Steam is still the top talker.
6. For fairness, curl `-4` a 20 MB Cloudflare download from a second LAN host
   during that Steam fill. Expect about half the pipe.

Rollback to the failed FQ-CoDel host-share attempt is not useful. Rollback
to pre-incident is pipe `type fq_codel`, queue mask `none`, queue
`codel_enable=0`. That restores Steam hogging.
