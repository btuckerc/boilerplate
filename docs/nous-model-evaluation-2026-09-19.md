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
