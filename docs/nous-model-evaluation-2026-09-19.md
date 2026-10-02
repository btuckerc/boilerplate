# Nous model selection — 2026-09-19

This is a hardware-specific screening for T3/OpenCode coding assistance and
bounded experiment planning, not a general intelligence leaderboard. Nous has
an RTX 3080 with 10 GB VRAM, 32 GB system RAM, and an i9-13900K. Models run
serially; clients and file tools stay on the MacBook.

## DeepSeek V4.1 Flash

Do not deploy this model on the current nous. The official model card lists a
552B-parameter backbone plus 196B parameters of Engram conditional memory.
Only 8B/16B parameters activate per token during prefill/decode, but this does
not eliminate the need to store the remaining weights. Even an idealized
2-bit encoding of the backbone alone is 138 GB, before conditional memory,
quantization metadata, runtime buffers or KV cache. Nous has roughly 42 GB
of combined RAM/VRAM, which is not a single unified allocation pool.
Disk-streaming forks are an experimental possibility, not an appropriate
interactive worker for this hardware. No DeepSeek weights were downloaded
and no DeepSeek runtime performance is claimed.

Source: [DeepSeek's model card](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash).

## Candidates and exclusions

- **Bonsai 2 27B PQ2_0:** already installed, specialized ternary runtime,
  32K configured context. Larger parameter count does not establish accuracy.
- **Qwen 3.5 9B Q5_K_M:** installed general-purpose baseline, 16K context.
- **Nemotron 9B OpenCode Q6_K:** installed coding fine-tune; previous full
  harness tests failed tool use, so it must earn a recommendation behaviorally.
- **Gemma 4 12B Q4_0:** newer candidate with native function calling;
  downloaded from the llama.cpp organization's conversion repository.
  [Google model card](https://huggingface.co/google/gemma-4-12B-it),
  [GGUF source](https://huggingface.co/ggml-org/gemma-4-12B-it-GGUF).
- **Ornith 1.5 9B Q5_K_M:** recent Qwen-derived candidate targeting reasoning
  and agentic tasks. Publisher benchmarks are not assumed to transfer to this
  quantization and harness. [Publisher model card](https://huggingface.co/ornith-ai/Ornith-1.5-9B),
  [publisher GGUFs](https://huggingface.co/ornith-ai/Ornith-1.5-9B-GGUF).
- **Qwen 3.5 4B Q5_K_M:** smaller throughput candidate for bounded work.
  [Official model](https://huggingface.co/Qwen/Qwen3.5-4B),
  [quantization source](https://huggingface.co/unsloth/Qwen3.5-4B-GGUF).

Qwen 3.8 27B is a relevant quality candidate, but its ordinary 4-bit weights
exceed this GPU before context and runtime overhead; CPU offloading would
change the latency tradeoff. It was researched, not benchmarked here.
[Current quantized artifacts](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF).

K2 Horizon 7B is promising but its llama.cpp implementation is still a draft,
with correctness issues reported in the upstream discussion. It was not
selected as a dependable service candidate or installed in this session.
[Runtime support discussion](https://github.com/ggml-org/llama.cpp/discussions/28308).

## Method

`utils/nous/evaluate.py` runs five synthetic checks twice, with seeds 73/74:
interval merging, FIFO state tracking, dependency-constrained scheduling,
evidence-sensitive action selection, and a real two-turn tool interaction.
The scheduler's optimal answer is independently enumerated. Tool results
are fixed fixtures; no game actions or generated shell commands execute.
A pass requires the exact expected structured answer, not a plausible
explanation. Output is bounded to 2,048 tokens; truncation counts as failure
for that profile, not proof the model cannot solve the task with more time.

A separate long-context check retrieves an exact record from 350 distractor
records (about 10K tokens with Qwen). Its first and cached repeat timings
are retained separately; a cached repeat is not cold prefill performance.

Initial profiles use default thinking with temperature 0.2. Faster profiles
explicitly disable thinking and use temperature 0.7. Results retain these
settings: they are comparisons of practical configurations, not controlled
claims about model weights alone. Qwen also receives a diagnostic quality
profile with temperature 1.0 and an 8,192-token output allowance, one pass
per task, because the original profile often exhausted its reasoning budget.
Requests are serial and use each model's
native tokenizer. Server decode tokens/sec excludes prefill; task wall time
includes it and any model load. Different tokenizers make tokens/sec only an
approximate cross-model speed measure. Downloads ran in the background during
part of the screening, so this is not an isolated hardware microbenchmark.

`coding_eval.py` uses OpenCode 1.18.31 in a disposable directory with read/edit
file tools allowed and shell tools denied. The retained runner now isolates its
config and uses `opencode-screening-baseline.json` (the pre-evaluation baseline)
to prevent later live defaults changing a profile. It asks for repairs to two small
Python functions: merging interval windows without mutating inputs, and
selecting the cheapest legal, current, budget-fitting action with an ID tie
break. The generated implementation is inspected before `grade_code.py`
checks 410 fixed/randomized edge cases against independent reference logic.
These 410 checks cover two functions, not 410 independent coding tasks.
A partially passing implementation is still a failed repair. No production
repository, firmware, game save, or experiment campaign was changed.

Artifact revisions, exact file sizes and SHA-256 values are recorded in
`utils/nous/model-artifacts.json`. Results live under `utils/nous/results/`.

Additional diagnostic runs use Qwen/Ornith's recommended general sampling
(temperature 1.0, top-p 0.95, top-k 20, min-p 0, presence penalty 1.5,
repeat penalty 1.0), with 4,096 output tokens and one pass per task. These
are labeled `recommended`, separately from the fixed-budget screening.
[Qwen's sampling guidance](https://huggingface.co/Qwen/Qwen3.5-9B).

The faster coding candidates also receive one follow-up with the first two
independent test failures. Their total time includes both attempts; this
measures limited recovery with feedback, not first-attempt success. Generated
solutions and each attempt's tool events are retained for review.

## Firsthand community settings cross-check

A [3080 10 GB Qwen 9B MTP measurement](https://gist.github.com/sabriguenes/43ecb28e520a9fbf1e0e58d838a7b3dc)
reports 93.6 tokens/sec without speculation and 133.3 with two draft tokens;
four draft tokens performed worse. Our roughly 93 tokens/sec baseline is
consistent with that report. MTP is a plausible throughput follow-up, not a
fix for incorrect reasoning; that user's Q4 model/build differs from ours.
Those speculative speeds were not measured on nous in this screening.

A [firsthand Gemma 12B thread](https://www.reddit.com/r/artificial/comments/1twgrd1/ran_gemma_4_12b_on_my_3090_yesterday_and_i_think/)
includes a headless 3080 10 GB report at about 59 tokens/sec with an Unsloth
4-bit quant and 59K context. Other reports in the same discussion differ
substantially. We use it to check plausibility, not substitute for host tests.

The [Ornith/OpenCode community setup](https://github.com/pradcoolz/ornith-local-6gb)
uses explicit reasoning/tool capability metadata, build/plan temperature 0.6
and top-p 0.95. Its 6 GB configuration offloads layers to RAM to support a very
large context. That allocation is not appropriate to copy blindly to our
10 GB GPU: its own measurements show sharply lower speed at high occupancy.
The `community` coding profile tests the metadata and agent sampling changes,
keeping our actual 16K context and 4K output reserve.

[Same-GPU CPU-offload reports](https://www.reddit.com/r/LocalLLaMA/comments/1t4tcmz/smaller_gguf_getting_way_less_tokens_per_second/)
show Qwen 3.6 35B-A3B can be useful with expert weights in system RAM, and
that nominally smaller IQ quants can be slower on CPU than K quants. This is
a credible next quality tier; it was researched, not downloaded or benchmarked
here. A 35B sparse model and a 27B dense model have different offload costs.

## Results and provisional choice

These are screening results, not an established coding leaderboard. Each API
score is five tasks run twice with a 2,048-token output budget. The coding
fixture is two Python functions, checked against 410 edge cases. It does not
establish embedded C proficiency or sustained agent reliability.

| Model / quant | API checks | Median decode tokens/s | Default OpenCode repair |
| --- | ---: | ---: | --- |
| Bonsai 2 27B PQ2_0 | 8/10 | 66 | Pass, 34.1 s |
| Gemma 4 12B Q4_0 | 8/10 | 71 | Pass, 39.4 s |
| Ornith 1.5 9B Q5_K_M | 7/10 | 95 | Pass, 21.8 s |
| Nemotron 9B OpenCode Q6_K | 6/10 | 85 | No edit |
| Qwen 3.5 9B Q5_K_M | 4/10 | 93 | Fail; passed after feedback, 31.0 s total |
| Qwen 3.5 4B Q5_K_M | 1/10 | 141 | Fail |

Reasoning truncation accounts for many failures: 0/2/3/3/6/7 calls respectively
in that table. A fixed-budget failure is operationally relevant but does not
show that a model could never solve the task. Disabling thinking made the API
scores worse for every model. Vendor general-purpose sampling with 4K output
did not consistently improve results: Gemma 3/5, Ornith 2/5, both Qwens 3/5.
Do not rank these single-pass diagnostic runs as statistically significant.

With the community coding profile, Ornith, Nemotron, Bonsai and Gemma all
passed the repair on their first attempt, taking 13.6, 27.0, 31.9 and 59.2
seconds respectively. Nemotron's earlier OpenCode failure is therefore not a
permanent incompatibility. A final isolated-config Ornith rerun also passed
in 19.4 seconds. This combined change does not isolate whether
metadata, sampling or ordinary run variance caused the improvement.

Ornith is the first optional recommendation for bounded coding work: it passed
both coding profiles and is faster than the larger passing candidates here.
Bonsai remains an alternative with a separate backend; Gemma is available for
comparison on the stock backend. Nemotron passed that coding fixture, but failed the later fresh worker tool
check; keep it experimental rather than treating that single pass as readiness.
Qwen 4B is experimental: fastest decoding did not yield the best verified
result. No model is established as a Luna replacement by these tests.

### September 22 follow-up on the R9700

The 32 GB Radeon host can fully offload two larger sparse candidates:
Gemma 4 26B A4B `UD-Q6_K` (23.17 GB) and the officially named
Qwen3-Coder 30B A3B `Q5_K_M` (21.73 GB). The latter is 30.5B total /
3.3B active, not a 32B checkpoint. Both downloads were pinned and
SHA-256 verified. They remain router-only candidates; the managed clients and
Qwen3.8 default were not changed.

The same five-check API screen was rerun with practical model-specific
profiles, so tokens/sec is informative but the scores are not a controlled
weights-only comparison:

| Model / quant | API checks | Median decode tokens/s | OpenCode repair |
| --- | ---: | ---: | --- |
| Qwen3.8 27B Q5_K_M, thinking, 4K output | 8/10 | 60 | Pass, 26.2 s |
| Gemma 4 26B A4B Q6_K, thinking, 4K output | 8/10 | 95 | Pass, 53.7 s |
| Qwen3-Coder 30B A3B Q5_K_M, non-thinking | 6/10 | 134 | Pass, 17.5 s |

Qwen3.8 missed the interval merge twice. Gemma exhausted its 4K reasoning
budget on scheduling twice; a single 8K rerun passed all five checks, with the
scheduling case taking 49.2 seconds. Qwen3-Coder missed both interval merges
and incorrectly treated the one-worker scheduling problem as parallel work.
All three edited the two-function OpenCode fixture successfully and passed all
410 independent checks.

Keep Qwen3.8 as the balanced default. Gemma is the stronger follow-up
candidate when an 8K output budget and longer hard-case latency are acceptable.
Qwen3-Coder is the fastest narrow coding candidate here, but its weaker general
reasoning screen does not justify replacing Qwen3.8.

The managed OpenCode config adds all three downloaded models and explicit
reasoning/tool metadata. After the opt-in review, temperature 0.6, top-p 0.95
and the 4K compaction reserve apply only through the explicit `nous-worker`
launcher; no global model, provider allowlist or build/plan override remains. Thinking stays enabled by the runtime default. Context
remains 16K for stock models and 32K for Bonsai. Workstation tools/builds stay
off nous. Switching models within stock llama.cpp is automatic; switching
between stock and Bonsai still uses `ai-stack` and interrupts active requests.

The five long-retrieval candidates (Bonsai, Qwen 9B/4B, Ornith, Gemma) passed
both cold and cached trials. Cold wall times were 9.33/4.91/2.45/3.21/4.31 s;
cached times were 0.78/0.37/0.37/0.35/0.65 s. Exact retrieval is not proof of
long-context reasoning. Raw responses and generated code remain locally under
`utils/nous/results/`; Git retains the aggregate `summary.json` and artifact
manifest, not the raw transcripts.

### September 25: Qwen3.8 27B GSQ-RCO IQ3_S (superseded)

ISTA-DASLab's `Qwen3.8-27B-GSQ-RCO-IQ3_S-mtp.gguf` (12.12 GB, SHA-256
`58fd8267…c12f` matches the HF etag) was first compared with the incumbent
`UD-Q5_K_M` on the R9700 with identical 64K/f16-KV/MTP3 presets on b11046:

| Check | UD-Q5_K_M | GSQ-RCO IQ3_S |
| --- | ---: | ---: |
| HumanEval+ base / plus (164, medium reasoning) | 162 / 156 | 161 / 155 |
| OMP agentic repair, 600 checks × 3 trials | 3/3 | 3/3 |
| wikitext-2 PPL (100×512) | 6.770 | 6.869 (+1.5%) |
| KLD vs Q5 / same top token | — | 0.055 / 89.1% |
| llama-bench tg128 / pp2048 (t/s) | 27.4 / 1067 | 38.7 / 1137 |
| Served decode with MTP, median t/s | 66.6 | 71.8 |
| VRAM at 64K / 128K / 256K f16 KV (MiB) | 23851 / 28459 / spills | 16848 / 21456 / 30672 |

Task scores tie within noise; the quant is measurably further from the
original than Q5. Tucker chose to promote it, and the serving setup was then
re-tuned from scratch. Bench harness: private llama-server per config, six
short prompts plus eight HumanEval+ prompts at temperature 0.6, aggregate
tokens/s, two or three interleaved repetitions (noise ±2–5%).

| Change | Result | Decision |
| --- | --- | --- |
| llama.cpp master f805c57a2 (int8 coopmat, #27952) vs b11046 | short +5%, code +3%, prefill 935 vs 926 t/s at 26K | Adopt, pinned |
| v0.5.0 HIP (gfx1201) | decode −3–5%, prefill 737 t/s | Reject |
| MTP n-max 4 + p-min 0.4 vs n-max 3 | short 69.7 vs 63.5, code 80.0 vs 71.0 t/s | Adopt; n3/n5/n6 and p-min 0.2–0.5 variants were lower or within noise |
| `RADV_DEBUG=nocompute` | +3% short and code, both reps | Adopt; graphics-queue flag equal, not additive |
| `GGML_VK_FORCE_MMVQ`, `--poll 0` | within noise | Reject |
| q8_0 KV | KLD 0.0047 vs f16, but decode at depth 63–65 vs 70 t/s | f16 at 128K (21.7 GB); q8 only if >128K is needed (256K q8 = 23.9 GB, retrieval correct at 192K) |
| `load-mode none` | same speed; host RSS 12 GB → ~4–7 GB | Adopt |
| prompt cache (`cache-ram`) | after another client's request, resume re-prefilled 2,791 new tokens in 3.7 s; with `cache-ram 0` all 19,963 in 21.4 s | Keep default 8 GiB; `ctx-checkpoints 16` bounds host RAM |
| Power | decode runs at the 300 W cap, ~3.1 GHz; OverDrive disabled (ppfeaturemask bit 0x4000); CPU cores boost to 5.5 GHz | No throughput lever |
| Runtime PM | idle GPU entered BACO and evicted the model to GTT/swap, so the next request was slow | udev rule `power/control=on`; `vm.swappiness 10` |

Quality gate on the shipped binary and preset through the router: HumanEval+
160 / 155 (≥159 / 153 required), OMP agentic 3/3. The 164-problem run took
1,667 s at a median 84.2 t/s, against 2,055 s / 71.8 t/s for the first IQ3_S
preset and 2,152 s / 66.6 t/s for Q5. Q5 stays on disk and in the router
preset for rollback; the b11046 build stays at `/opt/llama.cpp-vulkan`.
Flash-Next GSQ-RCO starts at 66 GB and does not fit this host.

### September 25 (second round): UD-Q4_K_XL + DFlash2 (promoted)

Research round over quants, speculative drafters and engines, on master
f805c57a2 Vulkan with `RADV_DEBUG=nocompute`, same harness, two reps.
KLD against unsloth Q8_0 (wikitext-2, 40×512):

| Target (GB) | KLD / same top | DFlash2 n5 short / code t/s | 86K decode / prefill t/s |
| --- | ---: | ---: | ---: |
| GSQ-RCO IQ3_S (12.1), MTP n4 (old default) | 0.054 / 90.0% | 68.8 / 80.3 (MTP) | 60.0 / 718 |
| GSQ-RCO IQ3_S | — | 73.5 / 92.1 | — |
| UD-IQ4_XS (14.3) | 0.017 / 93.8% | 77.6 / 97.7 | 70.4 / 709 |
| **UD-Q4_K_XL (17.6)** | **0.0058 / 96.7%** | **74.0 / 90.6** | **63.2 / 692** |
| UD-Q5_K_M (19.8) | 0.0035 / 97.2% | — | — |
| Q4_0 (16.1) | — | 60.6 / 78.6 | — |

The drafter is z-lab's DFlash2 Q4_K_M GGUF (1.1 GB; Q8_0 drafter −3%).
`spec-draft-n-max` 5 beat 4 and 6 overall on every target. Lucebox
(`luce_server` HIP, DFlash2 block 16, sampled verify, UD-IQ4_XS) reached
132 t/s on code but only 72 on prose, and fell to 35.6 t/s decode / 420 t/s
prefill at 86K with 2× the re-prefill in the agentic replay; rejected for
OMP's long-context workload.

Quality gate for UD-Q4_K_XL + DFlash2 against the old default, same private
preset: LiveCodeBench 60 (2025+, 30 medium / 30 hard, one sample, 8,192
tokens) 31 vs 28 passed (23 vs 27 truncated), 4,016 vs 5,014 s wall;
HumanEval+ 160 / 155 (old 160 / 155); OMP agentic 3/3; 100K retrieval
correct. 128K f16 KV peaks at 28.2 GB. UD-IQ4_XS is the faster fallback
(3× the KLD). The IQ3_S+MTP and Q5 presets remain for rollback.

### October 1: 128 GB RAM — concurrent agents and the host prompt cache

RAM went from 32 GB to 128 GB (2×64 GB DDR5-5600); VRAM is unchanged, so
the question was whether more than one chat can run at once. Harness:
`conc.py` under `bench.py` (production preset, private server): four agent
sessions of three turns on distinct ~20K-token documents (each turn re-sends
the conversation), then eight HumanEval+ prompts, with C client threads
against `--parallel P`. One repetition per row.

| Server | C | Agents makespan | t/s per stream | Prefilled / cached tokens | Code aggregate t/s |
| --- | ---: | ---: | ---: | ---: | ---: |
| P1, cache-ram 8 GiB (old production) | 1 | 247 s | 71 | 71K / 138K | 91 |
| P1, cache-ram 8 GiB | 4 | 389 s | 69 | 192K / 17K | 91 |
| **P1, cache-ram 32 GiB** | 4 | **254 s** | 71 | 71K / 138K | 92 |
| P2 unified 128K pool, f16 (after a C=2 run on the same documents) | 4 | 252 s | 31 | 53K / 155K | 81 |
| P4 unified 128K pool, f16 | 4 | 221 s | 22 | 70K / 138K | 107 |
| P4 unified, no speculation | 4 | 228 s | 18 | 70K / 138K | 65 |
| P4 unified 256K pool, q8_0 | 4 | 247 s | 19 | 71K / 138K | 102 |
| P2 split 2×128K, q8_0, cache 32 GiB | 4 | 280 s | 31 | 71K / 138K | 85 |
| P2 split 2×128K, q8_0, cache 32 GiB | 1 | 251 s | 64 | 69K / 136K | 91 |
| P4 unified f16, cache 32 GiB | 1 | 248 s | 70 | 71K / 138K | 90 |

- The old 8 GiB prompt cache could not hold four interleaved conversations
  (each ~20K tokens of f16 KV plus 16 recurrent-state checkpoints), so
  interleaved agents re-prefilled 2.7× the tokens and took 57% longer than
  running them back to back. 32 GiB removes the penalty. Production now uses
  `cache-ram = 49152`; at ~8.5 GiB per 100K-token conversation
  ([INFERENCE] from 64 KiB/token f16 KV plus ~145 MiB per checkpoint) it keeps
  about five long or a dozen mid-sized conversations.
- Parallel slots barely raise throughput on this GPU: DFlash speculation
  already fills the batch, so P4 gains 13% agent makespan / 17% code
  aggregate while each stream drops to ~22 t/s. Speculation still pays at P4
  (no-spec code aggregate 65 vs 107 t/s).
- A unified KV pool is not admission control. Four 40K-token sessions in a
  128K pool returned HTTP 500 "Context size has been exceeded." to **every**
  active request (llama.cpp f805c57a2 `server-context.cpp` releases all active
  slots when decode fails at batch size 1). OMP agents routinely exceed 32K,
  so P2/P4 unified is unsafe for them.
- Two guaranteed 128K slots need q8_0 KV (256K total, 29.9 GB VRAM peak): two
  100K-token conversations ran concurrently without error, but single-stream
  decode fell 10% (64 vs 71 t/s) and 86K-depth decode 18% (51.7 vs 63.0 t/s),
  and four clients finished later than one slot (280 vs 254 s).

Decision: keep one slot and enlarge the prompt cache. Concurrent chats queue
for the GPU but no longer pay for re-prefill when they alternate. Revisit
parallel slots only with an admission proxy that bounds summed context, or
with more VRAM.

### October 1–2: models offloaded to system RAM (rejected)

128 GB allows MoE models larger than VRAM, with experts in RAM
(`--fit on --fit-target 1536`, f16 KV 128K, no speculation, same harness).
Pass rule: close to the incumbent's 74 / 91 t/s decode and ~690 t/s prefill,
or a clear quality win.

| Model (GGUF, size) | Decode short / code t/s | Prefill @28K / @73K t/s | 73K-depth decode |
| --- | ---: | ---: | ---: |
| Incumbent Qwen3.8-27B UD-Q4_K_XL + DFlash2 (GPU only) | 74 / 91 | ~690 | 63 |
| Qwen3.8-Flash-Next UD-IQ4_XS (93.7 GB, 125B/6B active) | 21.6 / 21.8 | 226 / 219 | 16 |
| Qwen3-Coder-Next UD-Q4_K_XL (49.6 GB, 80B/3B active) | 42.9 / 43.3 | 434 / 408 | 38 |

Flash-Next tuning did not change the picture: ubatch 4096 doubled prefill
(443 t/s) but lowered decode to 19; 16 or 24 threads, `load-mode none`,
`--lazy-mode off` and `--no-op-offload` were equal or worse. On a
pre-registered 12-problem LiveCodeBench subset (`lcb/subset12.jsonl`: every
fifth medium and hard problem of the 60, same 8,192-token cap) it solved 5
against the incumbent's 6, with no exclusive win and 7 truncations; the
opt-in gate was at least 4 exclusive wins. Both models fail the speed rule,
so RAM-offloaded models are dropped for this host; their GGUFs were deleted
on October 2.

### October 2: host tuning, vision, context and new models

Question: what else raises speed, context, availability or capability on the
existing hardware? Sol (architect) ranked host knobs and researched newer
models; every option ran on the GPU under `llama-yield`, production preset
(UD-Q4_K_XL + DFlash2 n5, 128K f16) unless stated, two interleaved repetitions
per knob. Rule: adopt at a repeatable ≥3% gain, reject a >2% regression.
`edit.py` is a new copy-heavy workload: three full-file rewrites with small
changes (~6.7K output tokens). `vision.py` asks about three synthetic
screenshots (terminal traceback, bar chart, table), alone and after a
~95K–131K-token text prefix.

| Change | Prose / code t/s | Other | Decision |
| --- | ---: | --- | --- |
| Baseline (system Mesa 26.0.8) | 74.6–76.0 / 90.8–92.9 | edits 89 t/s; 73K prefill 717, decode 62–65 | — |
| CPU governor `performance` | 76.2 / 93.2 | +2% | Reject (below 3%, idle power) |
| GPU power profile COMPUTE (5) | 73.8 / 92.4 | — | Reject |
| Server pinned to P-cores 0-15 (quiet host) | 74.6 / 92.6 | — | Reject alone; see contention |
| llama.cpp 5fc4f3c8 (newer master) | 72.2–74.5 / 88.3–91.3 | edits 88 | Reject (−1 to −4%; build deleted) |
| **Mesa 26.2.3 (kisak PPA, private)** | 75.9–77.1 / 94.2–95.0 | 73K prefill **769**, decode **69** | **Adopt** |
| `RADV_DEBUG=nocompute` on 26.2.3 | 77.0 vs 74.1 without | `RADV_QUEUE_DISABLE=compute` equal | Keep |
| **DFlash + `ngram-mod`** (defaults 24/48/64) | 74.8–75.6 / 92.3–94.8 | edits **113–116** (+29%) | **Adopt** |
| **Vision projector** (mmproj F16) | 74.4 / 91.3 | +1.1 GB VRAM; 6/6 images, also after 95K tokens | **Adopt** |
| **160K f16 KV** | 74.2 / 90.5 | peak 30.25 GB; recall correct at 127K tokens (prefill 594, decode 54) | **Adopt** |
| 192K, K f16 / V q8_0 | 77.6 / 92.0 | peak 29.5 GB; recall correct at 156K, decode 49 | Not needed |

Combined production candidate (Mesa 26.2.3, 160K f16, vision, DFlash +
ngram-mod): prose 76.2, code 97.7, edits 124 t/s (+39%); 73K prefill 780 /
decode 69.0, 127K prefill 665 / decode 73.7; vision 6/6 including at 131K
tokens; VRAM idle 31.1, peak 31.4 of 32.6 GB. LiveCodeBench subset12: 6/12,
the same problems as the incumbent. Promoted. Mesa 26.2.3 shows only the
R9700 (as `Vulkan0`) and needs its newer libdrm; it is extracted to
`/opt/mesa-26.2` for llama alone (`utils/nous/mesa/`).

Models (Sol's top downloads), DFlash2 drafter, LCB60 at the 8,192-token cap:

| Model | Prose / code t/s | 73K decode | Edits | VRAM peak | LCB60 | Tokens | vs incumbent |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Incumbent UD-Q4_K_XL | 75.9 / 92.9 | 62–65 | 89 | 28.1 GB | 31 | 303K | — |
| ByteShape Qwen3.8-27B IQ4_XS-3.84bpw (13.1 GB) | 72.5 / 92.2 | 60.9 | 84 | 24.1 GB | 25 | 322K | 3 wins / 9 losses |
| Swift 1.5 Qwen3.8-27B Q4_K_M (17.4 GB fine-tune) | 73.9 / 94.2 | 69.8 | 85 | 28.1 GB | 29 | 321K | 2 wins / 4 losses |

Neither beat the incumbent. Swift's claimed shorter reasoning did not show
here (more tokens, more truncations), and ByteShape's smaller footprint cost
quality. Both GGUFs were deleted. Agention's AP-Q4_K_XL (publisher KLD
0.0083 vs 0.0087, no coding evidence) was not downloaded.

Host CPU contention. Rounds 18–19 lost ~35% decode while other sessions ran
Swift builds (load average ~21). Reproduced with busy loops on all 32 CPUs:
prose 46–55 t/s (−30 to −40%), once 17. `CPUWeight=1000` (47.5–48.3) and
`nice -10` (47.8–48.6) do not help. P-cores still ran at 4.3–4.6 GHz, so it
is not clock or power throttling; the server's threads lose time on shared
cores. Keeping the load off the server's CPUs restores speed: server on
CPUs 8-11 with the load on the other 28, 75.1–75.2 / 91.4–91.8 (−2 to −3%);
on 8-9 only, 71.5–74.1 / 84.4–93.2. Pinning costs nothing on a quiet host
(76.8–76.9 vs 76.7–77.1). sysstat shows sustained load average above 8 on
2 of the last 9 days.
Adopted: `llama.slice` owns CPUs 8-11; `system.slice` and `user.slice` get
0-7,12-31 (`utils/nous/cpu-reserve/`). Other work loses 4 of 32 threads,
including the 5.8 GHz pair.

Availability. A lease whose command was a multi-line `bash -c` broke
`llama-yield --placeholder-state` (systemd property parsing), so the 503
placeholder was down during such leases; fixed and verified (HTTP 503 with
`resume_at` during round 18). Router `--no-models-autoload` was not adopted:
since September 26 production loaded no model other than Qwen, and
`sleep-idle-seconds` already defaults to disabled.

## Established benchmarks for candidate selection

Research checked September 19, 2026. A repeatable harness and independent tests
are stronger evidence than model-card claims, but public tasks can be present
in training data. Leaderboard scores also measure the agent, prompts, retries
and tools; they do not transfer directly to our quantized weights and 16K
OpenCode setup.

| Evaluation | Use for nous | Limitation |
| --- | --- | --- |
| [SWE-bench Multilingual](https://www.swebench.com/multilingual.html) | Primary repository-repair benchmark: 300 curated issues, including 42 C/C++ cases. Start with its C/C++ cases, including MicroPython, jq and fmt. It checks issue fixes and retained functionality. | Public historical issues; no ESP32 peripheral/timing validation. A subset is not the full leaderboard score. |
| [BFCL](https://gorilla.cs.berkeley.edu/leaderboard.html), especially [multi-turn categories](https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html) | Screen repeated tool use, missing information and execution state before considering local agent workers. | Correct tool syntax alone does not establish grounded gameplay decisions. Test our actual chat template and tool parser too. |
| [Aider Polyglot](https://github.com/Aider-AI/polyglot-benchmark) | Cheaper first filter for bounded C++/Python function repairs with executable tests. | Exercises are public and small; OpenCode reruns must be labeled as adapted, not official Aider scores. |
| [SWE-rebench](https://swe-rebench.com/about) | Candidate discovery using fresh issue batches and a standardized agent; reduces dependence on old static scores. | Published context/scaffolding differs from nous. Use date-qualified results, not a universal ranking. |
| [Terminal-Bench](https://www.tbench.ai/run) | Broader build/debug/terminal competence after candidates clear the narrower tests. Current official version is 4.0. | Full 4.0 includes GPU tasks. Do not consume nous's inference GPU with benchmark workloads; choose an explicitly labeled CPU-only subset or older pinned suite. |

LiveCodeBench is useful supplementary algorithm evidence, but repository repair
and tool recovery are closer to this workload than contest problems. I would
not start with HumanEval/MBPP or a single SWE-bench Verified headline as the
admission criterion.

[Harbor](https://docs.harborframework.com/core-concepts/agents/pre-integrated-agents)
is the recommended evaluation runner alongside T3: it already integrates
OpenCode and saves trajectories. Its [OpenCode adapter](https://github.com/harbor-framework/harbor/blob/main/src/harbor/agents/installed/opencode.py)
accepts an `opencode_config` overlay, so the same local provider/model metadata
can be supplied. Pin Harbor, OpenCode, dataset revision and container digests;
do not use the adapter's unpinned latest installation default for comparisons.
The container's ability to reach the Tailscale endpoint must be smoke-tested.
This research did not install or execute Harbor or the established suites.

For hardened grading, use Harbor's [separate verifier](https://docs.harborframework.com/core-concepts/tasks/separate-verifier),
which is opt-in, not the default. Transfer only the proposed patch/artifacts
into a fresh verifier with trusted tests. Validate both the broken base and
the known fix. Keep solution patches, hidden tests and reference answers out
of agent access; restrict network access so an agent cannot retrieve the
upstream answer. Preserve all attempts, timeouts and invalid tool calls.

### Proposed admission pilot

1. Freeze a small stratified set of 12 C/C++ repository issues before looking
   at candidate outputs, spanning at least three repositories. Validate build
   environments and oracle patches first. This is a pilot, not a new leaderboard.
2. Compare Ornith, Bonsai and Nemotron under the same OpenCode version, tool
   access, 16K context, wall/turn budget and feedback policy. Include Luna as
   the reference arm if running the pilot; keep Gemma as the next contender.
3. Run three independent attempts per issue and report first-attempt repair
   success, success after one feedback round, elapsed time to verified repair,
   tool failures, truncation, and regressions. Show uncertainty; do not select
   each model's best run and call it first-attempt success.
4. Follow with held-out project tasks and a separate tool-reliability tranche.
   Evaluate usefulness by verified work saved, including review/correction
   time, rather than decode speed or number of agents launched.

Keep inference requests serialized on nous's single slot, grouped by model to
avoid reload churn. Benchmark containers and builds belong on a workstation
or other suitable runner, not the inference appliance. A queued local worker
can operate alongside a cloud coordinator; a swarm sharing one GPU is not
free parallel capacity.

### Application to s3-amoled (read-only assessment)

The project already has `tests/evaluate.py`: production C functions with
controlled I/O, saved source snapshots, seeds, deadlines, machine-readable
results and stale-source rejection. `tests/eval/check_mutations.py` checks
that known regressions are detected. These provide a better project-specific
oracle than asking another model whether a patch looks correct. Native tests
still do not establish hardware timing or replace the ESP-IDF build gate.
Follow the repo's current build guard and two-job limit when executing them.

Useful held-out repair categories are fragmented SSE/parser handling, queue
and memory bounds, touch/power policy transitions, and grounded action
admission. Recover historical pre-fix snapshots without exposing the fix;
keep tuning tasks separate from the final held-out set. For test-writing
workers, require proposed tests to detect a known defect or mutant while
passing the corrected code. Counting generated tests is not enough.

For Pokémon reasoning, derive offline cases from the existing grounding,
generalized-admission and recovery fixtures: changed observation sequence,
illegal/unready actions, contradictory constraints, unavailable capabilities,
accepted requests without proven effects, resource-limited goals, and resume
after actual state change. Vary option order, wording and map/entity values.
Score against trusted contracts and observed effects, not verbal confidence.
The existing helper tests verify runtime admission logic; they are not already
a benchmark of model decisions. A model-facing replay adapter is still needed.

Recommended initial roles:

- **Bounded patch worker:** one localized issue, explicit files and tests;
  return a patch and evidence for coordinator review.
- **Test author:** propose edge cases/mutants, with independent validation.
- **Experiment analyst:** summarize provided logs with traceable evidence,
  identify failures and propose the next bounded experiment.
- **Offline plan challenger:** propose alternative typed plans against saved
  observations, without executing gameplay or modifying the verifier.

The project's `docs/agent-engine-model-ownership.md` assigns routine decisions
to Jev and harder decomposition to Luna. This research does not change that
contract. Local development workers are distinct from runtime reasoning calls.
Promotion into runtime should first demonstrate grounding, abstention,
constraint retention and independently verified outcomes on held-out cases;
no hardware actions, save mutation or live campaigns were part of this work.
