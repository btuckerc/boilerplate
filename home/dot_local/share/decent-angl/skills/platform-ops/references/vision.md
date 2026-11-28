# Vision NAS (TrueNAS SCALE 25.10 + HexOS Local at elsie)

LincPlus LincStation N2 all-flash NAS at `elsie` (Intel N100 4C Quick Sync, 16 GB LPDDR5, 2.5GbE on Zyxel port 2, `3× 4 TB NVMe` RAIDZ1 pool `SSDs` = 7.13 TiB usable, 512 GB SK Hynix NVMe boot).

## Addressing & Exposure Boundary
- **Management IP (`10.77.78.122`, `vision.home.arpa`):** Private only (LAN / `wg0` / `elsie` Tailscale subnet router; **never** exposed on WAN).
  - TrueNAS UI/API: `http://10.77.78.122` (nginx pinned to `10.77.78.122:80/:443`).
  - HexOS Local: `https://1cb25a3d1938d46922e0484954116494bb1fde13.local.hexos.com:43705` (HTTPS) / `http://10.77.78.122:43706` (HTTP). Both `elsie` and `clt` Unbound exempt `local.hexos.com` in `privatedomain` so local TLS resolves without DNS rebind stripping.
  - SSH: `ssh vision` (`truenas_admin@10.77.78.122`, direct over `wg0` from `nous`, fleet key `~/.ssh/id_ed25519_fleet`).
- **Public HTTPS Ingress (`10.77.78.124:443` via OCI Always Free Relay `193.122.213.33`):**
  - Dedicated static alias `10.77.78.124` on `enp1s0` runs native TrueNAS custom Compose app `caddy` (`caddy:2-alpine`, `/mnt/SSDs/apps/caddy`), terminating Let's Encrypt TLS-ALPN-01 directly on `Vision` (true end-to-end TLS, zero 100 MB cap, HTTP/2 + HTTP/3 QUIC).
  - **OCI Always Free Relay (`vision-relay`, `$0/mo`, `us-ashburn-1` `AD-3`):**
    - Instance: `ocid1.instance.oc1.iad.anuwcljtno6dmzic632lp7lnbh552apxm462ilyyxzg2uthkk6tvdomaql6q` (`VM.Standard.E2.1.Micro`, Ubuntu 24.04 Minimal, `skip-source-dest-check=true`, `netfilter-persistent`/`iptables-persistent` purged).
    - VCN: `homelab-relay-vcn` (`10.88.0.0/16`, `ocid1.vcn.oc1.iad.amaaaaaano6dmzia3alpw7leicnm7c2v4cq4y6z62e5qfgur3q6cg4mzt73q`), Subnet `10.88.1.0/24` (`ocid1.subnet.oc1.iad.aaaaaaaackt2nfapkiceyctst52j52a2tcfnasvw42xvgzz4mk7rk4w4kcfq`), Security List (`ocid1.securitylist.oc1.iad.aaaaaaaankqh54skayaxnke2ygvrnib2la2fzoxsd2gxcz4ksslafwrxtgta`: TCP/UDP `443` + UDP `51820` `0.0.0.0/0`, TCP `22` restricted to `nous` + `elsie` WAN IPs).
    - Reserved Public IPv4: `193.122.213.33` (`vision-relay-ip`, `ocid1.publicip.oc1.iad.amaaaaaano6dmziafit6y4wnciyfy6u3gtihkiwtpr66y2akgjdndsyrnriq`, survives VM rebuilds).
    - Stateless forwarding: `nftables` DNATs TCP/UDP `443 -> 10.77.78.124:443` + masquerades on `wg0` (`10.77.254.5/30`, MTU `1420`, TCP MSS clamped to PMTU, BBR enabled). Zero certs or secrets live on OCI.
    - Outbound WireGuard from `elsie` OPNsense `wg1` (`10.77.254.6/30 -> 193.122.213.33:51820`, `keepalive=25`); `elsie` WAN `:443` is closed and `elsie-ddns-sync.timer` is disabled. OPNsense `wireguard` group only allows `10.77.254.5/32 -> 10.77.78.124/32:443` TCP/UDP (cannot reach `.122` mgmt or any other LAN host).
    - Agentic OCI control: `oci-auth-sync` materializes `~/.oci/{config,oci_api_key.pem}` (`0600`) from 1Password item `oci-api` (`scope: general`) for `oci` CLI (`uv tool install oci-cli`); `ssh relay` (`ubuntu@193.122.213.33`, `~/.ssh/id_ed25519_fleet`); `vision-ctl relay` checks WireGuard + WAN probes.
  - Cloudflare `weavedweb.com` DNS-only (`proxied=false`) `A` records point `photos.weavedweb.com` and `drive.weavedweb.com` to `193.122.213.33` (residential `elsie` IP is absent from DNS).
  - `elsie` and `clt` Unbound Split-DNS resolve both hostnames directly to `10.77.78.124` (full LAN / `wg0` speed).
  - Services: `https://photos.weavedweb.com` -> Immich (`:7772`, `go/photos`), `https://drive.weavedweb.com` -> Nextcloud (`:7771`, `go/drive`).

