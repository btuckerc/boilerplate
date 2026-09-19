# Codex usage and local-worker audit — 2026-09-19

Keep Astra for judgment and integration, with medium as the default and xhigh
available for demanding work. Use a fresh-brief Luna worker for broader
execution, and Ornith on nous for bounded file tasks whose results are cheap
to check. The changes below implement that recommendation without replacing
the main thread or changing the global OpenCode model picker.

## What changed

- The shared policy now persists Standard service, four concurrent spawned
  threads, Luna/low as the subagent default, and stable context management.
  Astra/medium remains the main default. Standard and four-way concurrency
  were already present in the live configuration; publishing prevents drift.
- Disabled the experimental context opt-in. This removes an unproven setting,
  not a demonstrated source of usage: the installed Astra/Luna catalog already
  reports `supports_experimental_context: false`.
- The second independent desktop retains its existing Luna/xhigh selection
  when the baseline is applied. Its adapter previously would reset it to Astra.
- The small shared `local-workers` skill now makes the routing recommendation
  discoverable across threads. Native Luna workers get a self-contained brief
  with `fork_turns="none"`, low effort for extraction and medium for bounded
  implementation. A full-history fork inherits the parent model in this
  harness, defeating an attempted cheaper model override.
- `nous-worker` returns a compact result with a session ID and evidence path.
  Raw traces stay on disk. The worker defaults to 12 steps and 180 seconds,
  cleans up its process group on deadline/cancellation, and promptly reports a
  busy or unavailable backend. The lock covers this workstation only.
- Worker-only provider/model selections keep main and auxiliary inference
  local. Global OpenCode defaults remain optional. Cloud fallback requires the
  supervising parent to deliberately choose Luna or another model.
- Added a read-only, repeatable usage audit. It emits token metadata only and
  requires neither an agent call nor an external service. No scheduled AI
  audit or self-modifying background agent was added.

The primary CLI, all three existing T3 shadow homes, and both independent
desktop homes were checked. Configuration files are applied on this Mac.
Already-running app-server sessions may retain their startup configuration;
new sessions load the changes. Active user work was not restarted.

## Measurements and interpretation

Snapshot: 2026-09-19 23:44:35 UTC; preceding 14 days. Scanned 710 local rollout
files across current and archived sessions in the primary, T3 and desktop
homes. Resolved symlinks and 138,081 response IDs were deduplicated.

| Attributed model | Responses | Median input | 90th percentile input | Cached share of input |
| --- | ---: | ---: | ---: | ---: |
| Astra | 47,509 | 122,628 tokens | 197,666 tokens | 97.6% |
| Luna | 90,517 | 134,734 tokens | 209,865 tokens | 97.0% |

The remaining 55 responses are attributed to automatic approval review.
Luna's recorded effort was `max` for 63,181 responses, about 70% of its total.
This does not establish that max was unnecessary; existing explicit thread
choices were preserved. New delegated work uses lower effort when suitable.

These are per-response input distributions, not unique document sizes or
subscription charges. Repeated cached context is counted on each request.
All model/effort attribution came from rollout turn context, rather than
authoritative model metadata on each usage record. Internal model switches
can therefore be missed. Two files have recent legacy cumulative counters
without per-response usage records; those counters are excluded from totals.
This Mac's retained logs are not a complete fleet-wide billing history.

The important finding is large recurring context, much of it cached. Do not
interpret the aggregate billions of repeated input tokens as uncached usage,
or infer a subscription percentage from API prices. Output/reasoning also
matters; the audit treats reasoning tokens as a subset of output.

The shared/user skill catalog was only about 3.8 KB of discovery metadata at
inspection, excluding built-in/plugin metadata. The project `s3-amoled`
AGENTS file was about 3.8 KB and contains useful hardware/project rules. No
global home or repository-root AGENTS file was adding a large workflow prompt.
By comparison, this long audit's accumulated tool outputs exceeded 1.7 MB;
that is historical output, not a measurement of the active context after
compaction. Short briefs and compact evidence are better targets than removing
useful skills or project rules.

One successful local review retained a 27,279-byte event trace and returned a
1,483-byte summary file: about 95% less material to read into the parent for
that result. This is a measured payload reduction, not a subscription-savings
estimate. The earlier unbounded review had looped through 42 file-tool calls
after receiving long JSON lines. It was stopped, its inputs converted to
ordinary text files, and the bounded launcher completed the review in 14.19 s.

## Research and settings decisions

