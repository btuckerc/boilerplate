# Nous: inference integration and evaluation

Initial inspection 2026-09-19; active deployment updated 2026-09-21 (MacBook
date). Nous hosts inference and isolated OMP workspaces, but remains excluded
from workstation bootstrap and bulk dotfile deployment. Public-key SSH to `tux@nous` was verified with
`BatchMode=yes`; the MacBook's local `ssh nous` alias selects that user and
its existing RSA identity, without forwarding the SSH agent.

## Host and service

| Item | Observed |
| --- | --- |
| OS / CPU | Ubuntu 26.04.1 LTS / i9-13900K |
| RAM / GPU | 128 GB DDR5-5600 (2×64 GB, since 2026-10-01; was 32 GB) / Radeon AI PRO R9700, 32 GB VRAM |
| Model storage | `/srv/models`; verified artifact identities in `utils/nous/model-artifacts.json` |
| Service | `llama.service` (name kept from llama.cpp): vLLM "radiance" 1.9.1, an RDNA4 fork, run by `nous-serve` from an exported image under bubblewrap (§ Serving: vLLM via nous-serve), since 2026-11-06. llama.cpp f805c57a2 Vulkan stays at `/opt/llama.cpp-vulkan-f805c57a2` for rollback and comparison runs |
| Network | Loopback server forwarded on port 8080 by Tailscale Serve, tailnet only |
| API | `http://nous:8080/v1` |
| Models | One: `Qwen3.8-27B-Swift-Heretic-MXFP4` (Swift-1.5 Qwen3.8 27B heretic abliteration, MXFP4 GPTQ) with the DFlash2 drafter (7 draft tokens), image input (2 per prompt), 163,840 context / 8,192 output. The router's other models are gone with the router |
| Capacity | Up to 8 sequences batched; one 386,677-token KV pool in VRAM holds every running sequence and the prefix cache (no host prompt cache). Four concurrent clients' context-heavy turns (128-token replies) complete 4.5x sooner than on llama.cpp's single slot |

No failed systemd units were reported. SSH directory/key file permissions
were 700/600. GPU temperature was 44 C at the initial inspection.

The deployment source is `utils/nous/serve/` (launcher, production spec,
speed check) plus `utils/nous/llama.service`; installing them is a one-time
administrative step (§ Serving: vLLM via nous-serve). Client catalog edits do
not switch or upgrade the service.
`decent-angl-doctor --fleet` checks SSH, the active llama service, GPU query, HTTP health
and model inventory without installing anything on nous. It does not run
inference or load models, and is not a correctness/throughput benchmark.