## Agentic Operations (`vision-ctl`)
HexOS Local is the human Command Deck UI layer on top of TrueNAS SCALE; automated and agentic operations run against TrueNAS's official API via `vision-ctl` (reads 1Password item `truenas-vision` via `op-secret`):
- `vision-ctl status` — OS, uptime, pool health/space, app states, HexOS Local & HTTPS probes.
- `vision-ctl apps` / `pools` / `backups` / `smart` — focused operational views.
- `vision-ctl api GET|POST|PUT|DELETE <endpoint> [json]` — direct TrueNAS `/api/v2.0/` calls.
- `vision-ctl immich status|config|jobs` and `vision-ctl immich api <METHOD> <endpoint> [json]` — Immich service-account API via 1Password item `immich-agent` (`scope: general`, field `password`, direct `http://10.77.78.122:7772/api/`). Supports both JSON and binary asset/thumbnail reads. Admin config/job tuning uses the dedicated service account promoted via `immich-admin grant-admin`; future image access uses opt-in Album / Partner Sharing with the service account.
- Never pass `-job` to non-job `midclt` calls (like `service.restart`), and always wrap SSH commands in `timeout`.

## Storage, Performance & Backups
- **ZFS tuning:** `SSDs` has `autotrim=on`, `atime=off`, `compression=lz4`; `recordsize=1M` on `SSDs/pool/{photos,drive}` and bulk `SSDs/backup/*` datasets; `recordsize=16K` on Postgres datasets `SSDs/apps/{immich-pg,nextcloud-pg}`.
- **Apps:** `immich` (`v3.4.2`, PG18 + VectorChord, Quick Sync `h264_qsv` + OpenVINO `v3.4.1-openvino` iGPU ML on `/dev/dri/renderD128`, `externalDomain=https://photos.weavedweb.com`, `publicUsers=false`), `nextcloud` (`35.0.3`, PG18, 5-min cron, 16 GiB upload cap), `hexos` (`1.4.10`, Local Command Deck), `caddy` (`2-alpine`, custom Compose; strips `Server`/`Via`/`X-Powered-By`, no ACME personal email, `Referrer-Policy: same-origin`).
- **Maintenance:** Weekly `SSDs` scrub (Sun 00:00); 5 recursive ZFS snapshot tasks (`SSDs/pool` hourly/daily/weekly, `SSDs/backup` & `SSDs/apps` daily); NVMe SMART weekly short & monthly extended TrueNAS cronjobs.
- **Backups (3-2-1, fail-closed):**
  - `02:30` Vision cronjob: `/mnt/SSDs/backup/vision-db/run-vision-db-backup.sh` (atomic `pg_dumpall` + TrueNAS config DB + SHA-256 manifest, 14d retention).
  - `03:30` `nous` `vision-offsite-backup.timer`: pulls `vision-db` + `pool/photos` originals over `wg0` to `/srv/models/backups/vision` (`909 GiB` volume, pre-flight delta + `100 GiB` reserve floor, atomic rolling 7-day `--link-dest` snapshots).
  - `04:00` Vision cronjob: `/mnt/SSDs/backup/vision-db/sync-macmini-backups.sh` pulls `macmini`'s `srv/restic`, non-media `Backups`, `vault`, and `photos` staging over 1GbE LAN (fail-closed on `/Volumes/webweaver-HD` APFS UUID + sentinel; excludes cold `Media/` and `Docker.raw`) and pushes Copy 2 (`vision-db` + `pool/photos` originals) back to `macmini:/Volumes/webweaver-HD/Backups/vision-mirror/`.
  - `04:30` `nous` `nous-git-mirror.timer`: mirrors all canonical bare repos to both `macmini` and `Vision:/mnt/SSDs/backup/nous-git`.
- **Cloudflare Access (`weavedweb.com`):** Browser-only internal/admin subdomains (`sonarr`, `radarr`, `lidarr`, `bazarr`, `prowlarr`, `qb`, `tautulli`, `dash`, `home`, `pi`, `f1`, `pinchflat`, `tubesync`) are gated by Access app `weavedweb-admin` (`716a621d-2329-4046-9c7e-b786b12b7b9e`, policy `Only Tucker`), matching `grafana` and `teslamate`. Family & native-app endpoints (`photos`, `drive`, `plex`, `tv`, `requests`, `list`, `join`, `abs`, `audiobooks`, `lib`, `booklist`, `vault`, `notes`, `pebble`) remain directly accessible.
