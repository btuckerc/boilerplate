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
| RAM / GPU | 32 GB / Radeon AI PRO R9700, 32 GB VRAM |
| Model storage | `/srv/models`; verified artifact identities in `utils/nous/model-artifacts.json` |
| Service | llama.cpp master f805c57a2 Vulkan (pinned at `/opt/llama.cpp-vulkan-f805c57a2`; b11046 kept at `/opt/llama.cpp-vulkan` for rollback), `llama.service`, enabled and active |
| Network | Loopback server forwarded on port 8080 by Tailscale Serve, tailnet only |
| API | `http://nous:8080/v1` |
| Models | Promoted Qwen3.8-27B-GSQ-RCO-IQ3_S-mtp (131,072 context / 8,192 output); the previous UD-Q5_K_M remains selectable; smaller Nemotron, Qwen 3.5 9B/4B, Ornith 1.5 9B and Gemma 4 12B remain selectable in OpenCode; verified Gemma 4 26B A4B Q6_K and Qwen3-Coder 30B A3B Q5_K_M candidates remain router-only |
| Capacity | One serialized model slot; Qwen3.8 uses the 131,072-token preset and other models retain 16,384-token presets |

No failed systemd units were reported. SSH directory/key file permissions
were 700/600. GPU temperature was 44 C at the initial inspection.

The scalable deployment source is `utils/nous/llama.service` plus
`utils/nous/models.ini`. The active host preset is installed at
`/home/tux/.config/llama/models.ini`, with the Qwen artifact under
`/srv/models`; per-model presets keep the 131,072-token Qwen/MTP settings from
leaking into smaller 16K models. Installation of the root-owned unit is a
one-time administrative step; ordinary client catalog edits do not perform
service switching or upgrades.
`decent-angl-doctor --fleet` checks SSH, the active llama service, GPU query, HTTP health
and model inventory without installing anything on nous. It does not run
inference or load models, and is not a correctness/throughput benchmark.

Since 2026-09-25 the promoted worker is ISTA-DASLab's GSQ-RCO IQ3_S quant of
Qwen3.8 27B (12.1 GB, with its MTP head). It uses Vulkan1, f16 KV at 131,072
context (21.7 GB VRAM), `load-mode none` (no 12 GB host mmap of the GGUF),
MTP `spec-draft-n-max 4` / `spec-draft-p-min 0.4`, microbatch 1024, 16 context
checkpoints at minimum spacing 1024, the default 8 GiB prompt cache, and
medium reasoning. It loads on service startup; other models are loaded on
demand, one at a time. The unit sets `RADV_DEBUG=nocompute` (+3% decode).
Host tuning: a udev rule keeps the R9700 out of BACO runtime suspend (which
evicted the idle model from VRAM to system RAM/swap and made the next request
slow), and `vm.swappiness = 10`. Measurements, rejected settings and rollback
are in [the model evaluation](nous-model-evaluation-2026-09-19.md#september-25-qwen38-27b-gsq-rco-iq3_s-promoted).
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
The matching, SHA-256-verified projector is retained at
`/srv/models/Qwen3.8-27B-mmproj-F16.gguf` on Nous (upstream `mmproj-F16.gguf`).
It is **not enabled** in the production preset or OMP catalog. API experiments
with MTP3 passed image-plus-retrieval checks at 119,605 prompt tokens using a
128K/f16 profile and 248,930 tokens using a 262K/q8 profile. The latter took
717 seconds cold and left only 0.42 GiB at peak: not a general-purpose default
or proof of large-image/full-window reliability. The matched follow-up promoted
128K/f16 **text-only**, not the vision profile. See the measured policy for
controls, the apples-to-apples latency comparison, and limitations.

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
| `llama.cpp` | `http://nous:8080/v1` | `~/.omp/agent/models.yml` | Qwen3.8: 131,072; smaller models: 16,384 |

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

## GPU lease

Benchmarks borrow the GPU with `llama-yield` instead of stopping
`llama.service` by hand. While a lease runs, `llama-placeholder` answers every
request on loopback 8080 with HTTP 503, `Retry-After` and a `resume_at`
deadline; `llama-watchdog.timer` restarts production if nothing else does.
Behavior and agent rules: `platform-ops` skill, `references/nous.md`.

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
