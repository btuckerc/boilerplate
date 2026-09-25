# OMP execution policy and measured migration — 2026-09-19

See the focused [OMP context and routing audit](omp-context-audit-2026-09-19.md) for the final RULES and local-workers changes and the failed native tool-surface trial.

The current routing recommendation was revised on 2026-09-22 from Astra-first
to Sol-directed, local-first execution. OMP 18.2.8 is installed and pinned.
Start new work with `omp`; existing sessions keep their selected model.
OpenCode remains useful for the existing T3 Nous instance and `nous-worker`;
it is not a prerequisite for OMP local children.

## Execution policy

| Work | Default choice | Reason |
| --- | --- | --- |
| Ordinary direction, requirements and integration | Sol 5.6 medium (default) | Capable director without paying Astra cost for every turn |
| Bounded implementation with clear contract and independent checks; mechanical edits/extraction | `nous` / Qwen3.8 medium first | Parent settles risky invariants and verifies; no autonomous local design |
| Work unsuitable for local capability/context or delayed by the local queue | Luna 5.6 medium via `task` | Focused cloud worker; read-only discovery uses `scout`, mechanical work `sonic` |
| Unresolved high-consequence design, conflicting evidence after investigation, failed check after one repair | `architect` / Astra medium for advice; `astra` / Astra medium for implementation | Scoped, evidence-triggered escalation, not routine review; clearly hard work may go directly here |
| Explicit sustained frontier work | Astra xhigh via `@slow` | Not the default escalation effort |
| Small mechanical transforms, extraction, predetermined edits | `nous` child / Qwen3.8 | Local tokens, short brief, independent exact checks |
| Manual alternatives | OpenRouter and explicitly selected smaller local models | Preserve provider choice without silent paid fallback; Bonsai is retired |

The model cycle is `default` / `task`. Routine work may stay direct; delegation
is chosen by the Sol director and carries a fresh scoped brief. Local-first
applies where the contract and acceptance are independently checkable and bounded;
it does not make nous an autonomous design/debugging default.
A worker receives owned files, contract, risky invariants and acceptance command,
not the entire main transcript. Reuse supplied requirements and add only missing
design decisions; there is no minimum brief length. The parent checks and reviews
the resulting artifact; at most one
focused failed-check repair is allowed before explicit escalation.
The `architect` agent is read-only. `astra` can implement; neither delegates.
Only one nous GPU worker should run at a time. A local error does not authorize
an automatic cloud fallback or service switch.

This is an evidence-backed starting policy, not proof of optimal routing.
Escalation creates a child and returns to Sol; it does not change the parent
model automatically. Workers return blockers to Sol instead of recursively
escalating. Missing information or access requires prerequisites, not a larger
model. No classifier, routing service, compulsory planner or advisor was added.

### Routing evidence and limitations — 2026-09-22

