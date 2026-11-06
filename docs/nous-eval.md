# nous-eval

`utils/nous/eval/nous-eval` measures local inference candidates (llama.cpp
builds, backends and settings, other engines) against production on the
R9700 and says whether a candidate is better, worse or not distinguishable.
It replaced the per-round scripts in `~/.local/state/gsq-eval/`; the older
`utils/nous/{evaluate,coding_eval,grade_code,summarize}.py` stay only because
historical reports cite them.

## Use

```sh
cd ~/src/boilerplate/utils/nous/eval
./nous-eval plan t1 --incumbent -c candidates/vllm-quark-stock.toml # resolve only, no lease/GPU
./nous-eval run t1 --incumbent --design abba # production twice: A/A harness check
./nous-eval run t2 --incumbent -c candidates/llamacpp-rvn-heretic.toml
./nous-eval run t2 --incumbent --set ubatch-size=2048 -c candidates/tip-vulkan.toml
./nous-eval ls; ./nous-eval show RUN; ./nous-eval compare RUN --a incumbent --b llamacpp-rvn-heretic
./nous-eval resume RUN
```

Runs longer than a few minutes go in a user unit so they outlive the shell:

```sh
systemd-run --user --unit nevl-t2 --working-directory=$PWD \
  -E PATH=/home/tux/.local/share/mise/shims:/home/tux/.local/bin:/usr/local/bin:/usr/bin:/bin \
  ./nous-eval run t2 --incumbent -c candidates/tip-vulkan.toml
journalctl --user -u nevl-t2 -o cat -f
```

`--set KEY=VALUE` needs `-c`: each candidate runs both as-is and with the
override, and each variant is compared with the incumbent and its base. On
`llama-router`, the override edits the preset section; on `serve`, it edits
the vLLM args or a known environment key.

`--no-lease --port P` is for CPU smoke runs (`candidates/cpu-selftest.toml`);
the GPU is only ever used under a lease.

## Lease flow

`run` plans the run, checks that every workload's data loads, runs the host
guards, prints how long production will be down at most, then hands itself to
`llama-yield --slice llama.slice` (see
[nous-inference.md § GPU lease](nous-inference.md)). Production stops, the
leased command runs in production's CPU reservation, production restarts. Inside the lease the
lease guards (CPU set, load, free VRAM) run first; before every block free VRAM
is checked again (a container can outlive its stop command), then the block
starts its candidate on port 18737, runs every item, checks that the server
still answers (an engine that crashed mid-block fails the block and names its
log in `logs/<label>.server.log`) and stops it. After the
lease `run` checks production health (`llama.service` active and production's
model answering a one-token chat) and grades. A lease that runs out of time is
followed by another, up to three; `resume` continues by hand.