OpenAI documents that model choice, context, reasoning and tools affect usage;
Astra Fast currently applies a 2.5x multiplier to its Standard credit rate.
Luna is substantially cheaper in the published credit table. These are reasons
to keep Standard and route suitable work, not promises of a fixed multiplier
in usable subscription time. [Official pricing](https://learn.chatgpt.com/docs/pricing.md)

The configuration reference defines the experimental flag, model compaction
threshold, per-tool history budget, and skill-catalog budget. We retained
model-selected context/compaction thresholds and the current 10,000-token
model-selected tool-output cap. A lower cap can hide needed diagnostic output
and cause repeated reads; compact worker results address a known source first.
The existing catalog is small enough that an artificial skill cap would mostly
risk hiding instructions. Request compression reduces transport bytes, not
the model's token input. [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)

The local catalog advertises a 272K default context with a 95% effective
window. We did not expand it to the larger advertised maximum, force a 128K
compaction threshold, replace the compaction prompt, or globally lower Astra's
reasoning. There is no controlled evidence here that those changes improve
completed work per subscription allowance. Frequent compaction can add work
and lose useful detail; large-context API pricing rules must not be assumed
to apply identically to subscription accounting.

Recent firsthand reports point in the same practical direction, with limits:

- September 10: a user reports large context growth and high cache reuse in
  routine UI work. It supports investigating long histories, but is not a
  controlled billing experiment. [Codex issue 44462](https://github.com/openai/codex/issues/44462)
- September 6–10: users ask how experimental history lookup is accounted for;
  this does not establish that the experimental mode saves usage.
  [Discussion 43257](https://github.com/openai/codex/discussions/43257)
- September 13: an author's investigation recommends independently scoped
  subagent briefs and warns that tiny delegated tasks can cost more than doing
  them directly. [Subagent context investigation](https://zenn.dev/kagarist/articles/codex-subagent-context-cost?locale=en)
- A firsthand Astra/Luna orchestrator keeps Astra on planning and Luna on
  execution, but adds several roles and can use high worker effort. We adopted
  the routing principle, not its full configuration or unmeasured savings
  claims. Its publication date was not verified as inside the two-week window.
  [Author's setup](https://github.com/donvito/codex-astra-luna-orchestrator)

Searches specifically targeting X posts from September 5–19 did not return
verifiable relevant recent posts. The research therefore relies on the dated
reports above and official documentation; it does not claim an X consensus.

OpenCode's provider allowlist and small-model settings are documented, and its
pinned source confirms that compaction can select a separate agent model.
This is why the launcher pins auxiliary inference as well as the main worker.
[Configuration](https://dev.opencode.ai/docs/config/),
[1.18.31 compaction source](https://github.com/anomalyco/opencode/blob/v1.18.31/packages/opencode/src/session/compaction.ts)

## Verification and remaining boundaries

Ten automated tests cover metadata deduplication across homes/archives,
timestamps, legacy counters, malformed tails, compact worker output with full
evidence retained, inherited model overrides, read-only permissions, busy and
offline failures, deadline cleanup, caller cancellation and slot reuse. Source
baseline checks pass. A fresh-brief Luna agent implemented the audit utility;
the parent reviewed it, caught schema/coverage issues and verified corrections.

Live Ornith tests from this T3 main thread:

| Task | Result |
| --- | --- |
| Bounded read-only launcher review | 14.19 s, four file-tool calls; parent rejected an unsupported tuning suggestion |
| Implement action selector | 30.52 s; 640 independently checked eligibility/tie/input-mutation cases passed |
| Resume session and add cooldown rule | 10.64 s; parent found a negative-cooldown edge-case error |
| One focused correction | 10.48 s; all 2,560 expanded cases passed afterward |
| Launch with inherited cloud auxiliary settings | 9.40 s; completed using the worker's local selections; its prose still required interpretation/checking |

These are bounded function/tool tests, not a general intelligence benchmark.
Local workers are useful when verification is cheap. Their claims are not
proof of correctness. Existing Gemma/Bonsai/Nemotron findings remain in the
[model evaluation](nous-model-evaluation-2026-09-19.md); Nemotron is experimental.
Ornith remains the default worker, with Gemma and Bonsai optional. Stock llama
remains the active backend. A nous worker is an OpenCode subprocess supervised
by T3/Codex, not a native cloud `spawn_agent` child or a T3 subagent-tree entry.

Three stopped T3 threads retain explicit `priority`/Fast overrides:
“Restore Safe macOS File Pickers”, “Improve Site Icon Consistency”, and
“Hardened Invite Access Controls”. They are not currently running. Those
per-thread choices can override Standard if resumed. The computer-use bridge
still reported a stopped session after work was resumed, so these UI settings
were not changed; the application database was inspected read-only. They
remain the specific unresolved UI exception to the Standard recommendation.

## Repeatable audit and evidence

From the baseline repository:

```sh
python3 utils/scripts/codex_usage_audit.py --days 14
uv run --with pytest pytest -q utils/scripts/tests/
python3 utils/scripts/check_baseline.py
```

The utility reports metadata and coverage limitations, never conversation text.
Use `--home PATH` repeatedly to audit selected homes and `--output PATH` to save
a snapshot. Compare like tasks and quality outcomes before asserting savings.
The existing `codex-meter`/`codex-budget` tools remain responsible for actual
account allowance snapshots; this utility does not replace them.

Local evidence (not committed):
`~/.local/state/codex-audits/usage-2026-09-19.json`; worker runs
`run-vq8jc69a`, `run-tjaoreg1`, `run-l0273fe6`, `run-z7tpblku`, and
`run-6p46hpqr` under `~/.local/state/nous-workers/`. The code fixture and parent
check counts are retained there in `code-verification-20260919/`.