Before vLLM (until 2026-11-06) production was llama.cpp. From 2026-09-25 to 2026-10-09 the promoted worker was unsloth's UD-Q4_K_XL quant of Qwen3.8
27B (17.6 GB) with z-lab's DFlash2 Q4_K_M drafter (`spec-draft-n-max 5`).
Since 2026-10-02 it also drafts from n-gram repeats (`spec-type
draft-dflash,ngram-mod`; +30-40% on copy-heavy code rewrites), reads images
(`mmproj` = `/srv/models/Qwen3.8-27B-mmproj-F16.gguf`) and runs on Mesa
26.2.3 (prefill +7%, deep decode +6-11%) with 163,840 f16 KV context. That
setup peaks at 31.4 of 32.6 GB VRAM. Other settings: `load-mode none` (no host
mmap of the GGUF), microbatch 1024, 16 context checkpoints at minimum spacing
1024, a 48 GiB host prompt cache (`cache-ram 49152`, since 2026-10-01) and
medium reasoning. It loads on service startup; other models are loaded on
demand, one at a time. The unit sets `RADV_DEBUG=nocompute` (+3% decode; still
effective on 26.2.3, which prefers the equivalent `RADV_QUEUE_DISABLE=compute`).
Mesa 26.2.3 shows only the R9700, so presets use `Vulkan0` (on system Mesa the
R9700 is `Vulkan1` behind the iGPU).
Host tuning: a udev rule keeps the R9700 out of BACO runtime suspend (which
evicted the idle model from VRAM to system RAM/swap and made the next request
slow), `vm.swappiness = 10`, and CPUs 8-11 reserved for llama (host load on
its CPUs cost 30-40% decode; see § CPU reservation). Measurements, rejected settings and rollback
are in [the model evaluation](nous-model-evaluation-2026-09-19.md#september-25-second-round-ud-q4_k_xl--dflash2-promoted)
and its [October 2 host and model round](nous-model-evaluation-2026-09-19.md#october-2-host-tuning-vision-context-and-new-models).
The September 22 isolated trials found a 24% branched-history latency reduction
from checkpoint spacing, not a cold/append speedup. See
[the measured policy](omp-execution-policy-2026-09-19.md) for the earlier Q5
controls and limitations.
The September 22 Q5 promotion checks passed: native OMP file read/write here and on nous, the
default OpenCode `nous-worker` read, and an OMP Serve conversation. All five
retained smaller models answered API smoke requests. The gateway's Nous and
Mini workers discover Qwen as the recommended local worker with selectable
low/medium/xhigh effort. Existing cloud roles and conversations are unchanged.
Bonsai is disabled and removed from active clients; its weights and historical
results below remain.

The fourth round (Q5) tested vision and larger contexts without replacing the GGUF.
The matching, SHA-256-verified projector is
`/srv/models/Qwen3.8-27B-mmproj-F16.gguf` (upstream `mmproj-F16.gguf`). It has
been **enabled** since 2026-10-02: with DFlash it read a terminal screenshot, a
bar chart and a table correctly, both alone and after 131K tokens of text. The
OMP catalog declares image input; OpenCode declares image attachments.

## Existing AI Stack manager

Use `ssh -t nous ai-stack` for the existing menu, or
`ssh nous 'ai-stack status'` / `doctor` for inspection. The maintained
`/home/tux/ai-stack.sh` has service switching, health waits, model
browsing/downloads, benchmarks and diagnostics. On 2026-09-19 the stale
installed copy was replaced with a symlink:
`/usr/local/sbin/ai-stack -> /home/tux/ai-stack.sh`. Syntax, help, resolved
path, identical contents and live status were verified. Future edits to the
home script immediately reach the command; do not reinstall a separate copy.
The previous executable is backed up on nous at
`~/.local/state/ai-stack/backups/ai-stack-installed-20260919`.

The manager's legacy `llama`/`bonsai` commands use `systemctl stop/start`,
not boot-policy changes. Bonsai and the old NVIDIA initialization unit are
now disabled; do not use the legacy Bonsai switch for ordinary work.

Bonsai weights and its projector remain under `~/repos/Bonsai-demo/models`.
The tests below record historical availability, not a currently supported
client route. The fleet inventory now checks only llama.cpp on port 8080.

`~/ai-stack.sh doctor` ran successfully. In the noninteractive SSH PATH it
reported llmfit, hf, gum, fzf and bat unavailable. The basic service manager
works without them; do not install optional tooling merely for fleet health.

## Codex and T3: verified limitation

[Codex supports custom model providers and local OSS providers](https://learn.chatgpt.com/docs/config-file/config-advanced).
The relevant direct provider would use `http://nous:8080/v1` and
`wire_api = "responses"`; OSS mode specifically selects Ollama or LM Studio.
The present service is llama.cpp, not either of those.

An isolated Codex 0.154.0 smoke test used each model with the Responses
provider, 16K context, read-only sandbox, no retries, and a temporary text
fixture. Both failed before executing the requested file read. Codex
displayed a generic high-demand error, but the server journal identified:

- `unsupported Responses tool type 'namespace' skipped`
- `unsupported Responses tool type 'web_search' skipped`
- HTTP 500 from the model template: `System message must be at the beginning.`

Simple direct Responses requests returned HTTP 200. That is insufficient:
the full Codex message/tool contract currently fails. No cloud Codex defaults
or T3 accounts were changed. Do not present a custom model picker entry as
a working integration. A future fix must test message-role normalization,
namespaced/custom tools, streamed tool results and multi-turn execution, not
just text generation. A compatibility gateway is possible but adds maintained
translation code; avoid making that the first dependency.

The installed T3 bundle has per-instance Codex `homePath`, `launchArgs` and
`customModels`, and understands providers that need no OpenAI login. Its
Codex adapter still launches `codex app-server`, so it inherits the failure.
[T3 provider source](https://github.com/pingdotgg/t3code/blob/main/apps/server/src/provider/Layers/CodexProvider.ts)
is the upstream reference; the installed application was also inspected.

## T3 coding-agent route

For work inside T3, use its OpenCode backend with a separate nous provider over Chat
Completions. [OpenCode documents llama.cpp and custom providers](https://opencode.ai/docs/providers#llamacpp).
OpenCode 1.18.31 is now pinned in mise and launched through
`~/.local/bin/opencode-baseline`. Its managed config is
`~/.config/opencode/opencode.json`; it registers llama.cpp without restricting
other providers or forcing a main-thread model. T3's **Nous** OpenCode instance
uses that wrapper; its catalog includes Qwen3.8, Ornith, Gemma 4 12B,
Qwen 3.5 9B/4B and Nemotron. Other T3 cloud defaults remain unchanged.

Select **Nous** in T3's model picker, then the desired model. All current
choices use llama.cpp on 8080; choosing a model does not switch systemd
services. Router model swaps are serialized.

A temporary fixture test required a real file-read tool and the correct
unseen validation word:

| Model | OpenCode result |
| --- | --- |
| Qwen 3.5 9B | Read tool executed; correct word returned |
| Nemotron 9B | No tool call; announced intent and stopped |
| Nemotron, thinking disabled | Retry still emitted no tool call |
| Bonsai 2 27B | Read tool executed; correct word returned |

Bonsai also passed an actual T3 conversation through the Nous instance:
its activity showed the fixture read and it returned the correct word in
16 seconds. These initial Nemotron failures were superseded by the later community-profile
repair test: it executed edits and passed all fixture checks. These are tool-round-trip checks,
not sustained coding benchmarks. Stock llama.cpp was selected after the expanded evaluation.

Keep repository tools and builds on the workstation. Start with narrow code
edits, test generation and small experimental variants in disposable worktrees;
review and run the existing project checks before promotion. Long prompts,
large tool catalogs and sustained autonomous tasks need separate validation
within 16K. There is no evidence here that either model replaces Luna.

## Measured local tool calls

One bounded Chat Completions call per model requested a typed
`inspect_state(region="LittlerootTown")` function. Both returned the correct
function and valid JSON arguments. No game action or shell tool was executed.

| Model | Wall time | Input/output tokens | Server decode speed |
| --- | ---: | ---: | ---: |
| Nemotron | 1.187 s | 290 / 79 | 84.8 tokens/s |
| Qwen | 2.387 s | 290 / 80 | 92.2 tokens/s |

Qwen's wall time includes switching models. These are single short transport
smokes, not comparative quality benchmarks. Both emitted reasoning before
the function call. A preliminary 32-token text probe exhausted its allowance
on reasoning without a final answer; account for reasoning in output budgets.
The [llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
describes the Chat Completions, Responses and constrained-output interfaces.

## Pokémon experiments in s3-amoled

The host's `scripts/agent-engine-live-compare.py:luna_body` already emits an
ordinary Chat Completions `select_candidate` function request. This is the
smallest experimental seam: a separate local provider can reuse the tool
schema while removing OpenRouter's `provider` routing and cloud-specific
reasoning options, selecting the exact local model, and calling nous.

Keep this a separate experimental arm with `model_owner=local_nemotron` or
`local_qwen`. The current generalized Jev path uses a typed Decisions API;
it is not interchangeable with a text model. The current provider journal
recognizes Jev/Luna and OpenRouter URLs, so endpoint substitution alone
would lose accounting and misstate ownership. Record local request IDs,
model/build, prompt hash, actual token usage, wall time, tool validity,
timeouts and verified effects. Zero API billing does not imply zero hardware
cost; do not invent OpenRouter generation IDs or cloud spend.

First replay frozen observations without execution, using the existing
public-state builder to withhold expected effects. Then compare matched
initial states and tools on the existing retained recovery, independent goal,
compound constraint and interruption/resume cases. Preserve legality,
freshness, bounds, independent receipts and save lineage. Report failed and
inconclusive cases. Serialize requests initially and bound each run; one
GPU slot is not a parallel experiment farm.

Use local models as experimental planners/coding helpers, with Luna retained
for harder reasoning and review until measured results justify a change.
The OMP smoke below favors starting with Qwen; Nemotron needs further
tool-use validation. This evaluation made no firmware edits, flashes or live campaign changes.

## Native OMP providers and bounded task-child results

OMP’s managed native providers use OpenAI Chat Completions directly:

| Provider | Live path | Managed model file | Context |
| --- | --- | --- | ---: |
| `llama.cpp` | `http://nous:8080/v1` | `~/.omp/agent/models.yml` | Qwen3.8: 163,840 (text and image); smaller models: 16,384 |

The chezmoi sources are `home/private_dot_omp/private_agent/private_models.yml`
and `private_config.yml`. These providers require no OpenCode installation;
OpenCode remains a separate, useful Nous path for Codex/T3 integration. The
host also runs isolated OMP workspaces. Bonsai results below are historical.

A native OMP task child using Ornith passed a corrective precise brief in
21.6 seconds; the parent then compiled and ran the C++ fixture successfully.
The direct original Ornith task failed a ceil-div/OR case. A native Gemma task
failed a `SIZE_MAX` overflow case. Therefore native local children are suitable
for bounded mechanical or extraction work; algorithmic reasoning should remain
with Luna/Astra pending broader evidence. Bonsai’s native Chat Completions
path passed file-read and CSV-write checks with exact ordered values. Stock
llama.cpp was restored afterward. These results do not establish a final
planner/router policy. See [the OMP execution report](omp-execution-policy-2026-09-19.md)
for the resulting default policy and subsequent classifier evaluation.

## Promoted Heretic worker and `omp-local` (2026-10-09)

`omp-local` runs OMP under the `local` profile
(`home/private_dot_omp/private_profiles/local/`, applied to
`~/.omp/profiles/local/agent`). Every role (default, task, smol, commit, plan,
slow, vision) is `llama.cpp/Qwen3.8-27B-RVN-Heretic-Q4_K_M`; `anthropic`,
`openai-codex`, `openai` and `openrouter` are disabled and the profile has no
credentials, so nothing in it reaches paid inference. The launcher clears the
default profile's broker and overlay variables when started from inside
another OMP session. Skills, extensions (Herdr state) and themes are symlinks
to the default profile; `RULES.md` is its own. Start it in any Herdr pane.

The model is 0bserverx's `RVN-Q4_K_M-multilingual-mtp.gguf`
(sha256 `8b207715…48f14b95`, 17.0 GB): a Heretic ARA abliteration of
Qwen3.8-27B whose card reports KL ≈ 0.0085 and 0–1/100 harmful-prompt refusals
(stock 3/100). The refusal figures are the card's, not measured here. Its
router preset (`utils/nous/models.ini`) copies the stock worker's settings,
including the stock-trained DFlash drafter and the base vision projector. It
replaced the stock worker on 2026-10-09 for every local role (`nous`, `scout`,
`sonic`, smol/commit/tiny, `nous-worker`); the stock preset is the rollback.

Gate through the production router (`~/.local/state/gsq-eval/gate-rvn.sh`):

| Check | RVN Heretic | Stock UD-Q4_K_XL |
| --- | ---: | ---: |
| HumanEval+ base / plus (164) | 161 / 154 | 160 / 155 |
| OMP agentic repair, 600 checks × 3 | 3/3 | 3/3 |
| LCB12 (pre-registered subset) | 5/12 (6 truncated) | 6/12 (5 truncated) |
| HumanEval+ median decode | 101.5 t/s | 96.7 t/s |

The single LCB12 difference is one hard problem (`abc388_e`). Capability is at
parity within this harness's noise, and DFlash drafting still accepts well.
Because both lanes share one model, `omp-local` and the default profile's
local roles no longer force weight reloads on the one-model router.

## Harness comparison after OMP tool-round-trip testing

For standalone workstation workers, a lean OMP configuration is also viable.
The initial tests used OMP 18.1.5, which accepts a no-auth local
`openai-completions` provider. Keep the 16K context explicit, initially expose
only the tools the task needs, and disable background/title/model-role calls
that could select cloud providers during a local-only evaluation.

A temporary isolated OMP agent directory was tested on 2026-09-19 with only
`read` enabled, no skills/extensions/rules/title generation or saved session.
The model had to read an unseen file and return its validation word:

- Qwen3.5-9B-Q5_K_M: emitted the read call, consumed the actual tool result,
  and returned the correct word. First response took 3.15 seconds including
  model loading; the final response after the tool result took 0.19 seconds.
- Nemotron-9B-OpenCode.Q6_K: emitted no tool call, claimed to have read the
  file, and invented the wrong word. Process exit code was zero; the
  behavioral test failed. The earlier forced-function smoke did not expose
  this distinction. Do not treat transport success as agent success.

This is one sample per model, not a quality ranking or sustained coding
benchmark. No production OMP configuration was changed during that initial test. The
later native-child tests above used the now-pinned OMP 18.2.6 and led to a
narrower mechanical-worker policy.

[OMP model configuration](https://github.com/can1357/oh-my-pi/blob/main/docs/models.md)
provides Chat Completions compatibility flags. The tested temporary provider
used `auth: none`, `contextWindow: 16384`, `maxTokens: 2048`, and compatibility
settings `supportsDeveloperRole: false`, `supportsReasoningEffort: false`,
`supportsStore: false`, `maxTokensField: max_tokens`.

[Pi](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/README.md)
is the alternative for a minimal custom coding/experiment worker: four core
tools, JSON/RPC modes and an embedding SDK. Its current upstream also has
[llama.cpp router support](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/llama-cpp.md).
It was not installed or tested here. A smaller default tool surface is useful
for this 16K deployment, but does not establish better model accuracy.

OpenCode remains the practical choice when T3 integration is the deciding
factor. It now passes the Bonsai end-to-end test above. For Pokémon gameplay decisions,
keep using the existing bounded host experiment runtime and add the local
provider there; a general-purpose coding harness should not replace the
runtime's gameplay admission, effect verification and save handling.

## Restricted passwordless service control

The installed `/etc/sudoers.d/90-ai-stack-service-control` is root-owned,
mode 0440. Its source is `utils/nous/90-ai-stack-service-control.sudoers`.
It permits `tux` to run only `/usr/bin/systemctl` start, stop or restart for
`llama.service` or `bonsai.service`, plus stopping both in that order.
There are no wildcard arguments. `NOSETENV` is set; the user-owned manager
itself is not authorized to run as root. Service units and systemctl remain
root-owned. Unit editing, arbitrary services and root shells are excluded.

This follows the standard [sudoers command allowlist](https://github.com/sudo-project/sudo/blob/main/docs/sudoers.man.in)
approach. SSH authenticates the login with the existing key; sudo grants this
limited permission to the `tux` account, not a particular SSH key. Any process
running as tux can therefore interrupt these inference services. No password
or private key is stored for automation, and agent forwarding is unnecessary.

The user installed the initial policy with ordinary sudo authentication.
Passwordless allowed service control was verified; `/usr/bin/true` and an
unrelated systemctl operation were denied without authentication. Normal
`ai-stack llama` / `ai-stack bonsai` switching can now run noninteractively.
Since 2026-09-25 `utils/nous/91-tux-nopasswd.sudoers` grants tux full
passwordless sudo, which supersedes this allowlist for agents.

## Serving: vLLM via nous-serve

Production is vLLM "radiance", an RDNA4 fork
([SlyBase/vllm-sly-radiance](https://github.com/SlyBase/vllm-sly-radiance)),
chosen over llama.cpp on 2026-11-06 for decode 1.7x, prefill 3.8x and 4.5x
for four clients' context-heavy turns (replies capped at 128 tokens; ledger
M53), with tool calls and images no worse. Accuracy against the llama.cpp arm
is t3's question
([evaluation](nous-model-evaluation-2026-09-19.md#november-56-inference-engine-llamacpp-vs-vllm)).
No container daemon runs it: `nous-serve export IMAGE` unpacks the image once
into `/srv/models/engines/<repo>-<tag>` (with a sidecar holding the image id,
environment and entrypoint), and `nous-serve run SPEC --port N` execs
bubblewrap on that tree: read-only root, the caller mapped to root inside as
under docker, `/dev` and `/sys` from the host, a writable home for compile
caches. The server is then an ordinary process of its unit: it stays in
`llama.slice`, a lease's `systemctl stop` kills it, and `--die-with-parent`
takes it down with the launcher.

The spec (`utils/nous/serve/production.toml`, installed as
`/etc/nous-inference/serve.toml`) names the rootfs, model, mounts, every
`vllm serve` flag and every environment knob, with the reason for each.
`nous-eval` reads it from the unit as its incumbent, and its candidates are the
same spec with overrides, so an evaluation measures what production serves
([docs/nous-eval.md](nous-eval.md)).

| Path | Contents |
| --- | --- |
| `/srv/models/engines/vllm-sly-radiance-1.9.1-rocm10.1` | exported image (6.3 GB) |
| `/srv/models/vllm` | weights, mounted read-only at `/models` |
| `/srv/workspaces/vllm-cache/home` | `/root` inside: `.cache/vllm` (compiled graphs), `.triton`, `.aiter/jit` |

A start with warm caches is ready in about 60 s; a new engine or changed
compile-relevant flag recompiles for about 10 minutes. The unit stays
`activating` until `/health` answers (`ExecStartPost`), and a start not ready
within 30 minutes fails and is retried by `Restart=on-failure`. aiter JIT-builds its ops
into `~/.aiter/jit` and, with a read-only package directory, imports them only
when `AITER_JIT_DIR` points there (nous-serve sets it for every spec).

ROCm on the R9700 decodes at one of two speeds ~22% apart, drawn per process
and occasionally switched mid-process
([ROCm/ROCm#6347](https://github.com/ROCm/ROCm/issues/6347)).
`GPU_MAX_HW_QUEUES=1` is upstream's mitigation and costs nothing. With it, all
6 production vLLM processes sampled on 2026-11-06 drew the same speed (the
speedcheck probe at 142-143 t/s), which suggests but does not prove it prevents
the slow draw. `llama-speedcheck.timer` probes decode every 15 minutes
while production is idle (a probe counts only if production was idle before
and after it and it was the one request finished) and restarts `llama.service`
after two slow probes in a row, or when a ready server fails `/health` four
times over a minute (a stalled event loop recovers; a dead server does not).
The slow threshold is per spec: `sudo -n llama-speedcheck --calibrate`, run on
an idle, settled server after every spec change and restart, takes 6
uncontaminated probes and stores 0.89 × their median with the sha256 of the
spec the running invocation loaded in
`/var/lib/llama-speedcheck/calibration.json`. `nous-serve run --record` writes
those exact bytes to `/run/nous-inference/serve.toml` (llama.service's
`RuntimeDirectory`, removed at every stop), so no clock or ctime is consulted.
With no calibration for that spec, no record, or a `serve.toml` that no longer
matches it (a restart would start another spec), slow-state restarts are off
(logged `uncalibrated`) and only `/health` failures restart;
a calibration across a restart or spec edit is refused. A calibration taken in
the slow state would set the threshold too low, so check the median against
the t2 decode before trusting it. It restarts only under the GPU lease lock,
only the invocation it probed, for a slow state re-checking under the lock that
production is still idle and still runs the calibrated spec, with
llama enabled and no lease or Bonsai, at most twice an hour; an unreadable
`/var/lib/llama-speedcheck/restarts.json` refuses restarts until fixed.
`journalctl -u llama-speedcheck` logs every probe and decision. A restart
drains: llama.service stops with `KillMode=mixed`, `nous-serve` hands the
SIGTERM to vLLM inside the sandbox, and `--shutdown-timeout 120` lets in-flight
replies finish, so a request admitted after the last idle check still completes
(ledger M57). While it drains, for up to 120 s, a new request gets HTTP 500
("cannot schedule new futures after shutdown"), not a refused connection
(drain smoke, 2026-11-06). Review on 2026-12-15: if a month of `journalctl -u
llama-speedcheck` shows no slow probe (`tps=` below the calibrated threshold),
delete the calibration and slow-state path and keep only the `/health` restart.

| Source | Installed |
| --- | --- |
| `utils/nous/serve/nous-serve`, `llama-speedcheck` | `/usr/local/bin/` (0755) |
| `utils/nous/serve/production.toml` | `/etc/nous-inference/serve.toml` (0644) |
| `utils/nous/llama.service`, `utils/nous/serve/llama-speedcheck.{service,timer}` | `/etc/systemd/system/` (0644) |

```sh
ssh nous 'cd ~/src/boilerplate/utils/nous && sudo install -m 0755 serve/nous-serve serve/llama-speedcheck /usr/local/bin/ \
  && sudo install -D -m 0644 serve/production.toml /etc/nous-inference/serve.toml \
  && sudo install -m 0644 llama.service serve/llama-speedcheck.service serve/llama-speedcheck.timer /etc/systemd/system/ \
  && sudo rm -f /etc/systemd/system/llama.service.d/mesa.conf \
  && sudo systemctl daemon-reload && sudo systemctl restart llama && sudo systemctl enable --now llama-speedcheck.timer'
```

Until calibrated the timer only restarts on failed `/health`; once the server
has settled (it refuses earlier), run `sudo -n llama-speedcheck --calibrate`.

A knob change is an edit to the spec, then archive the live spec
(`sudo -n install -D -m 0644 /etc/nous-inference/serve.toml
/etc/nous-inference/history/serve-$(date -u +%Y%m%dT%H%M%SZ).toml`), install,
restart and recalibrate the speedcheck. `nous-eval promote` and `rollback` print
these steps; `rollback` restores the newest archived spec that differs.

Rollback to llama.cpp restores the unit and Mesa drop-in from `c7a0dbb`, the
last llama.cpp commit (both files verified byte-identical to what ran in
production), and uses `~/.config/llama/models.ini` (unmanaged, left in place).
Both files are fetched and checked before either live file is touched:

```sh
ssh nous 'set -eu; cd ~/src/boilerplate; pre=c7a0dbbee72573e93167120f53f556ba4549f789; t=$(mktemp -d)
  git show "$pre:utils/nous/llama.service" >"$t/llama.service"
  git show "$pre:utils/nous/mesa/llama.service.d/mesa.conf" >"$t/mesa.conf"
  grep -q "^ExecStart=/opt/llama.cpp-vulkan-" "$t/llama.service"
  grep -q "^Environment=VK_DRIVER_FILES=" "$t/mesa.conf"
  sudo systemctl disable --now llama-speedcheck.timer
  sudo install -m 0644 "$t/llama.service" /etc/systemd/system/llama.service
  sudo install -m 0644 "$t/mesa.conf" /etc/systemd/system/llama.service.d/mesa.conf
  sudo systemctl daemon-reload; sudo systemctl restart llama
  until curl -sf -o /dev/null localhost:8080/health; do sleep 5; done; curl -s localhost:8080/v1/models'
```

`nous-eval-canary.timer` stays enabled. With llama.cpp in production, the
canary step refuses to run (that failure is ignored), and the watch reports
"production checks skipped" but keeps checking upstream releases.

Then revert the clients (the cutover commit's changes under `home/`,
`utils/scripts` and `utils/omp-context-eval`: `git revert` it, or
`git checkout c7a0dbb -- <paths>`), `chezmoi apply`, `omp-baseline validate`,
and propagate as for any shared-config change.

## GPU lease

Benchmarks borrow the GPU with `llama-yield` instead of stopping
`llama.service` by hand. While a lease runs, `llama-placeholder` answers every
request on loopback 8080 with HTTP 503, `Retry-After` and a `resume_at`
deadline; `llama-watchdog.timer` restarts production if nothing else does.
Behavior and agent rules: `platform-ops` skill, `references/nous.md`.

`--slice llama.slice` runs the lease in production's CPU reservation (CPUs
8-11, § CPU reservation). Benchmarks need it: without it a lease runs in
`system.slice` on the other CPUs and measures a different machine. `nous-eval`
always passes it ([docs/nous-eval.md](nous-eval.md)).

A TERM, INT or HUP to the `llama-yield` client (sudo relays it) stops its
lease, from llama-yield and under its lock, once the lease's start job is done
(stopping it earlier cancels the job and its restore of production), and
llama-yield restores production again itself after every lease. SIGKILL leaves
the lease running until `--runtime` (`systemd-run --wait` leaves the unit
running). `sudo systemctl stop llama-yield-gpu.service` also ends a lease and
restores production; during the start job, only llama-yield's own restore (or
the watchdog, after five minutes) brings production back.

Sources live in `utils/nous/gpu-lease/` and mirror these root-owned paths:

| Source | Installed |
| --- | --- |
| `llama-yield`, `llama-placeholder` | `/usr/local/bin/` (0755) |
| `llama-placeholder.service`, `llama-watchdog.service`, `llama-watchdog.timer` | `/etc/systemd/system/` (0644) |
| `llama.service.d/placeholder.conf`, `llama-yield-gpu.service.d/placeholder.conf` | same subdirectories of `/etc/systemd/system/` (0644) |

Install or update from this checkout, only while no lease is active
(`systemctl is-active llama-yield-gpu.service` prints `inactive`):

```sh
scp -r utils/nous/gpu-lease nous:/tmp/
ssh nous 'cd /tmp/gpu-lease && sudo install -m 0755 llama-yield llama-placeholder /usr/local/bin/ \
  && sudo install -m 0644 *.service *.timer /etc/systemd/system/ \
  && sudo install -D -m 0644 llama.service.d/placeholder.conf /etc/systemd/system/llama.service.d/placeholder.conf \
  && sudo install -D -m 0644 llama-yield-gpu.service.d/placeholder.conf /etc/systemd/system/llama-yield-gpu.service.d/placeholder.conf \
  && sudo systemctl daemon-reload && sudo systemctl enable --now llama-watchdog.timer'
```

Check for drift (no output means the host matches the source):

```sh
cd utils/nous/gpu-lease
for f in llama-yield llama-placeholder; do ssh nous cat /usr/local/bin/$f | diff -q - $f >/dev/null || echo "drift: $f"; done
for f in *.service *.timer *.d/*.conf; do ssh nous cat /etc/systemd/system/$f | diff -q - $f >/dev/null || echo "drift: $f"; done
```

## Private Mesa for llama.cpp

llama.cpp's Vulkan backend ran on Mesa 26.2.3 RADV from the kisak-mesa PPA
(prefill +7%, deep decode +6-11% over Ubuntu's 26.0.8). Production no longer
uses Vulkan; the llama.cpp candidates of `nous-eval` (the rollback arm and tip
builds) set its environment themselves. The `.deb`s are extracted, not
installed, to `/opt/mesa-26.2` (copies kept in `/opt/mesa-26.2/debs`, since the
PPA drops superseded builds); `utils/nous/mesa/install-mesa` recreates it. That
RADV needs its newer libdrm (system libdrm 2.4.131 fails RADV initialization)
and sees only the R9700, as `Vulkan0`:

```
VK_DRIVER_FILES=/opt/mesa-26.2/usr/share/vulkan/icd.d/radeon_icd.json
LD_LIBRARY_PATH=/opt/mesa-26.2/usr/lib/x86_64-linux-gnu
RADV_DEBUG=nocompute
```

## CPU reservation

`llama.service` runs in `llama.slice`, which owns CPUs 8-11 (P-cores 4-5);
`system.slice` and `user.slice` are limited to 0-7,12-31, so agents, builds
and GPU-lease benchmarks never share llama's CPUs. Busy loops on every other
CPU left decode within 2-3%; unreserved it fell 30-40% (`CPUWeight` and
`nice` did not help).

| Source (`utils/nous/cpu-reserve/`) | Installed |
| --- | --- |
| `llama.slice` | `/etc/systemd/system/` (0644) |
| `llama.service.d/cpu.conf` | `/etc/systemd/system/llama.service.d/` (0644) |
| `slice.d/cpu-reserve.conf` | `/etc/systemd/system/system.slice.d/` and `user.slice.d/` (0644) |

```sh
ssh nous 'cd ~/src/boilerplate/utils/nous/cpu-reserve && sudo install -m 0644 llama.slice /etc/systemd/system/ \
  && sudo install -D -m 0644 llama.service.d/cpu.conf /etc/systemd/system/llama.service.d/cpu.conf \
  && for s in system user; do sudo install -D -m 0644 slice.d/cpu-reserve.conf /etc/systemd/system/$s.slice.d/cpu-reserve.conf; done \
  && sudo systemctl daemon-reload && sudo systemctl restart llama'
```

Check: `cat /sys/fs/cgroup/{system,user,llama}.slice/cpuset.cpus.effective`.
Rollback: delete the three drop-ins and `llama.slice`, reload, restart llama.

## Memory guard

On 2026-09-28 nous froze for about 20 minutes (17:52–18:12 UTC). RAM and swap
were full: RAM-backed `/tmp` held ~10 GiB of agent scratch, 11 `omp` sessions
held 8.6 GiB, and `llama-server` held 7.6 GiB of host prompt cache
(`--cache-ram` defaults to 8192 MiB). The kernel OOM killer killed 32
processes, mostly small Chrome processes, until it reached `llama-server`.
These guards prevent a repeat without slowing inference.
A capped `/tmp`, a smaller `cache-ram`, `MemorySwapMax=0` on llama and caps
on the whole herdr/agent tree were rejected. Each of them either limits work or
moves memory pressure onto agents (Astra council review, 2026-09-28). The
2026-09-29 Sol council admitted one narrow exception: a long build loop may run
in its own scope with `MemoryMax` at about 2x its measured peak and no CPU quota
or swap limit, so it swaps before llama is chosen:

- `nous-tmp-clean` (timer, every 15 minutes) removes top-level `/tmp` entries
  owned by tux whose tree has not been modified for 12 h (2 h while
  MemAvailable is below 25%). It keeps anything referenced by a live process
  (cwd, fds, mappings, argv, environ), trees containing sockets, and
  `tmux-`/`ssh-`/`systemd-private-`/dot entries. atime is ignored because
  recursive greps refresh it. `nous-tmp-clean --dry-run` lists what it would remove.
- `earlyoom` sends SIGTERM once available memory is at or below 5% and free
  swap at or below 10% (SIGKILL at 3% / 5%). It prefers chrome, pytest and
  compilers and avoids llama-server, sshd, tailscaled, herdr and omp.
  Thresholds are measured against earlyoom's "user mem" (~120 GiB since the
  2026-10-01 upgrade to 128 GB), so SIGTERM fires near 6 GiB available.
- `llama.service` drop-in `OOMScoreAdjust=-500`, so the kernel kills agents and
  tools before production inference. This changes which process is killed; it
  does not protect llama absolutely.
- The Emerald hill-climb OMP session (pid 8331 and descendants, 7.9 GiB measured
  eval peak) was moved live into transient `emerald-hill-dev.scope`,
  `MemoryMax=16G`, `OOMPolicy=continue`; it ends with the session. Remove the
  cap with `sudo systemctl set-property --runtime emerald-hill-dev.scope MemoryMax=infinity`.
- `omp-chrome-reaper.timer` (chezmoi user timer) stops an OMP headless Chrome
  after 30 minutes of zero CPU in its tree. OMP keeps one per session and
  `browser.idleCloseSec` closes only tabs; OMP relaunches Chrome on next use.
- Swap is a 32 GiB swapfile at `/srv/models/.swap/swapfile` (xfs, fstab
  `nofail`, `x-systemd.requires-mounts-for=/srv/models`); the former 8 GiB
  `/swap.img` on the space-constrained root was removed on 2026-10-01. The
  `.swap` directory must stay world-readable (0755): the llama router walks
  `--models-dir` recursively and refuses to start on an unreadable directory.
  zswap (`lzo`, `max_pool_percent=10`, shrinker on) compresses newly swapped
  pages in RAM first. It is persisted in `/etc/default/grub.d/99-nous-zswap.cfg`.
  Undo it live with `echo N | sudo tee /sys/module/zswap/parameters/enabled`.
- `tmp.mount` is masked. After the next reboot, `/tmp` is ext4 on `/`: scratch
  becomes reclaimable page cache instead of RAM-only shmem. Verify with
  `findmnt -T /tmp`. Disk `/tmp` persists across reboots; the cleaner and
  `tmpfiles` (10 d) age it, so watch free space on `/`.

swappiness stays 10. Since the 128 GB upgrade llama's prompt cache is 48 GiB
(`cache-ram = 49152`, measured in the model evaluation, October 1).

| Source (`utils/nous/memory-guard/`) | Installed |
| --- | --- |
| `nous-tmp-clean` | `/usr/local/sbin/` (0755) |
| `nous-tmp-clean.service`, `nous-tmp-clean.timer` | `/etc/systemd/system/` (0644) |
| `earlyoom` | `/etc/default/earlyoom` (0644; package `earlyoom`) |
| `llama.service.d/oom.conf` | `/etc/systemd/system/llama.service.d/` (0644) |
| `99-nous-zswap.cfg` | `/etc/default/grub.d/` (0644), then `update-grub` |

```sh
scp -r utils/nous/memory-guard nous:/home/tux/memory-guard-stage
ssh nous 'cd ~/memory-guard-stage && sudo install -m 0755 nous-tmp-clean /usr/local/sbin/ \
  && sudo install -m 0644 nous-tmp-clean.service nous-tmp-clean.timer /etc/systemd/system/ \
  && sudo apt-get install -y earlyoom && sudo install -m 0644 earlyoom /etc/default/earlyoom \
  && sudo install -D -m 0644 llama.service.d/oom.conf /etc/systemd/system/llama.service.d/oom.conf \
  && sudo install -m 0644 99-nous-zswap.cfg /etc/default/grub.d/ && sudo update-grub \
  && sudo systemctl daemon-reload && sudo systemctl mask tmp.mount \
  && sudo systemctl enable --now nous-tmp-clean.timer earlyoom \
  && sudo systemctl restart earlyoom && sudo rm -r ~/memory-guard-stage'
```

Inspect: `journalctl -u nous-tmp-clean -u earlyoom`; `grep -E 'Zswap|Swap' /proc/meminfo`.

## NIC guard

On 2026-10-30 nous went unreachable on LAN and tailnet from 05:39 to 14:05 UTC
(power-button shutdown). The host kept running: the onboard Intel I226-V
(`igc`, `eno2`, PCI `0000:09:00.0`, NVM `2017:888d`) stopped receiving while
carrier and transmit stayed up. sysstat showed `eno2` rx at exactly 0 pkt/s
for 8 h after ~10 MB/s of Docker image pulls, with tx ~1.3 pkt/s (ARP for the
gateway), no kernel message and no link flap. Outbound connections failed with
`no route to host`. PCIe ASPM L1 was enabled on that link, a known I225/I226
receive-hang trigger; EEE was already off.

- `81-nous-i226-aspm.rules` sets `link/l1_aspm=0` on `0000:09:00.0`
  (`lspci -vv -s 09:00.0` shows `LnkCtl: ASPM Disabled`).
- `nous-nic-watchdog` (timer, every minute) is silent while the gateway answers
  ping. Otherwise it logs one line per run, and counts a strike only when
  carrier is up and `rx_packets` has not moved since the previous run (any
  received frame, including LAN broadcast, rules out a receive stall). On the
  third consecutive strike it logs counters and bounces `eno2`; on the sixth it
  rebinds `igc` and starts over. It logs `recovered` with the outage length.
  State is in `/run/nous-nic-watchdog/state` (`rx_packets strikes down_since`).

If a stall recurs with ASPM off, the next step is an I226 NVM update via a
board BIOS update.

| Source (`utils/nous/nic-guard/`) | Installed |
| --- | --- |
| `81-nous-i226-aspm.rules` | `/etc/udev/rules.d/` (0644) |
| `nous-nic-watchdog` | `/usr/local/sbin/` (0755) |
| `nous-nic-watchdog.service`, `nous-nic-watchdog.timer` | `/etc/systemd/system/` (0644) |

```sh
scp -r utils/nous/nic-guard nous:/home/tux/nic-guard-stage
ssh nous 'cd ~/nic-guard-stage && sudo install -m 0644 81-nous-i226-aspm.rules /etc/udev/rules.d/ \
  && sudo install -m 0755 nous-nic-watchdog /usr/local/sbin/ \
  && sudo install -m 0644 nous-nic-watchdog.service nous-nic-watchdog.timer /etc/systemd/system/ \
  && sudo udevadm control --reload && sudo udevadm trigger --action=add /sys/bus/pci/devices/0000:09:00.0 \
  && sudo systemctl daemon-reload && sudo systemctl enable --now nous-nic-watchdog.timer \
  && rm -r ~/nic-guard-stage'
```

Inspect: `journalctl -u nous-nic-watchdog`; past traffic per interface:
`sar -n DEV -f /var/log/sysstat/saDD`.

## Rootless Docker

Docker on nous runs rootless for `tux` (user unit `docker.service`, socket
`/run/user/1000/docker.sock`, docker context `rootless` selected in
`~/.docker/config.json`; Harbor and compose use the CLI, so they follow the
context). The rootful `docker.service`, `docker.socket` and `containerd.service`
are masked and `tux` is not in the `docker` group. A rootful socket is root on
the host for any agent that can reach it; under rootless, even
`--privileged --network host` only reaches rootlesskit's namespace (`tap0`
via slirp4netns), never `eno2`, host routes or the host firewall.

An agent installed rootful `docker.io` on 2026-10-30 for a Terminal-Bench run;
its 57 GB store filled `/` to 96%. Rootless data lives on
`/srv/workspaces/docker` (`utils/nous/rootless-docker/daemon.json` →
`~/.config/docker/daemon.json`); `/home` is on the small root filesystem.
Ubuntu's AppArmor userns restriction is satisfied by the packaged
`/etc/apparmor.d/rootlesskit` profile.

```sh
scp utils/nous/rootless-docker/daemon.json nous:.config/docker/daemon.json
ssh nous 'sudo apt-get install -y docker.io docker-compose-v2 docker-buildx rootlesskit uidmap slirp4netns \
  && sudo install -d -o tux -g tux -m 0700 /srv/workspaces/docker \
  && sudo systemctl disable --now docker.service docker.socket containerd.service \
  && sudo systemctl mask docker.service docker.socket containerd.service \
  && sudo gpasswd -d tux docker; \
  PATH=/usr/share/docker.io/contrib:$PATH dockerd-rootless-setuptool.sh install --force; \
  systemctl --user enable --now docker.service \
  && docker context create rootless --docker host=unix:///run/user/1000/docker.sock \
  && docker context use rootless'
```

The setup tool's final `docker version` step fails (it looks for the CLI next to
itself); the unit it writes is fine. Inspect: `docker info` (`name=rootless`
under Security Options), `systemctl --user status docker`,
`journalctl --user -u docker`. Space: `docker system df`; `docker image prune -a`
drops unused task images.

Docker only pulls and unpacks inference images (`nous-serve export`); nothing
runs the GPU in a container. `nous-serve` runs as `tux`, whose `render` group
opens `/dev/kfd` directly, so no device ACL is needed (rootless docker would drop
that group inside a container).

## Expanded model and benchmark evaluation

See [the September 19 report](nous-model-evaluation-2026-09-19.md) for six-model
screening, verified download hashes, community settings, Nemotron recovery,
DeepSeek feasibility, and the proposed Harbor/SWE-bench/BFCL admission pilot.
The small local tests support optional bounded workers, not a
general intelligence ranking or a replacement for Luna.

## Optional workers from a T3 main thread

The current Codex main thread's native `spawn_agent` tool exposes cloud model
IDs only. It cannot directly select a nous model. A main thread with terminal
access can explicitly launch a separate OpenCode worker, collect its JSON
summary/session ID, inspect its edits, and resume the same session:

```sh
nous-worker --dir /absolute/task-directory 'Read the task and make the bounded edit.'
nous-worker --dir /absolute/task-directory --session SESSION_ID 'Apply this follow-up.'
```

Supported aliases: `qwen` (default), `ornith`, `nemotron`, `gemma`. `--read-only`
disables edits. By default the worker can read/search/edit files; shell, web
and further delegation tools are denied. These are OpenCode permissions, not
an OS filesystem sandbox. Use a task checkout/directory and have the parent
run required builds/tests. Project instructions still apply. Prompt text can
come from stdin. The command neither chooses models for other sessions nor
switches inference services. All supported choices use llama.cpp; serialize inference work.

The default output is a compact JSON summary with `verified: false` and an
evidence path under `~/.local/state/nous-workers/`. Full events and stderr stay
there; `--format json` returns the original events when explicitly needed.
`--timeout 180` and `--steps 12` bound the default run. Deadline or caller
cancellation stops the worker process group. A workstation lock returns exit
75 if another launcher owns the slot, and backend health failure returns 69;
the launcher never silently falls back to a paid model. This lock coordinates
only this workstation, not other machines or direct OpenCode clients.
Its per-process provider allowlist and main/title/compaction model selections
keep auxiliary inference local too. These settings affect only this worker.

This is a supervised subprocess worker, not a native Codex collaboration
child or a claimed T3 subagent-tree integration. No global delegation quota
is imposed. The small `local-workers` skill makes the recommendation
discoverable across threads and permits useful bounded delegation without
a quota. Qwen3.8 is the launcher default, not the main-thread default. The Nous picker remains
an optional direct OpenCode route; existing T3 threads can retain their model.
The skill also prefers a fresh-brief Luna subagent for larger/tool-rich tasks
or a local failure, with integration and verification kept in the parent.
See [the usage audit](codex-usage-audit-2026-09-19.md) for this routing policy.

Verified from the active T3 main thread on 2026-09-19 using `nous-worker`:

| Model | Fresh file-tool task | Wall time | Follow-up |
| --- | --- | ---: | --- |
| Ornith 1.5 9B | Pass: read input, correct grounded choice, wrote result | 8.26 s | Same session, changed input, correct revised result in 6.93 s |
| Gemma 4 12B | Pass: read input and wrote correct result | 34.43 s | Not tested |
| Bonsai 2 27B | Pass: read input and wrote correct result | 16.68 s | Not tested |
| Nemotron 9B | Failed: announced read but called no tools | 54.58 s | Not tested |

Each input contained a fresh nonce, stale and illegal candidates, and a cost
tie. The parent independently checked the output file against the expected
nonce and selected ID. This verifies real delegation/file tools, not broad
coding quality. Earlier two-function coding tests complement these checks.
These September 19 results informed the original smaller-model shortlist.
The current promotion supersedes that recommendation with Qwen3.8; they
remain historical evidence, not a claim that Bonsai is still available.

Local raw evidence: `~/.local/state/nous-workers/smoke-20260919-191724/` and
`smoke-20260919-191927/` (inputs, output files, JSON events and session IDs).
Ornith's tested session was `ses_f440a2c81ffeuiK16M0bXuWDon`. Stock llama.cpp
was restored after the Bonsai check.
