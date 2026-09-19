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
| Models | `Nemotron-9B-OpenCode.Q6_K`, `Qwen3.5-9B-Q5_K_M` |
| Capacity | 16,384 tokens, one slot per model, one model loaded at a time |

No failed systemd units were reported. SSH directory/key file permissions
were 700/600. GPU temperature was 44 C at the initial inspection.
`decent-angl-doctor --fleet` checks SSH, the active llama/Bonsai service, GPU query, HTTP health
and model inventory without installing anything on nous. It does not run
inference or load models, and is not a correctness/throughput benchmark.

## Existing AI Stack manager

Use `ssh -t nous '~/ai-stack.sh'` for the existing menu, or
`ssh nous '~/ai-stack.sh status'` / `doctor` for inspection. The newer
`/home/tux/ai-stack.sh` (1,363 lines) has service switching, health waits,
model browsing/downloads, benchmarks and diagnostics. The installed bare
`ai-stack` command resolves to an older `/usr/local/sbin/ai-stack` (212 lines).
Do not mistake the older executable for the maintained script.

The manager switches with `systemctl stop/start` and waits for HTTP health.
Its `llama`/`bonsai` commands do not persist a boot selection via
`enable/disable`. Both services were enabled with mutual conflicts. This
is a boot-policy follow-up, not a reason to replace the existing manager.
No boot policy or manager code was changed. A separate typo remains in the
NVIDIA init unit: `After=systemd-modeuls-load.service`. Correcting the unit
requires sudo; the integration session did not have passwordless sudo.

The new fleet probe accepts either active backend and checks the matching
port. Bonsai 2 27B PQ2_0 and its Q8_0 multimodal projector are installed
under `~/repos/Bonsai-demo/models`; together with the two router models,
the manager counts four GGUF files (one is the projector, not a fourth LLM).
Bonsai's service uses port 8081 and a 32K context with KV4. It was inactive
and was not inference-tested. Switching interrupts the other backend.

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

## Recommended coding-agent route

Use T3's OpenCode backend with a separate nous provider over Chat
Completions. [OpenCode documents llama.cpp and custom providers](https://opencode.ai/docs/providers#llamacpp).
OpenCode was not installed on this Mac and its T3 backend was disabled at
inspection; this route is a recommendation, not an end-to-end tested setup.
The documented configuration shape is:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "nous": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Nous",
      "options": {"baseURL": "http://nous:8080/v1"},
      "models": {
        "Nemotron-9B-OpenCode.Q6_K": {
          "name": "Nous Nemotron 9B",
          "limit": {"context": 16384, "output": 4096}
        },
        "Qwen3.5-9B-Q5_K_M": {
          "name": "Nous Qwen 3.5 9B",
          "limit": {"context": 16384, "output": 4096}
        }
      }
    }
  }
}
```

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

Use Nemotron first as an inexpensive experimental planner/coding helper,
with Luna retained for harder reasoning and review until measured results
justify a change. This evaluation made no firmware edits, flashes, live
campaign changes or cloud model calls.
