---
name: web-data
description: Use parallel-cli or the firecrawl CLI when native web search/read fall short - deep research, entity lists, monitoring, JS-heavy or bot-walled pages, site crawl/map, code/issue search, Alexandria advisory data.
---

# Web data (Parallel, Firecrawl)

Native tools first: OMP web search (Exa, then keyed Firecrawl and Parallel as
fallbacks) and URL reads cover routine lookups. When local readers fail, URL
reads fall back to keyed Parallel/Firecrawl extraction (billed, cheap). Use the
CLIs (`parallel-cli`, `firecrawl`, pinned in mise) only for what those lack.

## Keys

- `PARALLEL_API_KEY` and `FIRECRAWL_API_KEY` live in `~/.omp/agent/.env`,
  written by `omp-env` from 1Password items `parallel-api` and `firecrawl-api`.
  OMP shells inherit them. Missing: the user runs `omp-env` on that host
  (`machine-secrets` skill).
- Never run `login`, `config`, `init`, `setup`, `env`, `launch`, `make`,
  `skills` or `update`: they store credentials, install MCP servers or skills,
  or replace the pinned binary.
- Codex shells lack the keys. Only when the user asks, load just those two
  lines for one command:
  `( eval "$(grep -E '^(PARALLEL|FIRECRAWL)_API_KEY=' ~/.omp/agent/.env)"; export PARALLEL_API_KEY FIRECRAWL_API_KEY; firecrawl ... )`.

## Which command

| Need | Command |
| --- | --- |
| Second engine, domain or date filters | `parallel-cli search "objective" --mode fast --include-domains D --after-date YYYY-MM-DD` |
| Markdown of known URLs | `parallel-cli extract URL...` or `firecrawl scrape URL --only-main-content` |
| JS-heavy or bot-walled page | `firecrawl scrape URL --wait-for 3000` |
| Site URL list, docs crawl | `firecrawl map URL`; `firecrawl crawl URL --limit N --wait` |
| Repos, issues, PRs, curated docs | `firecrawl developer "query"` |
| Cited deep research | `parallel-cli research run "question" --text -p core -o /tmp/NAME` |
| Entity lists, enrichment, change tracking | `parallel-cli findall`, `enrich`, `monitor`; `firecrawl monitor` |
| Advisory data (NVD, CISA KEV, OSV, GitHub) | `firecrawl alexandria developer`, then `firecrawl scrape <tool address>` |

Read the subcommand's `--help` first; flags change between releases.

## Spending

- Firecrawl is on the free plan: 1,000 credits a month. Search costs 2 per 10
  results, scrape 1 per page (+4 for JSON; PDFs 1 per parsed page), crawl 1
  per page. Always pass `crawl --limit` (the API default is 10,000 pages) and
  `--max-pages` for PDFs; check `firecrawl credits` before bulk work.
- Parallel draws prepaid credit; don't rely on its spend limit to stop a run.
  `research run` defaults to `pro-fast`; use `lite`, `base` or `core` unless
  the question needs depth.
- Ask the user before `ultra*` processors, `findall`, `enrich` batches, any
  `monitor` (recurring charges), `firecrawl agent` or `interact` beyond one
  test, and any Alexandria provider execution (discovery is free, execution is
  priced per provider, some providers need terms; never accept terms). Never
  top up a balance.
- Dependency audits use lockfile scanners (`osv-scanner`, `npm audit`,
  `pip-audit`); Alexandria only enriches a specific advisory.

## Privacy

Parallel's customer terms let it train its models on submitted data, and both
vendors keep zero data retention for higher tiers. Never send secrets, private
code, signed or authenticated URLs, or private page content.