A run records `inputs.json` (a hash of every workload's items) and each
block's candidate manifest. `resume` refuses items that changed since, and
fails a block whose candidate no longer matches its recorded manifest (rebuilt
engine, retagged image), so one run never mixes two versions of either.

## Tiers

`tiers.toml` defines them; `budget_s` is per block and sizes the lease.

| Tier | Design | Workloads | Use |
|---|---|---|---|
| t1 | ab | speed, longctx 32K, vision, toolcall, lcb 10 | does it boot and work at all |
| t2 | abba | speed ×3, longctx 32K-160K, replay ×3, concurrency, vision, grounding, toolcall | promotion evidence |
| canary | abba | trimmed t2 | weekly origin/master check |
| t3 | ab | lcb 258 medium+hard, 16K cap | coding accuracy, non-inferiority |
| selftest | abba | speed, lcb (short) | harness check on CPU |

ABBA (incumbent, candidate, candidate, incumbent) cancels drift such as
thermals and page cache; the first and last block of the same label also give
an A/A row that shows the noise floor.

## Workloads

| Workload | Measures | Must pass | Reported only |
|---|---|---|---|
| speed | decode t/s and time to first token on prose, code, and copy-heavy edits | decode_tps | ttft_s |
| longctx | needle recall, answered within budget (8192 tokens, 3584 at 160K) and prefill/decode speed at 32K-160K, cold prefill | prefill_tps, decode_tps | |
| replay | session wall time and re-prefilled tokens across 8-turn agent sessions with another client cutting in | | reprefill_tokens (the mechanism; wall time is the outcome) |
| concurrency | makespan of 4 sessions with 1, 2, 4 clients in flight; any failed request fails the item | | |
| vision | synthetic screenshots, charts, tables, rotated text, two-image diff, image at 120K | | |
| grounding | ScreenSpot-v2 click points (100, stratified) | | hit_pixel, hit_norm1000 |
| toolcall | tool-call validity on checkpoints cut from real OMP sessions, with OMP's tool set offered; a checkpoint whose history calls a tool not offered is dropped (ledger M45) | | name_match |
| lcb | LiveCodeBench v5/v6, graded in a bwrap sandbox | pass | |

Every other metric may fail: a significant loss fails the candidate, but its
item set is too small to prove a pass. Every request streams with production
sampling (Qwen3.8 thinking: temp 0.6, top-p 0.95, top-k 20, reasoning medium).
Timings are measured at the client on every engine (first and last streamed
token, `usage` token counts minus cached prompt tokens), so engines are
compared at one boundary; llama.cpp's own timings are kept under
`timings.server` for draft acceptance. Every reply (content, reasoning, tool
calls, finish reason, usage) is kept in `replies.jsonl`, so any score can be
traced back to what the model said.

A candidate is a TOML file in `candidates/`.

- `kind = "serve"`: `spec` names a nous-serve TOML spec. Optional `overrides`
  change vLLM args, spec/image environment variables, `rootfs`, or
  `served_model_name`. The resolved spec is frozen in plan.json. The server
  runs through `/usr/local/bin/nous-serve` on the lease cgroup.
- `kind = "llama-router"` (default): `engine`, `preset`, `section` (default
  `load-on-startup`), optional `[overrides]`, `args`, and explicit `env`.
- `kind = "command"`: a foreground OpenAI-compatible server started by `start`,
  stopped by process-group termination.
- `--incumbent` is derived from the live `llama.service` ExecStart and its
  nous-serve spec, not a checked-in candidate file.

`vllm-quark-stock.toml` compares Quark AWQ weights using the production spec.
`llamacpp-rvn-heretic.toml` is the previous Vulkan model as a comparison and
rollback arm. `--set` edits one candidate's serve args/environment or router
preset values using the same flag semantics.

The vLLM candidate and production run the same exported radiance image through
`nous-serve`; there is no docker candidate wrapper or router sidecar. Specs
mount model directories read-only and all server processes remain inside the
lease cgroup.

ROCm on the R9700 decodes at one of two speeds per process, about 22% apart
([ROCm/ROCm#6347](https://github.com/ROCm/ROCm/issues/6347)): 6 of the first 18
vLLM blocks ran slow, one switched mid-process, at the same clocks, VRAM
placement, CPU placement and draft acceptance. Every ROCm candidate (vLLM and
`build --backend hip*`) sets `GPU_MAX_HW_QUEUES=1`, upstream's mitigation
([lemonade#2609](https://github.com/lemonade-sdk/lemonade/issues/2609)); it
cost nothing here but has not been shown to prevent the slow state, so a
candidate's A/A still decides whether a run counts (§ Statistics, ledger M44).
Vulkan llama.cpp has not shown the split (incumbent A/A 0.99-1.00).

The vLLM argv starts from the fork's quickstart, changed where production's
contract differs: 160K context, images on, prefix caching on. Images on means
no `--skip-mm-profiling` (the quickstart's flag for images off; with images on
it reserves no VRAM for the vision encoder and a 2880x1800 screenshot killed
the engine, so `candidate.py` refuses the pair), and images are capped at
llama.cpp's 4096 tokens so both engines read the same resolution.

`build REF --backend vulkan|hip|hip-wmma [--patch FILE]` builds llama.cpp in a
user unit into `/srv/models/.eval/builds/llama-<sha9>-<backend>` and prints a
candidate TOML.

### Engines considered (2026-11-05)

| Engine | Status on one R9700 (gfx1201) | Decision |
|---|---|---|
| llama.cpp upstream | production (Vulkan); HIP, HIP+rocWMMA and the MMVQ fix ([#29820](https://github.com/ggml-org/llama.cpp/issues/29820)) build at tip | measured arms |
| vLLM radiance fork | RDNA4 kernels, MXFP4 weights (not production's GGUF), DFlash drafter with lossy Cactus acceptance on by default ([1.5.1 notes](https://github.com/SlyBase/vllm-sly-radiance/releases/tag/v1.5.1)), faded out past 4K output tokens since [1.9.0](https://github.com/SlyBase/vllm-sly-radiance/releases/tag/v1.9.0); [1.9.1](https://github.com/SlyBase/vllm-sly-radiance/releases/tag/v1.9.1) fixes a GDN accuracy bug; releases every few days | measured at 1.9.1: 1.7-4× production's speed at t2 ([results](nous-model-evaluation-2026-09-19.md)); `RADIANCE_CACTUS_DELTA=0` is the lossless variant |
| SGLang | no gfx1201 support | cut |
| ExLlamaV3 | kernel tests pass on an R9700 ([#460](https://github.com/turboderp-org/exllamav3/issues/460)); no published 27B serving result | revisit when one appears |
| MLC-LLM | advertises Vulkan/ROCm; no gfx1201 Qwen3.8 result found | not measured |
| Ollama, LM Studio, Lemonade | wrappers around llama.cpp | nothing over upstream |
| llama.cpp r9700 fork ([write-up](https://chrisnovick.com/p/r9700-amd-inference)) | MTP k=3 + RDNA4 kernels; published decode below ours (code 88-98, depth 30K 66-68 t/s) | not measured |

Drafters are a setting, not an engine: production runs DFlash2; llama.cpp also
loads the target's embedded MTP head (`draft-mtp`) and DSpark drafters
(`draft-dspark`, [RadixArk card](https://huggingface.co/Anbeeld/Qwen3.8-27B-DSpark-GGUF)
reports acceptance on NVIDIA/SGLang only), both sweep arms.

## Statistics and verdicts

`compare` pairs items between two labels of one run. Speed-like metrics use
the geometric-mean ratio over items (reps averaged first) with a bootstrap 95%
interval: pass if the lower bound is at least 0.97 (`tolerance` 0.03), fail if
the upper bound is below it. Rates (recall, pass, tool validity) use a per-item
non-inferiority test on the difference: pass if the lower bound is at least
−0.04 (`margin`). The lower bound is never above effect − 3/n (rule of three),
so a few agreeing items cannot certify a 4-point margin; it takes about 75.
The upper bound stays the bootstrap's, so three of seven images lost still fails.
A rate pass is approximate (about 5% rather than 2.5% one-sided error near the
margin at n=258), which is why no promotion needs one.
The verdict fails on any failed must-pass or may-fail metric, any error row or
any reasoning leak (all thinking, no answer) on either side; it passes only when
the run finished with status ok and every must-pass metric passes. A candidate
whose own A/A on a must-pass ratio metric falls outside [1−2·tolerance,
1/(1−2·tolerance)] ran in two states, and their mean measures neither, so it
cannot pass until a stable rerun (ledger M44). Anything else is inconclusive:
run more reps or a bigger tier. Before a t3 decision, measure the incumbent's
own LCB discordance (an A/A on a subset) to size reps.

`./nous-eval canary` checks the latest SlyBase/vllm-sly-radiance GitHub release,
reads the image tag documented in its release notes, exports it with
`/usr/local/bin/nous-serve export`, writes a reusable candidate under
`$NOUS_EVAL_ROOT/canary/candidates/`, and runs the `canary` tier against the
live incumbent. No llama.cpp build is part of the production canary.

Exact flow:

```sh
./nous-eval canary
# Read Candidate spec and run ID from the output.
./nous-eval run t3 --incumbent -c /srv/models/.eval/canary/candidates/radiance-VERSION.toml
./nous-eval promote radiance-VERSION --run CANARY_RUN --run T3_RUN
```

`promote` checks both same-incumbent runs and prints reviewed steps to update
`utils/nous/serve/production.toml` and `/etc/nous-inference/serve.toml`, then
restart `llama.service`; it never applies the change. `rollback` prints steps
to restore the previous exported rootfs from the prior production spec/record
and restart the unit. `G-engine-age` compares production's image ref and
sidecar export time with the latest release.

llama.cpp `build REF --backend vulkan|hip|hip-wmma` remains available to create
comparison candidates; it no longer promotes or tracks production freshness.

## Data layout

Everything lives under `/srv/models/.eval` (`NOUS_EVAL_ROOT` overrides it):

| Path | Holds |
|---|---|
| `data/<workload>/` | fetched datasets (`lcb/questions.jsonl` is what a lease loads; `lcb/tests.jsonl` only grading) |
| `runs/<run_id>/plan.json` | the run's frozen plan: candidates, workloads, blocks, seeds |
| `runs/<run_id>/rows.jsonl`, `graded.jsonl` | one row per (block, candidate, workload, item, rep); later rows replace error rows |
| `runs/<run_id>/manifest.<label>.json` | image/engine identity, model files (hashes), load time and VRAM per block |
| `runs/<run_id>/compare.<a>.<b>.{json,md}` | verdicts |
| `runs/<run_id>/presets/`, `specs/`, `logs/` | derived llama.cpp presets, resolved nous-serve specs, server logs |
| `runs/<run_id>/inputs.json`, `replies.jsonl` | item hashes per workload; every reply |
| `builds/`, `canary/`, `index.sqlite` | builds, canary records, run index |

## Mistakes become guards

`ledger.toml` lists every mistake that cost a run and what now stops it: a
guard in `nevl/guards.py` (run by `preflight`, before a lease, or inside it)
or a regression test. `tests/test_ledger.py` fails if the ledger and the
code disagree in either direction. A fix for a new mistake adds its ledger
entry in the same change.

```sh
python3 -m pytest -q tests
```
