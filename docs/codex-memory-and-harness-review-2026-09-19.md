# Codex memory, harness choice, and computer use — 2026-09-19

Historical snapshot. The subsequent [OMP migration and execution policy](omp-execution-policy-2026-09-19.md)
supersedes the OMP provider/default recommendations below. Codex/T3 settings
remain a separate baseline.

Keep T3/Codex as the main workspace for now. OMP is the more complete alternative
for this user's mix of coding, delegated work, browser use, and native Mac apps.
Pi is the strongest lean-harness challenger to evaluate for coding efficiency.
Neither has demonstrated better Astra subscription longevity on our workload.
OpenCode remains the tested execution path for bounded nous workers.

This is a source/configuration audit and literature review, not a new matched
Astra benchmark or a successful desktop-automation migration. It supplements
the [usage audit](codex-usage-audit-2026-09-19.md) and its completed local-worker
tests. Research includes September 8–18 material and older relevant evidence;
searches did not establish a verifiable recent X consensus.

## What T3 actually changes

Inspected the installed T3 0.0.40 bundle and local settings, rather than assuming
the latest upstream behavior matches this installation. The Codex provider accepts a configured binary path and otherwise resolves
`codex` (observed PATH fallback 0.154.0); the active T3 binary path was not
independently observed. It starts `codex app-server`, retains its thread ID,
and resumes that thread. Normal turns do not reconstruct and submit an additional
full T3 transcript. Codex still owns the agent loop and context handling.

T3 adds developer instructions: its Default-mode template is roughly 1,020
characters, Plan-mode template roughly 9,279, and optional collaborative-browser
instructions another 1,104. Runtime metadata adds a short block. These are source
character counts, not measured tokens or a complete accounting of tool schemas.
Plan mode also changes behavior, so its effect cannot be reduced to prompt size.