- [OpenAI's usage guide](https://help.openai.com/en/articles/20001516-managing-usage-with-gpt-6-astra-in-work-and-codex)
  estimates Plus local messages per five-hour window at Astra 5–45, Sol 10–100,
  Luna 250–2,000. These are variable estimates, not fixed message limits or
  per-task savings. Model, context, reasoning effort, tools and speed all affect
  allowance; switching models does not restore a shared quota.
- [OpenAI's GPT-5.6 efficiency guidance](https://openai.com/index/advancing-the-price-performance-frontier-with-gpt-5-6/)
  explicitly describes Sol resolving uncertainty/planning and Luna implementing
  well-specified changes. Luna's lower price is reflected in subscription usage,
  but API/catalog cost is not an observed subscription debit.
- The local stats database, synced before this change, contained 9,307 Astra
  main requests and 65 Astra child requests since September 15, versus 4 Luna
  main and 4,338 Luna child requests. No Sol history was present. These are
  unmatched historical request counts, not task-quality scores or a controlled
  savings comparison. They establish Astra-heavy direction, not that every
  request could safely move to Sol.
- The existing Qwen admission trial below passed 8/8 guided bounded attempts,
  matching Luna's 8/8 in four synthetic task families. That supports keeping
  local-first within those constraints, not treating local as a frontier model.
- A fresh default session reported `gpt-5.6-sol` and completed a live request.
  In a synthetic DMA ownership case with a failed repair and unresolved
  high-consequence race, Sol independently selected `architect`. The first
  harness omitted native hub and induced artifact polling; that setup was
  corrected. The final run used native waiting and omitted the effort override,
  retaining configured Astra medium. One case proves the upward route is usable,
  not that Sol always chooses it.
- A separate explicit dispatch smoke exercised nous, Luna and writable Astra
  from a Sol parent. All three produced their owned JSON artifacts and passed
  independent exact checks. This tests dispatch, not comparative intelligence.

Use existing session evidence to review first-pass acceptance, repairs,
escalations and latency on comparable real tasks. Measure subscription allowance
only with account/window boundaries and concurrent usage controlled; do not
convert catalog dollars to claimed quota savings. No new telemetry service or
per-request classifier is required.

Cloud IDs live in `private_config.yml` roles and enabledModels. Agents use aliases;
the baseline check validates family/effort independently of generation. Upgrade
Sol/Luna there only after native discovery and exact response-model smoke tests.
There is no GPT-5.6 Astra in the current native catalog; retain the working
GPT-6 Astra escalation. Historical experiments below retain their original IDs.

Runtime/configuration validation passed with `omp-baseline validate`; native skill
projection also passed. The strict publication check reports only the new,
untracked `agents/astra.md` as pending. Nothing was staged, committed or published.

## Accounts, settings, and context

Four independently authorized native Codex OAuth accounts are connected on this
Mac: primary, second, last, btc. Native live inference passed for primary, second,
and btc. Last returned an actual usage-limit error; login succeeded. Quota state
changes over time. The pool selects accounts using available quota and session
stickiness; it is not equal round-robin and cannot create additional allowance.
Use `/session pin` to choose an account, and `omp usage --provider openai-codex
--redact` to inspect usage. Do not use `omp token` as an account selector: it prints
a credential. Do not copy Codex refresh credentials into OMP or between machines.
Four accounts are not a fleet prerequisite.

The shared settings now use:

- Sol 5.6 medium for default; Astra 6 medium for plan/architect/astra; Luna 5.6
  medium for vision/task and low for scout, commit and tiny roles. Nous is
  preferred for suitable bounded work; Astra xhigh remains the explicit slow role.

The evidence matrix is deliberately small: the Astra→Ornith corrective child
passed its specified quotient/remainder edit and independent compile/run
(21.6 s); the original Ornith repair failed an exact edge case, and the
Luna→Gemma repair overflowed at `SIZE_MAX`. These are tested fixture outcomes,
not general quality claims. They support local-first bounded delegation with
parent checks and a Luna fallback, while keeping novel algorithms and uncertain
debugging on Luna/Astra.

A native steering acceptance started a background `nous` child, observed its
running status, delivered one `hub send` correction before final yield, and
verified the corrected artifact with a parent-run check. Parent metadata was
`gpt-6-astra`; child metadata was `llama.cpp/Ornith-1.5-9B-Q5_K_M:off`.
The child had no shell tool, so the parent ran the acceptance command through
native `hub start`. This demonstrates steering and verification boundaries for
one fixture; it is not evidence of general model quality or savings.

Supervision follows OMP's native task and hub semantics: background local
children expose compact status, the director may send steering at model/tool
boundaries whenever new evidence or requirements warrant it, and a stuck or
over-budget child is cancelled or escalated to Luna. The one focused repair
correction budget applies only after repeated local failure; it does not cap
normal coordination or user steering. This keeps full transcripts available
for diagnosis without making transcript polling or an advisor loop part of
normal execution. See the
[task agent](https://raw.githubusercontent.com/can1357/oh-my-pi/v18.2.6/docs/tools/task.md)
and [hub](https://raw.githubusercontent.com/can1357/oh-my-pi/v18.2.6/docs/tools/hub.md)
semantics for the pinned OMP release.
- `task.eager: default`, depth 1, concurrency 3, a 40-request soft worker budget
  and 10-minute runtime limit. Soft budgets are not hard token caps.
- `task.enableEffort: true` exposes native per-task effort without a classifier.
  Omit the hint for configured medium. Current `lo` resolves to low for
  Astra/Luna; coarse `med` resolves to high, not medium. Retain local medium.
- Prewalk, background advisor, memory, recap, idle/async compaction, unexpected
  stop resumption, and automatic context promotion off. Standard OpenAI tier.
- Native model-aware compaction thresholds (`-1`), mid-turn compaction enabled,
  recent-content budget 8,000 rather than 20,000 (the local context is only 16K).
  Provider context behavior is `auto`, not the old forced Grok policy.
- One ordinary retry; cross-model fallback disabled. Native within-provider
  account rotation remains available.
- Lazy LSP, catalog-only documentation for less-used tools, foreign harness
  discovery disabled, native shared skills enabled.

First-message titles still use the tiny Luna role. Replan titles are off.
Thinking-display settings are presentation choices, not demonstrated reductions
in model reasoning or quota. No model weights or inference service were added to
the Mac. Experimental `promptProfile` / `xdevForceMount` recommendations belong
to a separate fork and are not supported by this installed release.

The usage widget now reads native Codex usage rather than SuperGrok. Grok roles,
model overrides, OAuth login and the Linux launch binding were removed; OpenRouter
remains available and its live GLM 5.3 Flash call passed. This does not cancel any
subscription. Auth databases, tokens, `.env`, sessions and caches stay outside Git.
Chezmoi source names `private_config.yml` / `private_models.yml` deploy to ordinary
`~/.omp/agent/config.yml` / `models.yml` with mode 0600, resolving permission drift.

## Astra-directed Qwen admission — 2026-09-22

The earlier Ornith/Gemma results below are historical. This admission used
Qwen3.8-27B-UD-Q5_K_M, medium, served at 65,536 context / 8,192 output. Since
2026-09-25 the promoted worker is Qwen3.8-27B-UD-Q4_K_XL with a DFlash2 drafter
(131,072 context); see [the nous inference notes](nous-inference.md).
The question is whether compact Astra design guidance makes a bounded local
implementation lane useful, not whether Qwen independently equals Luna.

Protocol and guidance were frozen before held-out inference. Four synthetic
task families (two-file API migration, TTL/LRU cache, recursive config overlay
with consumer, incremental binary framing) ran twice each under bare Qwen,
Astra-guided Qwen, and Luna medium. Order was reversed on the second round.
Each used native OMP 18.2.6 read/edit/write, fresh files, no skills/extensions,
no model fallback, and external parent-run behavioral checks. Provider defaults
and output limits were retained rather than artificially equalized.

| Condition | First-attempt complete contracts | Median seconds | Total seconds | Reported output tokens |
| --- | ---: | ---: | ---: | ---: |
| Bare Qwen | 6/8 | 41.9 | 376.0 | 16,485 |
| Astra-guided Qwen | 8/8 | 34.6 | 313.3 | 13,517 |
| Luna medium | 8/8 | 22.2 | 192.0 | 6,310 |

Both bare failures evicted a live cache entry while retaining an expired,
recently accessed entry. Frozen guidance explicitly separated expiry, recency
and capacity decisions. Guided runs needed no repairs. All 24 runs exited zero
without timeouts, reported tool errors, or detected out-of-scope file changes.
The API case is a small migration, not a repository-scale refactor.

Guidance was 105–118 words per family, 446 unique words total; it contained
approach/invariants, not full implementations or hidden expected outputs.
The prior failed SSE artifact was separately repaired with a 115-word brief:
32 checks passed in 65.7 seconds. That calibration result is excluded from
held-out scores and does not establish held-out repair success.

Predeclared quality gate: >=7/8 guided first-pass and 8/8 after at most one
repair, no fewer passes than Luna, no scope violations. Latency gate: median
including repairs <=4x Luna. Both passed: guided Qwen was 1.56x Luna's median.
This admits supervised bounded implementation, not novel algorithms, uncertain
debugging, vision, large-context tasks or a wholesale replacement of `@task`.
The parent must have meaningful checks and review the code, not accept a
worker's claim of success. Avoid a local queue when foreground delay dominates.

No net subscription saving is claimed: this experiment used cloud workers to
construct the harness and Luna for comparisons; the Astra director's usage
and subscription debits were not isolated. Luna's eight runs had an OMP
catalog-price estimate of $0.0299, not a measured subscription charge.
Tokenizers differ. The guided implementation generation itself stayed local.
Raw synthetic fixtures, frozen briefs, graders, prompts, usage and outputs:
`/tmp/astra-local-gates/`. Reference implementations passed and buggy seeds
failed before inference; harness defects were corrected before any scored run.

### Native director/child smoke and overhead

After applying the rules and nous agent, a fresh Astra medium parent delegated
one cache implementation to native `nous`, then ran the six parent checks:
all passed in 77.4 seconds end-to-end. Hub metadata resolved the child to
`llama.cpp/Qwen3.8-27B-UD-Q5_K_M:medium`. The equivalent explicit Luna-control
child resolved to `openai-codex/gpt-5.6-luna:medium` and passed in 47.7 seconds.
Both clean runs exposed read/task/bash/hub to the parent; local child inference
remained serial and there was no failed-check repair.

An initial smoke accidentally omitted the parent's hub tool. It still passed
the checks, but attempted shell `hub` and sleep-based waits. That harness error
was corrected; its 96.1-second run is retained separately and is not the clean
integration result or part of the 24 scored attempts.

Both clean routes used seven Astra assistant messages and roughly 63K parent
input tokens including cache reads. The local-child parent produced 582 output
tokens versus 618 for the Luna-child parent. OMP estimated parent API-list
costs at $0.2676 versus $0.1874, with different cache-hit mixes; these exclude
child costs and are not subscription debits or a controlled cost benchmark.
This is why the policy uses the existing Astra director, batches compatible
edits, avoids extra planning agents, and keeps trivial work direct. Offloading
child implementation is proven here; net subscription allowance savings are not.

## Orchestration hill climb — 2026-09-22

Objective: accepted work per total OpenAI usage, including director calls,
verification and failed attempts. OMP remains the only front door. No extra
router service, model download, inference-service change or cloud fallback.

Twelve fresh-session trials covered a TTL/LRU fixture and a refactor of the
actual `utils/nous/summarize.py`, copied into disposable directories. The latter
had six independent acceptance checks: import-safe sparse metrics, explicit
CLI file plus stdout, default output selection, malformed records, empty input,
and legacy no-argument CLI. The original failed and a reference passed before
worker trials. Workers did not receive the checker or a complete implementation.
Failures were recorded without repair to measure first attempts.

| Trial | Acceptance | Wall time | Astra calls |
| --- | --- | ---: | ---: |
| Cache, background local plus hub waits | 6/6 | 103.1 s | 8 |
| Cache, blocking local | 6/6 | 89.2 s | 4 |
| Cache, native eval await/check | 5/6 | 95.3 s | 3 |
| Repository summarizer, local medium | 6/6 | 79.3 s | 4 |
| Same, local low | 6/6 | 199.0 s | 4 |
| Same, local medium eval await/check | 6/6 | 202.6 s | 3 |
| Same, Luna configured medium | 6/6 | 83.8 s | 4 |
| Same, Luna configured medium repeat | 5/6 | 101.3 s | 4 |
| Same, Luna low | 6/6 | 58.1 s | 4 |
| Same, coarse `med` (actually Luna high) | 6/6 | 85.1 s | 4 |
| Same, direct Astra medium | 6/6 | 34.7 s | 4 |
| Normal live front door, no forced route/effort/tools | 6/6 | 38.9 s | 4 |

The unforced front door selected direct Astra (`read`, `edit`, `bash`), a
reasonable fast lane for this small change. This does not prove automatic
local selection on larger work. Luna's failed repeat wrote the output file
but omitted required stdout. The cache failure evicted a live item while an
expired item remained; that capacity invariant was not explicit in the public
brief. Earlier guided-versus-bare cache comparisons therefore confound improved
contract completeness with implementation guidance. They are not clean proof
that supplying an algorithm is necessary.

On the matched summarizer pair, the local and Luna routes each used four Astra
calls, 37,170 versus 37,060 parent input tokens including cache, and 518 versus
521 parent output tokens. Local work avoided the entire 86,905-token Luna child
conversation without extra director calls. This is evidence of avoided cloud
worker traffic, not a measured subscription allowance percentage. Parent cache
mix differed greatly; catalog dollars cannot isolate a routing benefit.
The cache blocking trial reduced parent calls from eight to four and processed
input from 73,139 to 35,530 tokens. One pair is not a general savings estimate.
Native eval achieved three calls but did not improve latency reliably.

### Promoted policy

- Keep trivial work direct. Admit bounded local implementations with a clear
  contract and parent acceptance, not only predetermined line edits. Astra
  settles risky design; routine implementation choices belong to the worker.
- Keep `blocking: false` for concurrency and steering. When solely waiting on a
  bounded local job, native eval can spawn, await, and execute the pre-agreed
  parent check in one cell. Retain the handle and use a finite handle wait:
  eval's cell timeout pauses during agent waits and is not a worker deadline.
- Enable native `task.enableEffort`. Omit the hint for configured medium;
  current coarse `med` means high on Astra/Luna. Use `lo` for routine cloud work
  where appropriate, not as a blanket setting. Keep local medium: the low trial
  emitted 8,224 output tokens versus 1,906 at medium and took longer.
- Keep one focused failed-check repair, then escalate. No mandatory classifier,
  extra planner, transcript polling or background advisor.

### Research limits and deferred changes

Jev's 12/12 and Laya's 7/12 remain synthetic route-label agreement, not executed
downstream savings. No router was promoted from those scores. OpenJev documents
NVIDIA/vLLM and Apple/MLX, not our AMD runtime; fitting 32 GB is insufficient.
The advisor-strategy study supports selective consultation, not enabling OMP's
different background-advisor mechanism. Execution-verified full trajectories,
as in TwinRouterBench, are the appropriate next admission standard.

The [Qwen model card](https://huggingface.co/Qwen/Qwen3.8-27B) explicitly warns
that lower effort can increase total work. Live sampling matched its thinking
temperature/top-p/top-k, but used min-p 0.05 instead of recommended zero.
Sampling was not changed; no causal benefit has been demonstrated.

[OMP 18.2.7](https://github.com/can1357/oh-my-pi/releases/tag/v18.2.7)
adds native system-prompt templates and changes thinking policy; 18.2.8 adds
judge-provider support and notification improvements. Neither was installed.
[PR 12614](https://github.com/can1357/oh-my-pi/pull/12614) restores the Qwen
top-level dialect after an intervening discovery change. The pinned 18.2.6
`classes/qwen.kdl` already selects `qwen` plus template reasoning effort for
llama.cpp Qwen >=3.8; this PR alone is not evidence our trials used the wrong
dialect. Actual server-side effort was not separately traced in these runs.
The shared upgrade requires clean pin files; pre-existing dirty pin work was
preserved. Lean native prompt templates merit a separate compatibility and
acceptance experiment, not an untested prompt replacement or fork today.

Raw events, graders and aggregate accounting remain private under
`/tmp/omp-orchestration-hillclimb/`; `analysis.json` includes failed trials and
native child usage where available. Temporary experiment files are outside
the repository. These are small stochastic fixtures, not a repository-wide
quality ranking or proof of globally optimal routing.

Source and MacBook live rules, nous agent, task-effort setting and both skills
were applied. Native config lookup and skill validation passed. Strict baseline
validation remains blocked only by the existing untracked `commands/draft.md`.
No commit, push, shared version-pin change or remote-host rollout was performed.

A separate native timeout smoke caught an API pitfall before final delivery:
JavaScript `h.wait(0.001)` did not impose a deadline, and `h.status` is a method,
not a status value. The corrected `h.wait({timeout: 0.001})` raised
`TimeoutError`; `await h.cancel()` returned true and `await h.status()` returned
`cancelled`. The applied local-worker skill now gives the verified object-form
wait and method-form status. Skill source/live validation passed after correction.

## Prompt, cloud effort and sampling experiments — 2026-09-22

The user requested these three experiments, leaving unforced routing observation
to ordinary OMP use. Twenty-eight worker-only attempts used fresh sessions,
scoped read/edit/write tools, fixed public contracts and independent parent
graders. There were no acceptance-driven repairs or checker exposure. Tool-use
retries remain included in usage. Director overhead is excluded from this
screen; these figures must not be presented as subscription allowance savings.
The config/frame seed implementations failed their graders and references
passed before local trials. The repository summarizer reused the previously
validated six-check grader.

### Lean native prompt: not promoted

Both arms used the official isolated OMP 18.2.8 Darwin arm64 binary, not an
old-stock/new-lean comparison. Its SHA-256 matched the release API:
`cf8d34a7fe6f60de1acbe74f29c82026e4c07888e9d89f7ebceeb922159e5787`.
The template retained live rules, skills, tool inventory/device documentation,
explicit privacy and scope boundaries, and parent verification. Native generated
project/context/safety blocks and provider tool schemas remained intact.
General director/personality/delegation/workflow prose was shortened.

Config merging and incremental frame decoding each ran twice per arm, with
seeds 42 and 31415 and stock/lean then lean/stock order. Model, medium reasoning,
min-p 0.05 and other sampling controls were identical.

| Metric, four attempts per arm | Stock | Lean |
| --- | ---: | ---: |
| Accepted attempts | 4/4 | 4/4 |
| Median first-request input including cache | 6,394.5 | 4,906.5 |
| Total generated output tokens | 5,436 | 6,427 |
| Model calls | 13 | 15 |
| Total elapsed seconds | 194.8 | 196.9 |

The initial prompt shrank 23%, but output increased 18% and elapsed time did
not improve. Smaller prompt size alone did not earn production adoption.
Keep the stock prompt and shared 18.2.6 pin. No global template was installed;
the tested CLI template is not a verified per-nous-agent configuration route.

### Luna low: supports routine cloud work, not a global downgrade

Config merging, frame decoding and the real repository summarizer each ran
twice at explicitly selected `low` and `medium`, avoiding the coarse `med`
mapping. Both arms used OMP 18.2.6 with rules/skills/extensions/title helpers
disabled and no director invocation.

| Metric, six attempts per arm | Low | Medium |
| --- | ---: | ---: |
| Accepted attempts | 6/6 | 6/6 |
| Output tokens | 5,355 | 9,342 |
| Input tokens including cache | 162,270 | 185,549 |
| Model calls | 25 | 27 |
| Tool errors | 0 | 3 |
| Total elapsed seconds | 148.7 | 298.4 |

Low used 43% less output and 13% less processed input; it passed every matched
contract and emitted fewer output tokens in each pair. The runner used
low-then-medium blocks in both repeats, not the planned balanced order.
Cache/order effects and shared provider variability therefore limit timing
and cost inference. This strengthens the existing `lo` choice for routine
cloud work; uncertain diagnosis, unresolved design and failed-local-repair
escalation retain configured medium. The generic Luna role was not downgraded.

### Qwen min-p: promote zero for native OMP requests

On pinned OMP 18.2.6, config merging and frame decoding each ran twice per
arm with matched seeds 42/31415 and reversed arm order on the second repeat.
Actual outgoing requests verified medium reasoning, temperature 1, top-p 0.95,
top-k 20, the seed and min-p. Only min-p differed within each pair.

| Metric, four attempts per arm | min-p 0.05 | min-p 0 |
| --- | ---: | ---: |
| Accepted attempts | 2/4 | 4/4 |
| Output tokens | 4,287 | 6,989 |
| Model calls | 12 | 12 |
| Total elapsed seconds | 202.4 | 197.2 |

Both 0.05 failures aliased mutable input state in config merging; inspecting
the artifacts confirmed the grader's counterexamples. Zero did more generation,
not less, but delivered accepted implementations without repair. The
[Qwen recommendation](https://huggingface.co/Qwen/Qwen3.8-27B) also specifies
min-p zero for thinking. This small screen supports alignment, not a general
claim that zero doubles reliability; stock 18.2.8 also passed the config cases
at 0.05 in the separate prompt experiment.

Set only Qwen's native OMP `modelOverrides.compat.extraBody.min_p: 0`.
No fixed seed, other sampler change, host service restart or server-default
change was promoted. OpenCode and other clients retain server defaults.
The applied native smoke's live llama.cpp slot reported min-p 0.0 with the
ordinary random seed and other existing sampling defaults.

Raw plans, wire metadata, events, artifacts, graders and aggregates are private
under `/tmp/omp-tuning-local/`, `/tmp/omp-tuning-luna/` and
`/tmp/omp-tuning-prompt/`. No credentials were copied into the isolated local
profiles. The temporary loopback wire observer is experiment-only.
The model override and updated local-worker evidence were applied on MacBook;
no commit, push, remote rollout or shared version upgrade was performed.

Post-apply verification: a fresh native OMP 18.2.6 Qwen smoke, using live
configuration and the ordinary random seed, passed all three config-contract
checks in 129.8 seconds. The server's default min-p remained 0.05; only the
OMP request used zero. Skill source/live validation passed. Strict baseline
validation passed configuration/discovery/pin/format checks and exited 1 solely
for the preserved pre-existing untracked `commands/draft.md`. The temporary
wire observer was stopped after experiments; no experiment service remains.

## Behavioral tests

| Test | Observed result | Implication |
| --- | --- | --- |
| Direct Luna C++ row-byte repair including `SIZE_MAX` | Correct; compile/run passed; 4 model calls | Capable default on this fixture |
| Native prewalk, same fixture | Correct; 8 Astra + 3 Luna calls | Additional planning increased work here; leave off |
| Direct original Ornith repair | Incorrect ceil-div expression | Local transport success is not coding success |
| Astra → native Ornith corrective child | Specified quotient/remainder edit; 21.6 s; parent compile/run passed | Native local delegation works with a bounded, checkable brief |
| Luna → native Gemma original repair | Overflow at `SIZE_MAX`; parent detected failure | Do not promote local models to algorithmic defaults |
| Bonsai through native OMP | Read JSON, wrote exact ordered CSV; independently checked | Manual local provider works; llama.cpp restored afterward |
| Native OpenRouter GLM 5.3 Flash | Returned required sentinel | Existing optional provider works |
| Luna → native `architect` | Astra medium child completed; main received result | Explicit consultation works through native RPC/task |
| Native RPC steering | Active turn consumed steering and returned the new sentinel | Steering works without a custom orchestration layer |
| Native OMP computer capability probe | Quartz capture/input/AX/background-window input available, permissions granted | Computer use capability remains; this probe is not a full desktop workflow test |

The prewalk fixture's reported traffic was 68,992 Astra + 31,177 Luna tokens;
direct Luna reported 25,573. These include cached input and are not a measurement
of subscription allowance debited. The runs are small behavioral checks, not a
statistically reliable ranking or a general estimate of quota savings. The
remaining local-model screening and proposed Harbor/SWE-bench/BFCL admission
strategy are in [the nous evaluation](nous-model-evaluation-2026-09-19.md).

## Jev, Laya, and DiffusionGemma

Jev is a decision model, not a normal coding/chat worker. Its OpenRouter endpoint
is `/api/alpha/decisions`. A matched synthetic triage probe covering extraction,
ordinary code, hard diagnosis, explicit overrides and missing context matched
all 12 manually assigned labels. Latency was 253–376 ms; reported total cost was
$0.000268506. This proves a useful API path on these examples, not that the chosen
worker will finish a real repository task or that confidence is calibrated here.

`omp-triage 'explicit request text'` offers one optional decision using the existing
OpenRouter key. It sends only supplied text, makes no changes, executes nothing,
uses no retry, and does not run automatically on turns. Do not send private/local-
only task content to this cloud helper merely because the desired worker is local.
A returned label is advisory; it cannot override explicit user choice, permissions,
missing context, or evidence of failure.

Both relevant Laya checkpoints were installed and tested in an isolated CPU
venv on nous, with four Torch threads and CUDA disabled:

| Checkpoint | Expected routes | Warm median / max | Cold load | Peak process RSS |
| --- | ---: | ---: | ---: | ---: |
| General English | 7/12 | 315.8 / 337.2 ms | 8.28 s | 2.92 GiB |
| Typed decisions | 7/12 | 316.8 / 338.3 ms | 8.61 s | 2.89 GiB |

Both routed the ambiguous DMA architecture and repeated failed diagnosis to
Luna rather than Astra, and failed the vague-request retain case. They differed
on extraction, UI work, research, and continuation. These labels reflect our
policy, not measured downstream task success. The cases and rubric matched Jev;
no fine-tuning or repeated rubric edits were used to chase the expected labels.
All option text fit the measured 208-token decision head. The English head
budget was raised from 192 to 256 to avoid clipping; states were at most 36
tokens. The tested input fit both checkpoints without truncation.

**Decision: keep Laya available for experiments; do not put it in the automatic
routing path.** It fits the host and avoids the GPU, but did not demonstrate the
routing reliability needed here. Jev's 12/12 on the same small fixture supports
retaining it as an optional advisory helper, not mandatory middleware. No extra
classifier call is added to ordinary work.

The isolated environment is `~/.local/share/nous-triage-eval/` on nous. There is
no Laya service or listener, and no inference process remains after the test.
Stock llama.cpp stays active. [Synthetic fixtures, result records, dependency
pins and reproduction instructions](../utils/nous/triage-eval/README.md) are
preserved in the repository; model weights remain on nous.

The current OpenJev/DiffusionGemma implementation documents NVIDIA/vLLM
(24 GB or more) and Apple/MLX backends, not a supported R9700 backend.
The old RTX 3080 10 GB exclusion is obsolete: nous now has an R9700 32 GB.
Memory alone is not the remaining blocker; runtime compatibility, GPU contention
with the coding model, and unproven downstream routing benefit remain.
No weights were downloaded and no Mac inference service was introduced.

## Evidence and interpretation

- [OMP 18.2.6 release](https://github.com/can1357/oh-my-pi/releases/tag/v18.2.6): reviewed pinned runtime. Local source checkout at commit `78b753124d11f8dd3ae73e2524125890ff7c977e`.
- [TwinRouterBench](https://arxiv.org/html/2605.18859v1): trained routing can reduce API spend while preserving benchmark success, but a rule-based router in the same experiment cost more. This does not establish savings for our subscriptions or models.
- [Advisor strategy](https://claude.com/blog/the-advisor-strategy): evidence for selective strong-model consultation. OMP's background advisor is a different implementation and remains off.
- [Jev on OpenRouter](https://openrouter.ai/typesafe/jev-1.13), [TypeSafe decision concepts](https://docs.typesafe.ai/concepts/system-one): typed decisions and pricing. No ordinary chat endpoint assumption.
- [Laya source and limitations](https://github.com/NandhaKishorM/laya), [typed checkpoint](https://huggingface.co/convaiinnovations/laya-typed-decisions): small encoders, token budgets, domain-specific fine-tuning and calibration caveats.
- [OpenJev](https://github.com/razorback16/openjev), [NVFP4 checkpoint](https://huggingface.co/nvidia/diffusiongemma-26B-A4B-it-NVFP4): reviewed implementation and hardware feasibility.
- [Compact OMP fork](https://github.com/vinicius91carvalho/oh-my-pi/tree/compact-prompt-for-local-models): source of experimental prompt settings, not the installed upstream schema.

Raw test events are private local artifacts under `/tmp/omp-migration-20260919/`.
They include native model IDs/tool traces; do not publish complete session events
or authentication material. Portable reproduction material contains synthetic
fixtures only. No firmware changes, flashes, live Pokémon campaigns, or inference
host workstation bootstrap were part of this migration.

## Validation and rollout boundary

The candidate passed core OMP policy, model discovery, private runtime
permissions, shared skill projections, source-skill audit, baseline pin/syntax
checks, and focused triage/usage collector tests. The strict source-tracking
gate remains pending solely because the pre-existing untracked
`home/private_dot_omp/private_agent/commands/draft.md` is reported as PENDING;
that unrelated user work was preserved and not staged or normalized.
The exported source skills were also audited independently.

MacBook configuration is applied. T14's SSH check timed out; Linux Omarchy live
validation and remote rollout remain unverified. Mac Mini was not changed or
validated in this migration. The published baseline is available through the
usual `omp-baseline pull` workflow; OAuth login remains local to each machine.

## 2026-09-22: OMP 18.2.8 and independent knob trials

This follow-up supersedes the earlier pending draft-depth/read-summary gates;
it does not repeat or change the automatic-routing experiment. Astra remains
the director, with one explicit Nous worker at a time and Luna for broader work.

Four knobs were tested separately before promotion:

| Knob | Evidence | Decision |
| --- | --- | --- |
| MTP depth 2 vs 3 | Four complete, independently graded answers per arm; both 4/4. Median end-to-end 10.586s vs 9.386s; mean decode 55.48 vs 62.59 tokens/s. | Keep 3. Depth 2's higher draft acceptance did not improve throughput. |
| Microbatch 512/1024/2048 | Two cold/warm cycles per arm, reversed order, 19,250-token prompt; all 12 answers passed. Mean native cold prefill 22.338/21.535/21.827s. | Promote 1024: 3.6% lower cold prefill than 512. No robust warm-cache gain claimed. |
| Nous structural reads off/on | Two real files, two seeds, balanced order; 4/4 independently graded edits per arm. Aggregate duration 181.578/157.320s; input including cache 146,619/129,844 tokens; output 7,293/6,885. | Enable `readSummarize`. Summaries actually elided bodies; explicit recovery reads increased. |
| Native shake before remote compaction | Two paired stress runs per arm, then a larger-history control; all retained the requested facts, constraints and URI. | Keep `[remote, handoff, soft]`; do not enable shake. |

Structural reads reduced aggregate elapsed time 13.4% and input including cache
11.4% in this small screen; one TypeScript seed was slower, so this is not a
universal latency claim. Real source repositories were not modified by trials.

Shake reclaimed about 4,607 tokens per stress run, but still fell through to
remote compaction: mean 71.181s versus baseline 43.913s, with six versus four
successful remote compactions across the two runs. The larger control reclaimed
33,883 tokens yet still needed remote compaction: 34.605s versus 22.903s.
Recovery reads added work. Main-model usage excludes unexposed compactor usage;
neither those counts nor cache differences establish subscription charges.

The GPU trials held Qwen3.8-27B Q5_K_M, native b11046 Vulkan, 64K context,
q8 KV, medium reasoning and sampler settings fixed. Complete final answers,
not truncated reasoning, were graded. Initial harness-development runs with
an incorrect extraction oracle or short output cap were excluded.
Each trial restored the original preset before the final promotion.
Microbatch 1024 retained MTP depth 3 and left about 10.44 GiB VRAM free;
no OOM or health failure was observed.

Raw local evidence is under `/tmp/omp-ecosystem-upgrade/`:
`20260922T164004Z-mtp-ubatch/`, `read-real/`, `shake/`, and
`promotion.json`. These are machine-local experiment artifacts, not a durable
shared storage promise. The promoted preset's SHA-256 is
`ea1399e5f9cd9029b8e64e3e584adf22c1829b8efb5b1e3fbdf4747a29873886`;
the original is backed up on Nous under
`~/.local/state/omp-upgrade-18.2.8/models.ini.before-ubatch1024`.

## 2026-09-22: second isolated trial round

Native OMP 18.2.8 remained pinned. Each comparison changed one setting within
its fixture; no automatic routing, T14 rollout, model download, or cloud
fallback was added. Cloud runs used Astra medium. Local runs used Qwen3.8-27B
Q5_K_M, b11046 Vulkan/RADV on the R9700, 64K context, MTP 3 and microbatch
1024. Balanced orders reduce drift but these small screens are not a general
coding benchmark or proof of subscription savings.

| Setting | Observed result | Decision |
| --- | --- | --- |
| Astra Code Mode off/on | Two coding fixtures, two repetitions: 4/4 behavior passes per arm. Mean 39.055/81.076s; total input including cache 276,621/658,678 tokens; output 3,069/7,307. Code Mode actually used the eval bridge; both API runs retried malformed nested edit requests. | Keep off. No quality gain, substantially more time and prompt traffic. |
| Speculative tools off/on, max in flight 2 | Two fixtures: 2/2 passes per arm; mean 37.831/38.534s. Native event output did not expose speculative admission/commit telemetry, so actual early-read reuse is unproven. | Keep off; no demonstrated benefit, not proof that speculation never helps. |
| Local LSP off/on | Eight multi-file migrations with aliases, namespace calls and an unrelated same-name function; 4/4 behavior and TypeScript passes per arm. Mean 54.613/67.378s. Three on-arm runs called LSP references. | Do not enable LSP globally for Nous workers. This direct-CLI screen did not test native task-child activation or larger repositories. |
| KV q8/f16 | Two lengths (~19K/~45K), two seeds, balanced order; 4/4 strict passes per arm. Mean 42.725/41.644s; f16 used about 1.70 GiB more VRAM. | Keep q8: only 2.5% elapsed improvement, no observed quality gain, less headroom. |
| Checkpoint spacing 8192/1024 | Six user-message blocks (~19K tokens), two repetitions per arm, cold/branch/append: all 12 strict answers passed. Branch mean 26.727/20.318s; TTFT 23.149/16.959s; reused prefix 26/6,468 tokens. | Promote 1024; keep default checkpoint count 32. |

The checkpoint improvement is branch-specific: cold means were 25.668/26.474s
and append means 2.462/2.603s, neither an improvement. An earlier same-message
mutation screen showed no gain (12.362/12.382s mean): the
[b11046 checkpoint placement logic](https://github.com/ggml-org/llama.cpp/blob/b11046/tools/server/server-context.cpp)
favours user-message boundaries and near-end checkpoints. That earlier screen
had 3/12 strict JSON-integer passes per arm because the prompt allowed numeric
strings; numeric values matched in all 24 responses. It is not quality evidence
for promotion. The multi-message control explicitly required JSON numbers.

Each GPU comparison restored the original preset before the next trial.
After local LSP runs finished, only `checkpoint-min-step = 1024` was added to
the Qwen preset in `utils/nous/models.ini` and on Nous. Idle-slot and original
hash guards preceded the restart. The loaded model arguments and health were
checked; a subsequent native OMP migration passed independent behavior and
TypeScript checks in 71.349s. No error-free tool trace claim is made: that run
recovered from four tool errors. The new preset SHA-256 is
`1b2fae85251cee7dea9d752256a52d51c0238549410d1d5f8fb7e9f2fd5001f9`.
Rollback bytes are on Nous at
`~/.local/state/omp-upgrade-18.2.8/models.ini.before-checkpoint1024`.

### Background completion cascade

The official native 18.2.8 binary reproduced
[issue 12869](https://github.com/can1357/oh-my-pi/issues/12869) using a local,
scripted provider: one explicit asynchronous job caused both following 80ms
foreground bash calls to report early backgrounding, without user steering.
Four provider requests completed, exit 0, no stderr; the temporary loopback
service was stopped. A separate source-level simulation eliminated the cascade
with the candidate logic, but that is not validation of a patched native binary.
[PR 12874](https://github.com/can1357/oh-my-pi/pull/12874) was still open and
unmerged at inspection. Keep the official pin; do not mask the bug by disabling
background work or changing timeouts.

Raw evidence remains machine-local under `/tmp/omp-round2/`: `code-mode/`,
`lsp/`, `gpu-summary.json`, `checkpoint-turns-summary.json`, `async/`,
`checkpoint-promotion.json` and `promotion-smoke.json`. These temporary paths
are not a durable artifact-storage promise. `omp-baseline validate --strict`
passed after promotion; shared OMP defaults and cloud roles remain unchanged.

### Notes-backed context versus remote compaction

Eight balanced native RPC runs resumed synthetic ~41.5K-token coding histories:
two task families (URL canonicalization and a one-pass event index), two
repetitions, identical 32K rollover threshold and 8K retained tail. Only
experimental context management and its required notebook tools differed.
This deliberately stressed rollover; production thresholds were not changed.
Early contracts, rejected approaches and artifact paths were in the history,
not repeated in the final implementation request.

All eight final source artifacts passed the same independent behavioral
grader. Notes completed 4/4 runs before the deadline; baseline completed 3/4,
with one correct artifact but no final agent end before the 240s deadline.
Measured process elapsed, including shutdown, averaged 166.554s baseline and
165.268s notes. The first repetition favoured notes; the second favoured
baseline on both tasks. Notes actually updated the notebook and performed 13
rollovers across four runs, with repeated raw-history recovery reads; baseline
performed four provider-native remote compactions. Main-model usage excludes
unexposed remote-compactor usage, so no cost comparison is claimed.

**Keep notes-backed management off by default.** Recovery worked, but the
mixed per-run latency, repeated rollover churn, and effectively equal aggregate
elapsed do not justify a global context-semantics change. The one completion
deadline difference is a signal, not established reliability improvement.
Retain `[remote, handoff, soft]` and the existing automatic thresholds.

Only `notes/runs/final-*` are comparison runs; earlier harness-development
attempts were excluded. Final grading removed an undocumented surrounding-space
normalization requirement and added explicit contract checks for trailing DNS
dots, control characters and unknown-lookup isolation. Every final artifact
was regraded identically; both unmodified templates fail. Compact results are
in `/tmp/omp-round2/summary.json`; full native events remain private in `notes/`.
The notebook's [16 KiB bound and recovery semantics](https://github.com/can1357/oh-my-pi/blob/v18.2.8/packages/coding-agent/src/session/context-notes.ts)
were reviewed, but this screen did not establish broad resume/branch safety.

## 2026-09-22: third round — hardware and serving

The earlier f16 rejection overweighted unused VRAM. Replicated long-context
measurements now justify f16 for Qwen; the global smaller-model default stays
q8_0. Context/output limits remain 65,536/8,192. No driver, firmware, clock,
power-cap, CPU-governor or binary upgrade was made.

### Controlled results

All serving comparisons serialized GPU requests, retained MTP depth 3 and
microbatch 1024, and restored the original preset between experiments.
KV used balanced q8/f16/f16/q8 order with two seeds; the other screens held
f16 constant. These are narrow workload measurements, not confidence intervals
or a claim of uniformly faster coding.

| Experiment | Evidence | Decision |
| --- | --- | --- |
| q8 versus f16 KV | 22/22 answer checks passed, including 62,265 prompt tokens. At ~55K, mean prefill 72.534/70.223s (3.2% shorter); elapsed 76.553/74.124s. Near-limit elapsed 90.480/86.733s. Peak f16 VRAM 23.39 GiB, leaving 8.47 GiB. | Promoted f16 in the live Qwen preset and source. |
| Short-prompt generation, q8/f16 | Mean elapsed 17.571/17.982s; f16 was 0.41s slower despite slightly higher reported decode throughput. | Do not claim universal latency improvement. |
| Native OMP coding, q8/f16 | Four migrations all passed behavior and TypeScript checks. Means 66.490/75.647s; one f16 run made four incorrect-path edits and recovered. Output lengths also differed. | Behavioral validation, not evidence of a coding wall-time win. Read headers contained the correct paths; no harness workaround added. |
| Logical batch 2048/4096/8192 | 12/12 answers passed. ~55K cold means 73.594/74.064/74.198s. | Retain 2048; larger batches did not help. |
| Vulkan versus installed HIP | Same b11046 commit/compiler, f16, MTP and prompts. Two runs each: cold means 23.245/23.973s; sustained-generation means 17.428/19.128s; decode 70.02/62.89 tok/s. | Keep Vulkan. This does not generalize to other models or ROCm builds. |
| RADV default versus `nocompute` | First balanced screen: generation 17.428/16.871s (3.2% shorter). Independent balanced confirmation: 17.383/16.907s (2.7% shorter), 70.23/72.34 tok/s. Child environment explicitly verified in confirmation. Both full screens passed 18/18 answers. | Stage service-scoped environment setting; live installation requires interactive sudo. |
| Actual P-core affinity | All model threads pinned to logical CPUs 0,2,4,6,8,10,12,14, verified before and after requests. Two runs: cold 23.202s versus unrestricted 23.130s; generation 17.346/17.383s. | No meaningful gain; retain unrestricted placement. |

The first native `cpu-mask`/`cpu-strict` screen was ineffective: every thread
remained allowed on CPUs 0–31 despite the flags appearing in model arguments.
It is not performance evidence for placement. Launch-time taskset also left
three threads unrestricted; the final screen applied taskset to all existing
threads after load. Aborted placement runs and a runner attempt that failed
to terminate its SSH child are excluded. The orphaned experimental router was
explicitly stopped; final comparisons used remote PTYs and waited for exit.

### Hardware and upstream findings

PCIe negotiated 32 GT/s ×16. Host available RAM was approximately 25 GiB.
The initial loaded junction reading was 58 C; sustained trials reached 94 C,
below the reported 110 C critical threshold. This does not establish absence
of all clock throttling. The configured power cap was already its 300 W
maximum. No evidence justified changing power/fan controls.

The [R9700 community guide](https://github.com/aguaishuo/AMD-Radeon-AI-PRO-R9700-llama-cpp-Vulkan-MTP)
provided the queue hypothesis, not transferable performance proof.
[Pinned Mesa source](https://raw.githubusercontent.com/chaotic-cx/mesa-mirror/mesa-26.0.8/src/amd/vulkan/radv_instance.c)
maps `nocompute` to disabling the separate compute queue; it does not disable
GPU computation. The [ROCm/Vulkan comparison](https://www.phoronix.com/review/rocm-71-llama-cpp-vulkan/4)
motivated testing the already-installed matching HIP binary rather than
installing another stack. [Kernel power-control documentation](https://docs.kernel.org/gpu/amdgpu/thermal.html)
distinguishes DPM level `high` from the older power-state `performance` knob.

llama.cpp v0.4.1 was older than installed b11046; advertised Vulkan fixes in
that release were already present. Newer nightly commits did not establish
a benefit for this GPU. Inspection of
[b11046 speculative decoding](https://raw.githubusercontent.com/ggml-org/llama.cpp/b11046/common/speculative.cpp)
also ruled out `spec-draft-p-split` as a useful MTP experiment: that strategy
does not consume it. No unmeasured cache-reuse or speculative setting was
promoted.

OMP [PR 12874](https://github.com/can1357/oh-my-pi/pull/12874) remained unmerged
at inspection. The final validator discovered release
[18.2.9](https://github.com/can1357/oh-my-pi/releases/tag/v18.2.9);
it was not installed or benchmarked. The active pin remains 18.2.8.

### Deployment and verification

Live preset SHA-256:
`1f865c33bd4080571cbbf9261b1f4bc9e278e5099357b80de0fa877fa449b063`.
Rollback: `~/.local/state/omp-upgrade-18.2.8/models.ini.before-round3` on Nous.
An idle-slot guard delayed promotion until existing inference finished.
After promotion, cold/branch/append answer checks all passed; the branch
reused 6,468 tokens and completed in 19.111s. This is a smoke check, not
another controlled checkpoint comparison.
A subsequent native OMP multi-file migration completed in 73.135s with zero
tool errors, an agent-end event, and passing independent behavior and
TypeScript checks. Final process inspection confirmed f16 K/V, unchanged
64K context, unrestricted CPU affinity and no live RADV override.

The queue setting is staged in `utils/nous/llama.service` and on Nous at
`~/.local/state/omp-upgrade-18.2.8/llama.service.round3`, but **not live**.
`sudo -n true` failed with interactive authentication required. Passwordless
service restart permission does not authorize unit installation. At an idle
maintenance point, the administrative install is:

```sh
ssh -t nous
sudo cp -a /etc/systemd/system/llama.service /etc/systemd/system/llama.service.before-round3
sudo install -m 0644 ~/.local/state/omp-upgrade-18.2.8/llama.service.round3 /etc/systemd/system/llama.service
sudo systemctl daemon-reload
sudo systemctl restart llama.service
```

Verify loaded health and the model child's `RADV_DEBUG=nocompute` environment
after that step; the current deployed performance must not include its gain.
`omp-baseline validate --strict` checked matching live configuration, secrets
boundaries and pin, but exited 1 because the pre-existing portable
`agents/astra.md` source is untracked. No staging/commit was authorized.
Evidence remains temporary under `/tmp/omp-round3/`: `kv/`, `kv-agent/`,
`batch/`, `backend-*`, `clean-*`, `promotion.json`, `branch-smoke.json` and
`final-native/`.

## 2026-09-22: fourth round — EXL3 compatibility, context and vision

### The Twitter chart is not a VRAM-only recipe

EXL3 is ExLlamaV3's trellis/codebook quantization format, derived from QTIP;
it is not a GGUF quant or a llama.cpp switch.
[Upstream description](https://github.com/turboderp-org/exllamav3/blob/master/doc/exl3.md).
The chart's 32 GB row names an RTX 5090, whereas Nous has an AMD R9700.

The requested
[`malaiwah/Qwen3.8-27B-EXL3-K5K6-hydrated` card](https://huggingface.co/malaiwah/Qwen3.8-27B-EXL3-K5K6-hydrated)
requires the custom Gilded Gnosis vLLM runtime, explicitly excluding stock
vLLM, llama.cpp, transformers and stock ExLlamaV3. Its own capacity table
puts hydrated K5K6 around 180K on 32 GB; 262,144 belongs to the separate
K5K6-context edition. Its fidelity figures have protocol/provenance caveats
and are not general task-quality or cross-hardware speed guarantees.

This is a **GPU/runtime-port compatibility blocker, not a missing installable
dependency**. The fork's
[ROCm platform admission list](https://github.com/local-inference-lab/vllm/blob/dev/gilded-gnosis/vllm/platforms/rocm.py)
does not include `exl3`. Its published CUDA stack and
[B12X kernels](https://github.com/local-inference-lab/b12x)
target NVIDIA hardware, including SM120/121 Blackwell. Installing CUDA does
not give an AMD GPU NVIDIA execution support.

[ExLlamaV3 ROCm PR 365](https://github.com/turboderp-org/exllamav3/pull/365)
and stacked PRs 366/367 document R9700 build, fallback and kernel-port work,
but were unmerged at inspection. That is a different runtime and does not
establish support for the requested hydrated artifact. No 21.61 GB EXL3
weights or incompatible CUDA container were downloaded. Running this exact
recipe needs compatible NVIDIA hardware or additional AMD runtime/kernel
porting; the experiments below are explicitly **not an EXL3 benchmark**.

### Existing GGUF: larger context plus vision

Downloaded only the matching projector from the already-pinned
`unsloth/Qwen3.8-27B-GGUF` revision
`4ca720788d1e01f1bff70c033e0d0028fd02e502`:
upstream `mmproj-F16.gguf`, stored on Nous as
`/srv/models/Qwen3.8-27B-mmproj-F16.gguf`.
Size 927,607,488 bytes; SHA-256
`cbb841a9ee0636b2ec172f5bb8df2ea8dfeb01e90fe7c6126581d662a0b4e43e`,
verified on host and recorded in `utils/nous/model-artifacts.json`.
A 32 MiB sample measured 8.29 MB/s, predicting 108 seconds remaining; the
resumed remainder took 90.6 seconds. The download ran asynchronously while
independent work proceeded; long inference waits used timed sleeps.

The API capacity screen kept b11046, Vulkan, MTP3, microbatch/checkpoint
spacing 1024 and one slot. Added `mmproj` above and
`mmproj-device = Vulkan1`. The base model's
[native position limit](https://huggingface.co/Qwen/Qwen3.8-27B/blob/main/config.json)
is 262,144; no RoPE/YaRN extrapolation was added.
Each long request asked for three exact integer values near the beginning,
middle and end of a generated table, plus counts in a 480×240 synthetic
image. Warm follow-ups repeated the answer. These are capacity/retrieval
smokes, not replicated performance comparisons or comprehensive quality tests.

| Configured context / KV | Actual cold prompt tokens | Cold elapsed | Warm elapsed | Peak VRAM | Cold-answer decode |
| --- | ---: | ---: | ---: | ---: | ---: |
| 65,536 / f16 | 19,329 | 24.088s | 2.759s | 24.50 GiB | 59.68 tok/s |
| 131,072 / f16 | 119,605 | 203.572s | 2.978s | 29.00 GiB | 48.56 tok/s |
| 262,144 / q8_0 | 248,930 | 716.801s | 7.327s | 31.44 GiB | 27.45 tok/s |

All six image/retrieval answers and the separate ~1,100-token generation
fixture passed, with speculative draft/acceptance counters confirming MTP
engagement. Two additional same-text/different-image controls also passed:
three red squares/two blue circles versus one red square/four blue circles.
JSON integer/boolean types were audited, not just Python numeric equality.

The longest profile left only **0.424 GiB free at observed peak**. This does
not establish safety for larger images, maximum output, multiple requests or
an entirely full 262,144-token prompt. It does not approach the chart's
155–212 tok/s claim on our workload/hardware. Enabling a projector also makes
b11046 disable context shifting and cache-reuse according to
[the server implementation](https://github.com/ggml-org/llama.cpp/blob/b11046/tools/server/server-context.cpp).
**Retain 64K/f16 text-only as production.** The projector remains available
for explicitly configured experiments; client catalogs were not changed.

### Remaining serving and OMP settings

MTP confidence threshold `spec-draft-p-min` is consumed by
[b11046 draft-MTP](https://github.com/ggml-org/llama.cpp/blob/b11046/common/speculative.cpp).
Six balanced arms (0, 0.5, 0.8, 0.8, 0.5, 0), identical seed and prompts,
passed 18/18 cold/warm/generation checks:

| Threshold | ~19K cold | Warm | Generation fixture | Generation decode |
| --- | ---: | ---: | ---: | ---: |
| 0, current default | 23.596s | 1.432s | 16.832s | 71.79 tok/s |
| 0.5 | 23.726s | 1.496s | 16.895s | 71.50 tok/s |
| 0.8 | 23.831s | 1.274s | 16.703s | 71.83 tok/s |

At 0.8, generation drafted/accepted totals fell from 1,698/1,662 to
1,666/1,660; output length also changed by one token. A 0.8% shorter
generation fixture with slightly slower cold requests is not a clear general
win. Keep threshold 0 rather than promoting on acceptance ratio alone.

OMP 18.2.8's
[`appendOnlyContext=auto` resolver](https://github.com/can1357/oh-my-pi/blob/v18.2.8/packages/coding-agent/src/config/append-only-context-mode.ts)
already returns true for `llama.cpp`. Setting it to `on` would not create a
new local optimization, so no redundant A/B was run.

An isolated native Astra coding screen compared 8K/4K recent-token retention
with the same resumed history and 32K compaction trigger. Both completed
tasks passed the independent grader (189.417/174.875s), but both remote
compactions processed **56,392 input tokens**. The
[pinned implementation](https://github.com/can1357/oh-my-pi/blob/v18.2.8/packages/agent/src/compaction/compaction.ts)
concatenates summarized, turn-prefix and recent partitions before native
remote compaction. The local cut point changed, but the proposed reduction
in remote input did not occur. The remaining batch was cancelled, all child
processes exited, and no timing win is attributed to this setting. This does
not rule out effects on later replay or local/handoff compaction. Keep 8K.

Research found OMP 18.2.9 correctness changes, not a demonstrated performance
gain; [PR 12874](https://github.com/can1357/oh-my-pi/pull/12874) remained open
and absent from that release. No OMP/runtime/driver upgrade, power tuning,
root-unit installation or shared config change was made. The previously
measured RADV override still awaits interactive sudo installation.

Every completed GPU screen restored the exact production preset SHA-256
`1f865c33bd4080571cbbf9261b1f4bc9e278e5099357b80de0fa877fa449b063`.
Final health/model inspection confirmed the loaded 64K/f16 text-only profile.
Machine-local evidence: `/tmp/omp-round4/{pmin,capability,vision-contrast,
retention,exl3-compatibility.json,restored-state.json}`. Temporary experiment
scripts and traces are not deployed services or a durable benchmark suite.
A final native OMP multi-file migration on the restored production service
completed in 82.949s with an agent-end event and passing behavior/TypeScript
checks. It recovered from four tool errors; it is not an error-free trace or
a performance comparison. The artifact manifest parses, and the router's
six-model catalog remained unchanged.

## 2026-09-22: matched context-size follow-up — promote 128K/f16

This supersedes the fourth round's decision to retain 64K. The 203.572-second
vision result processed 119,605 tokens, which cannot fit at 64K; comparing
that result to an ordinary short production request would confuse work size
with configured capacity. A matched text-only comparison was needed.

Changed only `ctx-size`: balanced 64K/128K/128K/64K order, two repetitions
per arm, identical seed/prompts, f16 K/V, same model/build/device, MTP3,
microbatch/checkpoint spacing 1024, no projector and no RADV override.
All 20 strict answer checks passed.

| Identical workload | 64K mean | 128K mean | Change |
| --- | ---: | ---: | ---: |
| ~19K cold prompt | 22.980s | 23.080s | +0.43% |
| ~19K cached follow-up | 1.774s | 1.807s | +1.88% / 33ms |
| ~55K cold prompt | 72.956s | 73.034s | +0.11% |
| ~55K cached follow-up | 2.229s | 2.229s | effectively unchanged |
| Short-prompt ~1,100-token generation | 18.131s | 18.201s | +0.39% |

Peak measured VRAM increased from 23.39 to 27.89 GiB, leaving **3.97 GiB**
free at 128K. This is a small controlled screen, not a statistical
non-inferiority claim or a whole-workflow benchmark. It supports doubled
capacity at marginal measured latency cost, **not a throughput speedup**.
Actual longer histories still take longer to prefill.

Promoted `ctx-size = 131072` in the canonical and live preset. f16 KV,
8,192 output, text-only input and all other serving controls are unchanged.
Updated the shared OMP/OpenCode catalogs, applied them on the MacBook, and
updated both Nous CLI and active Serve-profile catalogs. Fresh native model
discovery on all three OMP profiles reports 131,072 context / 8,192 output.
Existing processes may retain an old model object until a new session/reload;
other workstations have not received an unpublished fleet rollout.
Capacity references in shared skills were updated and their Codex projections
regenerated; no invocation/routing policy changed.

Live preset SHA-256:
`97402782f6b6c4d8de66adfb981c8e3b50230ab91600f16b3b06ec6f73d4297a`.
Service-preset rollback on Nous:
`~/.local/state/omp-upgrade-18.2.8/models.ini.before-context128`.
Both Nous client profiles also retain `models.yml.before-context128`.
Evidence: `/tmp/omp-context128/matched/`, `comparison.json`, and the
three `*-discovery.json` files. No commit/push or binary upgrade was made.

Post-promotion production smoke correctly answered a 119,465-token text-only
prompt in 199.092s and its 119,672-token cached continuation in 3.052s.
Peak VRAM was 27.88 GiB, leaving 3.98 GiB. A fresh native OMP migration with
the 128K catalog completed in 76.914s, passed independent behavior and
TypeScript checks, and emitted agent-end; it recovered from four tool errors.
Final live arguments confirm 131,072 context, f16 KV and no projector.
Applied MacBook catalogs match canonical source bytes. Strict baseline
validation passes config, skill/projection and format checks but still exits
1 solely for the preserved pre-existing untracked `agents/astra.md`.
