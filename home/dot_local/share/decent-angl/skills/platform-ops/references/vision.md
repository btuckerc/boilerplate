# Vision NAS (TrueNAS SCALE 25.10 + HexOS Local at elsie)

LincPlus LincStation N2 all-flash NAS at `elsie` (Intel N100 4C Quick Sync, 16 GB LPDDR5, 2.5GbE on Zyxel port 2, `3× 4 TB NVMe` RAIDZ1 pool `SSDs` = 7.13 TiB usable, 512 GB SK Hynix NVMe boot).

## Addressing & Exposure Boundary
- **Management IP (`10.77.78.122`, `vision.home.arpa`):** Private only (LAN / `wg0` / `elsie` Tailscale subnet router; **never** exposed on WAN).
  - TrueNAS UI/API: `http://10.77.78.122` (nginx pinned to `10.77.78.122:80/:443`).
  - HexOS Local: `https://1cb25a3d1938d46922e0484954116494bb1fde13.local.hexos.com:43705` (HTTPS) / `http://10.77.78.122:43706` (HTTP). Both `elsie` and `clt` Unbound exempt `local.hexos.com` in `privatedomain` so local TLS resolves without DNS rebind stripping.
  - SSH: `ssh vision` (`truenas_admin@10.77.78.122`, direct over `wg0` from `nous`, fleet key `~/.ssh/id_ed25519_fleet`).
- **Public HTTPS Ingress (`10.77.78.124:443`):** Dedicated static alias on `enp1s0` running native TrueNAS custom Compose app `caddy` (`caddy:2-alpine`, `/mnt/SSDs/apps/caddy`).
  - `elsie` OPNsense DNAT forwards WAN TCP+UDP `443 -> 10.77.78.124:443`.
  - Cloudflare `weavedweb.com` DNS-only (`proxied=false`) `A` records point `photos.weavedweb.com` and `drive.weavedweb.com` directly to `elsie`'s WAN IP (no 100 MB Cloudflare Free upload cap; kept synced by hourly `elsie-ddns-sync.timer` on `nous`).
  - `elsie` and `clt` Unbound Split-DNS resolve both hostnames directly to `10.77.78.124` (full LAN / `wg0` speed, valid Let's Encrypt TLS via Caddy TLS-ALPN-01).
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
- **Apps:** `immich` (`v3.4.2`, PG18 + VectorChord, Quick Sync `/dev/dri` readable by UID `3002`), `nextcloud` (`35.0.3`, PG18, 5-min cron, 16 GiB upload cap), `hexos` (`1.4.10`, Local Command Deck), `caddy` (`2-alpine`, custom Compose).
- **Maintenance:** Weekly `SSDs` scrub (Sun 00:00); 5 recursive ZFS snapshot tasks (`SSDs/pool` hourly/daily/weekly, `SSDs/backup` & `SSDs/apps` daily); NVMe SMART weekly short & monthly extended TrueNAS cronjobs.
- **Backups (3-2-1, fail-closed):**
  - `02:30` Vision cronjob: `/mnt/SSDs/backup/vision-db/run-vision-db-backup.sh` (atomic `pg_dumpall` + TrueNAS config DB + SHA-256 manifest, 14d retention).
  - `03:30` `nous` `vision-offsite-backup.timer`: pulls `vision-db` + `pool/photos` originals over `wg0` to `/srv/workspaces/backups/vision/` (50 GiB free-space floor on `/srv/workspaces`).
  - `04:00` Vision cronjob: `/mnt/SSDs/backup/vision-db/sync-macmini-backups.sh` pulls `macmini`'s `srv/restic`, non-media `Backups`, `vault`, and `photos` staging over 1GbE LAN (fail-closed on `/Volumes/webweaver-HD` APFS UUID + sentinel; excludes cold `Media/` and `Docker.raw`) and pushes Copy 2 (`vision-db` + `pool/photos` originals) back to `macmini:/Volumes/webweaver-HD/Backups/vision-mirror/`.
  - `04:30` `nous` `nous-git-mirror.timer`: mirrors all canonical bare repos to both `macmini` and `Vision:/mnt/SSDs/backup/nous-git`.