T3 generates a first-turn thread title with a separate ephemeral Codex execution,
with up to two retries on failure. Its current default is Luna/low. Regenerating
a title adds another call; source-control text generation runs for relevant
actions. No evidence found that normal provider-health refreshes are model
inference. T3 adds some cost, but is not itself an entirely different Astra
harness. [Upstream provider architecture](https://github.com/pingdotgg/t3code/blob/main/docs/internals/providers.md)

Important local override: T3's saved new-thread selection is **Astra/low/Standard**.
The shared CLI configuration is **Astra/medium/Standard**. T3's explicit selection
can override that CLI default, as can existing per-thread choices. The independent
second desktop retains Luna/xhigh. None of those explicit effort selections was
changed during this review. Three stopped T3 threads still have Fast overrides,
as recorded in the earlier audit; their UI settings remain unchanged.

Native Codex CLI would remove T3's orchestration additions, but retain Codex's
core harness. Switching a T3 thread to OpenCode changes the harness while retaining
the T3 UI. Installed T3 has no Pi/OMP driver. Upstream Pi support remains a proposal;
PR 3818 closed unmerged on July 19. A fork or custom adapter is a maintenance
commitment, not a settings toggle. [Pi proposal](https://github.com/pingdotgg/t3code/discussions/6685),
[PR 3818](https://github.com/pingdotgg/t3code/pull/3818)

## What the comparative evidence supports

| Evidence | Result | Limits on applying it here |
| --- | --- | --- |
| Databricks, July 8 | Same model/effort through Pi sometimes cost less than half as much as the native harness at similar quality; context per turn was substantially smaller. | Private enterprise tasks, different models/codebase; no Astra/ESP32 allowance measurement. |
| September 8 private-suite preprint | Paired native/neutral comparisons did not resolve an average quality advantage. Observed GPT-5.5 cost per solved task favored native Codex. | Neutral harness was deepagents, not Pi; uncertainty and corrected telemetry matter. |
| September 17 SoL-Pi preprint | On EdgeBench, its efficiency configuration reduced cost about one third versus Pi while retaining about 94% of the score. On CPU Terminal-Bench tasks, it solved 15/63 versus 18/63 for both Pi and Codex. | Sol/Opus, not Astra; savings included a quality tradeoff. Research extensions are not stock Pi settings. |

Sources: [Databricks methodology/results](https://www.databricks.com/blog/benchmarking-coding-agents-databricks-multi-million-line-codebase),
[Harness or Model?](https://arxiv.org/abs/2609.11987),
[SoL-Pi paper](https://arxiv.org/html/2609.20519v1).

The SoL-Pi mechanisms are useful leads: avoid repeated large observations,
retain retrievable evidence, combine suitable tool actions, and decide compaction
with cache-rewrite costs in mind. Its full stack is not a no-quality-loss upgrade.
Our compact local-worker receipts already apply the evidence-retention principle;
we have not installed those research extensions or claimed their savings.

A recent firsthand Astra review comparison reported approximate API-equivalent
costs of $1.67 for Codex/low, $2.15 for Pi/low, and $3.13 for OMP/low. Pi with
agents was more expensive again. This is one task without blind quality grading,
not a subscription experiment. Crucially, its Codex input counter included
cached input while Pi/OMP's displayed input excluded it: the columns cannot be
compared directly. [Author's report](https://www.reddit.com/r/codex/comments/1wcc4wh/token_efficiency_codex_vs_omp_vs_pi/)

A more detailed July protocol comparison also found lower starting prompt
overhead for Pi, but task totals depended on caching, model, and tools. It disclosed
test corrections and configuration contamination. This is a useful reproducibility
example, not proof of a universal multiplier. [Author's benchmark](https://github.com/earendil-works/pi/discussions/6646)

The decision metric is **allowance and time per independently accepted result**,
including retries, worker calls, parent review, and repairs. Raw input totals,
smaller initial prompts, or API-equivalent dollars do not establish proportional
ChatGPT subscription savings. A cheaper-looking attempt that needs Astra to redo
the work can be the more expensive workflow.

## Would moving lose computer use?

| Capability | Current T3/Codex | OMP | Stock Pi plus extensions |
| --- | --- | --- | --- |
| Coding tools and local inference | Current Codex workflow; separate tested OpenCode/nous workers | Built-in tools and provider/model routing | Minimal core; configurable providers |
| Browser automation | Current exposed computer-use integration and provider-specific preview surface | Built-in browser; optional Chrome relay | Add browser/MCP extension or CLI integration |
| Native Mac applications | Current CUA integration, though its session is presently stopped | Native desktop tool is installed but disabled | Available through computer-use extensions; not built into the minimal core |
| Delegation | Native Codex children plus external nous worker | Built-in task/subagent controls | Extension or separate Pi processes |
| Existing managed connectors | Present in this Codex session | MCP possible; existing connectors/auth not verified as portable | Add integrations; model login alone does not transfer connector access |
| Current thread/GUI continuity | Preserved | New harness sessions and different UI | New harness sessions and different UI |

OMP 18.1.5 is already installed. Its browser is enabled/headless; the relay is
off. `computer.enabled=false` currently hides native desktop control. Upstream
documents window handles, accessibility actions, screenshots and input, with
macOS permissions required. This is OMP's implementation, not the identical
Codex CUA interface. It needs a real workflow check before calling it equivalent.
[OMP computer-use documentation](https://github.com/can1357/oh-my-pi/blob/main/docs/computer-use.md)

Pi intentionally leaves MCP and subagent orchestration to extensions. Our old
Pi settings already list several packages, including subagents and an output
optimizer, and select a Fireworks/Kimi route. No `pi` executable resolved on PATH
during this audit. Those settings are not a clean Astra/Pi comparison.
[Pi design and extension model](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/README.md)

Two concrete Pi desktop routes exist. `injaneity/pi-computer-use` supplies its own
helper and accessibility-oriented tools. `danecando/pi-codex-computer-use` proxies
Codex app-server MCP calls to the Codex computer-use backend. The latter's source
starts an ephemeral thread and calls tools directly; it does not launch an
additional Codex model turn in that path. However, it is version 0.1.0, with one
June 9 commit, and expects the older `computer-use` tool/app layout. It is not
verified against our current unified CUA surface. A recent crawl date does not
make the implementation recent. [Independent helper](https://github.com/injaneity/pi-computer-use),
[Codex bridge](https://github.com/danecando/pi-codex-computer-use)

Existing skills with explicit CUA API instructions, such as the chandelier
workflow, would need adaptation/validation for another computer-use interface.
Screenshots also require a vision-capable model or an auxiliary vision model;
the small text-oriented nous worker should not silently become the desktop agent.
For browser tasks, DOM/accessibility observations often avoid unnecessary image
payloads; native apps still need screenshots when semantic controls are missing.

## Settings worth keeping or changing

| Setting or behavior | Verified state / decision | Why |
| --- | --- | --- |
| Codex `[desktop] ambient-suggestions-enabled` | Already false; now persisted in shared policy | Avoid optional background suggestions on fresh/reapplied homes. |
| Codex `[features] memories` | Effective default already false; now explicitly persisted false | Avoid background extraction/consolidation and memory injection unless deliberately wanted. |
| Experimental context management | Already disabled by earlier audit | No demonstrated benefit for this setup. |
| Service tier | Standard baseline; three stopped-thread Fast exceptions remain | Avoid paying a speed premium by accident. |
| Main reasoning | Keep medium recommendation, xhigh for difficult reasoning; preserve explicit selections | Low effort can lose savings through retries. |
| Native worker reasoning/context | Luna low/medium with fresh briefs | Avoid inherited Astra/history costs and unnecessary high worker effort. |
| Local workers | Bounded nous jobs, compact evidence, independent checks | Replaces suitable cloud work while retaining quality control. |
| Context window / compaction | Keep Codex model defaults; OMP extended context is off | Larger windows and overfrequent compaction can both add cost. |
| OMP memory, recap, advisor | All already off | No active background feature to disable here. |
| OMP async/idle compaction | Already off | Avoid optional background processing. |
| OMP `tools.xdevDocs` | `catalog`, with `tools.xdev=true` | Discover less-used tools without eagerly expanding all documentation. |
| OMP `provider.appendOnlyContext` | `on` | Existing cache-oriented setting; measure total context too. |
| Pi `cacheWarming` | For a future subscription-focused trial, start `off` | Warming makes extra billed requests; API-price heuristics do not prove allowance savings. |
| Pi `showCacheMissNotices` | Useful to enable in a future trial | Observability rather than a savings claim. |
| Skills, history files, hooks, rendering | Keep useful capabilities | Their mere existence is not evidence of inference usage. |

The two new shared opt-outs preserve current behavior. They are drift prevention,
**not a newly measured reduction in usage**. All three distinct local Codex TOMLs
had ambient suggestions off; all three memory databases had zero jobs and zero
stage-1 outputs. Historical suggestion JSON files exist but do not establish an
active generator. No stored conversations or memory artifacts were deleted.

Native memories can consume quota while generating summaries. `generate_memories`
and `use_memories` are separate finer controls, but are unnecessary to add while
the feature itself is disabled. Computer History is a newer feature replacing
Chronicle and depends on Memories; it is not the same thing as saving local CLI
history. [Official Memories](https://learn.chatgpt.com/docs/customization/memories),
[Computer History](https://learn.chatgpt.com/docs/customization/computer-history),
[pinned configuration schema](https://github.com/openai/codex/blob/rust-v0.154.0/codex-rs/core/config.schema.json)

The remembered H/N/I name might be **Hindsight** or **Mnemopi**, both OMP memory
backends; the active backend is `off`. Ambient/personalized suggestions are
another plausible match. Users report quota drain from them, but those reports
are not controlled billing measurements, and OpenAI support's September 9 reply
did not verify the allowance effect. [Firsthand report](https://www.reddit.com/r/codex/comments/1w11frm/fix_for_codex_desktop_using_quota_while_idle/),
[support discussion](https://community.openai.com/t/title-codex-desktop-background-ambient-personalized-suggestions-appear-to-consume-quota-without-explicit-user-action/1385208)

Pi's current documentation explicitly describes cache warming as extra requests.
It can be economical for some API/cache configurations, but is not free capacity.
Hiding thinking text is likewise different from reducing reasoning effort.
Do not disable images globally to save tokens if desktop work needs vision.
[Pi settings](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/settings.md)

OMP's present provider roles use Grok/Gemini/GLM routes, not an equivalent copy of
the Astra/Codex setup. Its 180K snapcompact policy was chosen around that setup.
Do not transplant it into an Astra comparison or assume bitmap compression
preserves every firmware detail. Its configured fallback chains also include
metered cloud routes: a local trial must explicitly prevent silent cloud fallback.
No OMP settings, model roles, or computer permissions were changed in this review.

## A migration that would earn its cost

For feature continuity, trial OMP before assembling a Pi replacement. For a
strict coding-efficiency comparison, test a minimal Pi profile alongside Codex.
Keep T3's existing sessions and integrations available throughout. A full move
should require both better accepted-work efficiency and working native-app,
browser, connector, and delegation paths that the user actually depends on.

Use actual s3-amoled task families: a C/C++ state/eligibility bug with independent
edge-case checks, a bounded firmware integration with a real build, and a visual
or device workflow whose acceptance cannot be reduced to compilation. Separate
code-only harness evaluation from the desktop capability check.

Freeze task inputs, base revision, model ID, effort, service tier, account route,
tool access, and allowed context. Use isolated copies without accessible future
solutions in git history. Run paired trials in alternating order, retain failures
and corrections, and repeat where results remain ambiguous. Avoid a single toy
task or arbitrary score threshold as a migration verdict. Keep fixture/test
oracles outside the agent's write scope and grade behavior, not patch wording.

Record uncached input, cached input, output (including reasoning without double
counting), auxiliary calls, wall time, and verified outcomes. Use actual allowance
snapshots only when concurrent account work and reset boundaries are controlled.
Include desktop recovery, summary accuracy, missed requirements, and human repair
time. Do not confuse the same model name via OpenRouter/API billing with the
ChatGPT subscription route.

## Applied change and validation

Updated `home/.chezmoitemplates/codex/model-policy.toml.tmpl` with the two opt-outs.
Applied only the three Codex config targets on this Mac; T3 shadow-home symlinks
share the primary configuration. Verified existing-home and empty-home rendering,
semantic diffs, pinned CLI feature resolution, and baseline checks. The only
semantic live-config change was making the already-false memories default explicit.
Other settings were preserved. New processes read the policy; active work was not
restarted. Fleet application outside this Mac is unverified.

Local evidence is in `/tmp/codex-memory-audit/` and the installed T3 bundle
extraction `/tmp/nous-t3-inspect/`. Pre-change local configuration backups are in
`~/.local/state/codex-audits/before-memory-policy-20260919/`. These local artifacts
are not added to Git. No additional paid model benchmark was run for this review.
