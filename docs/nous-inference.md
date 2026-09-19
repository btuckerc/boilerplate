# Nous: inference integration and evaluation

Inspected 2026-09-19 from MacBook. Nous is an inference appliance, excluded
from workstation bootstrap and dotfile deployment. Fleet membership is for
health reporting. Public-key SSH to `tux@nous` was verified with
`BatchMode=yes`; the MacBook's local `ssh nous` alias selects that user and
its existing RSA identity, without forwarding the SSH agent.

## Host and service

| Item | Observed |
| --- | --- |
| OS / CPU | Ubuntu 26.04.1 LTS / i9-13900K |
| RAM / GPU | 32 GB / RTX 3080, 10,240 MiB VRAM |
| Storage | Root 21% used; model partition about 991 GB available |
| Service | llama.cpp b11046-60081bb2b, `llama.service`, enabled and active |
| Network | Loopback server forwarded on port 8080 by Tailscale Serve, tailnet only |
| API | `http://nous:8080/v1` |
| Models | Nemotron 9B, Qwen 3.5 9B/4B, Ornith 1.5 9B, Gemma 4 12B (exact IDs in managed OpenCode config) |
| Capacity | 16,384 tokens, one slot per model, one model loaded at a time |

No failed systemd units were reported. SSH directory/key file permissions
were 700/600. GPU temperature was 44 C at the initial inspection.
`decent-angl-doctor --fleet` checks SSH, the active llama/Bonsai service, GPU query, HTTP health
and model inventory without installing anything on nous. It does not run
inference or load models, and is not a correctness/throughput benchmark.

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

The manager switches with `systemctl stop/start` and waits for HTTP health.
Its `llama`/`bonsai` commands do not persist a boot selection via
`enable/disable`. Both services were enabled with mutual conflicts. This
is a boot-policy follow-up, not a reason to replace the existing manager.
No boot policy or manager code was changed. A separate typo remains in the
NVIDIA init unit: `After=systemd-modeuls-load.service`. Correcting the unit
requires ordinary sudo authentication; it is outside the narrow policy below.

The new fleet probe accepts either active backend and checks the matching
port. Bonsai 2 27B PQ2_0 and its Q8_0 multimodal projector are installed
under `~/repos/Bonsai-demo/models`; the initial manager inventory counted four
GGUF files including a projector. Three additional stock models were installed
during the expanded evaluation; the projector is not a separate LLM.
Bonsai's service uses port 8081 and a 32K context with KV4. It passed OpenCode and T3 tool-round-trip tests below. Switching interrupts
the other backend.

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
`~/.config/opencode/opencode.json`; it registers the two local providers without restricting other providers or
forcing a default model. T3's enabled **Nous**
OpenCode instance uses that wrapper; its config includes Ornith, Gemma 4 12B,
Qwen 3.5 9B/4B, Nemotron and Bonsai. Cloud defaults for
other T3 instances are unchanged; T3 title generation can still use its
configured cloud model.

Select **Nous** in T3's model picker, then the desired model. The backend must
already match: `ssh nous 'ai-stack llama'` serves Ornith/Gemma/Qwen/Nemotron, and
`ssh nous 'ai-stack bonsai'` serves Bonsai. Choosing a model in T3 does not
switch systemd services. Switching interrupts the other backend.

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

## Harness comparison after OMP tool-round-trip testing

For standalone workstation workers, a lean OMP configuration is also viable.
OMP 18.1.5 is already pinned and maintained here and accepts a no-auth local
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
benchmark. No production OMP configuration was changed. The next trial
should use Qwen with bounded read/edit/test tasks before adopting either
model for unattended coding.

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
Broader maintenance still requires ordinary sudo. To revoke the grant, remove
this sudoers file using authenticated sudo; keep that operation outside the
automation allowlist.

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
events/session ID, inspect its edits, and resume the same session:

```sh
nous-worker --model ornith --dir /absolute/task-directory 'Read the task and make the bounded edit.'
nous-worker --model ornith --dir /absolute/task-directory --session SESSION_ID 'Apply this follow-up.'
```

Supported aliases: `ornith`, `nemotron`, `gemma`, `bonsai`. `--read-only`
disables edits. By default the worker can read/search/edit files; shell, web
and further delegation tools are denied. These are OpenCode permissions, not
an OS filesystem sandbox. Use a task checkout/directory and have the parent
run required builds/tests. Project instructions still apply. Prompt text can
come from stdin. The command neither chooses models for other sessions nor
switches inference services; select `ai-stack bonsai` explicitly for Bonsai
and restore `ai-stack llama` for the other three. Serialize inference work.

This is a supervised subprocess worker, not a native Codex collaboration
child or a claimed T3 subagent-tree integration. No global delegation rule
or automatic preference for local models was added. The Nous picker remains
an optional direct OpenCode route; existing T3 threads can retain their model.

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
Ornith, Gemma and Bonsai are usable optional bounded workers; Nemotron remains
experimental despite its earlier repair success. Qwen models remain picker
options but are not promoted into this ready-worker shortlist.

Local raw evidence: `~/.local/state/nous-workers/smoke-20260919-191724/` and
`smoke-20260919-191927/` (inputs, output files, JSON events and session IDs).
Ornith's tested session was `ses_f440a2c81ffeuiK16M0bXuWDon`. Stock llama.cpp
was restored after the Bonsai check.
