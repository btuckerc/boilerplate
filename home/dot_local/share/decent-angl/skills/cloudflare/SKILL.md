---
name: cloudflare
description: Use for Cloudflare zones, DNS, Workers, R2, D1, KV, tunnels, or any Cloudflare API task via the cf CLI.
---

# Cloudflare

Use `cf` (Cloudflare CLI, beta, pinned in mise as `npm:cf`) for every
Cloudflare task instead of raw `api.cloudflare.com` calls or `flarectl`.
Exception: a project with `wrangler.toml`/`wrangler.jsonc` and no
`cloudflare.config.ts` keeps using Wrangler for dev/build/deploy.

## Account

- One account: `btuckerc-flare` (`d0e2dc9e20c4611c2d54c3387a5c9c46`).
- Zones: `angl.gg`, `btuckerc.dev`, `cluewell.app`, `trivrdy.com`,
  `weavedweb.com`, `webyl.app`. Re-check with `cf zones list`.
- Wrangler projects: `herdwick/relay`, `tinycast/website`.

## Auth

- Per host: `cf auth login --no-browser`, then the user approves the printed
  device code. Credentials live in `~/.config/cloudflare/`; machine-local, never
  in Git or chezmoi. Check with `cf auth whoami`.
- `cf` does not reuse a Wrangler login. A `CLOUDFLARE_API_TOKEN` in the
  environment or a project `.env` overrides the login.
- Unattended jobs need a scoped API token from Bitwarden via
  `bw-secret exec ITEM FIELD CLOUDFLARE_API_TOKEN -- cf ...`.

## Workflow

1. `cf cli search "<task>"` (quoted; local, no credentials) finds the command.
2. `cf schema <command words>` shows the API request; `--help` shows options.
3. Zone commands take `--zone <domain|id>`.
4. Preview writes with `--dry-run`, then run without it.

Output is JSON on stdout, messages on stderr; pipe to `jq`. Lists return one
page; check `--help` for paging.

## Safety

- Changing DNS, WAF, or zone settings, or deleting anything, is an external
  write: confirm with the user first.
- Non-interactive destructive commands without `--force` print `Aborted.` and
  exit 0; verify the result instead of trusting the exit status.
- `--force` can also be an API parameter (e.g. `cf workers delete --force`
  removes Workers other Workers reference); read `--help` before using it.
- Never run `cf dev`, `cf build`, or `cf deploy` in an unmigrated Wrangler
  project; migrate first with `cf migrate --dry-run`, then `cf migrate`.

Docs: https://developers.cloudflare.com/cf/ (index: `/cf/llms.txt`).
