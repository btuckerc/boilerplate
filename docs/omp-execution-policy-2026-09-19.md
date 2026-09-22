# OMP execution policy and measured migration — 2026-09-19

This is the current OMP recommendation, superseding the earlier harness audit.
OMP 18.2.6 is installed and pinned. Start new work with `omp`; existing T3/Codex
threads keep their own settings. OMP talks directly to nous over Chat Completions.
OpenCode remains useful for the existing T3 Nous instance and `nous-worker`;
it is not a prerequisite for OMP local children.

## Execution policy

| Work | Default choice | Reason |
| --- | --- | --- |
| Routine implementation, tests, navigation, bounded debugging | Luna medium | Avoid a frontier planning turn before straightforward work |
| Ambiguous architecture, conflicting evidence, stalled diagnosis | Focused `architect` child, Astra medium (`@plan`) | Consult on the hard decision, then continue implementation |
| Explicit sustained frontier work | Astra medium; xhigh via `@slow` | Available without a mandatory classifier |
| Small mechanical transforms, extraction, predetermined edits | `nous` child / Ornith | Local tokens, short brief, independent exact checks |
| Manual alternatives | OpenRouter; Bonsai after explicit backend switch | Preserve provider choice without silent paid fallback |

The model cycle is `default` / `plan`. Routine work need not spawn a child.
A worker receives owned files, relevant facts and acceptance checks, not the
entire main transcript. Verify the resulting artifact once; repeat checks after
new changes/failures. The `architect` agent is read-only and does not delegate.
Only one nous GPU worker should run at a time. A local error does not authorize
an automatic cloud fallback or service switch.

This is a recommendation, not a benchmark claim that Luna always equals Astra.
A new Luna session answered our DMA ownership consultation directly and chose
hardware-terminal completion rather than `cancel()` return as the lifetime
boundary; it did not autonomously invoke `architect`. Routing instructions are
model behavior, not a deterministic automatic escalation guarantee.

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

- Luna medium for default/task/vision; Luna low for scout, commit, tiny roles.
  Astra medium for plan and xhigh for slow.
- `task.eager: default`, depth 1, concurrency 3, a 40-request soft worker budget
  and 10-minute runtime limit. Soft budgets are not hard token caps.
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

The reviewed OpenJev/DiffusionGemma path uses a 26B-parameter checkpoint despite
4B active parameters. The NVFP4 weights are roughly 18 GB; the implementation
requires at least 24 GB NVIDIA memory and experimental vLLM changes. That direct
path does not fit nous's 10 GB RTX 3080. No DiffusionGemma weights were downloaded.
An alternative CPU/offload implementation would need its own speed/quality test.

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

The reviewed Git candidate passed `omp-baseline validate --strict`, the shared
source-skill audit, baseline pin/syntax checks, and the focused triage/usage
collector tests. Live OMP policy, model discovery, private runtime permissions,
and shared skill projections passed. The full working checkout separately
reports the pre-existing untracked `commands/draft.md`; that unrelated work was
preserved and excluded from this commit. Candidate validation used its exported
source/manifest plus the actual live skill inventory, including the user's draft.
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
