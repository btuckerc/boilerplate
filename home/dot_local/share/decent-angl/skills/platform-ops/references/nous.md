# Nous inference appliance

`nous` is inference-only. Do not bootstrap chezmoi, shell preferences, Codex,
OMP, or development checkouts on it. Clients and experiment runners stay on
workstations; model requests go to nous over Tailscale.

- SSH: `ssh tux@nous`; MacBook also has a local `ssh nous` alias using its
  existing `~/.ssh/id_rsa`, with agent forwarding disabled. Other clients
  install their own public key; do not copy private keys between machines.
- API: `http://nous:8080/v1`; health: `http://nous:8080/health`.
- Fleet inventory: `~/.config/decent-angl/fleet.json`, role `inference`.
  `decent-angl-doctor --fleet` uses stock SSH commands plus HTTP checks;
  it follows the active llama/Bonsai backend and does not expect the workstation
  doctor or baseline on nous.
- Service: `llama.service`; models: `/srv/models`; service configuration is
  machine-local under `/etc/systemd/system`, not workstation chezmoi state.
- Read-only inspection: `ssh tux@nous 'systemctl status llama.service;
  nvidia-smi; systemctl --failed'`. Logs: `journalctl -u llama.service`.

On 2026-09-19: Ubuntu 26.04.1, i9-13900K, 32 GB RAM, RTX 3080 10 GB;
llama.cpp b11046-60081bb2b. The API binds loopback and Tailscale Serve forwards
8080 within the tailnet. Preserve that exposure boundary.

`Nemotron-9B-OpenCode.Q6_K` and `Qwen3.5-9B-Q5_K_M` are available through
the router. Re-query `/v1/models` for current names. Both were configured for
16,384 context tokens and one slot; the router loads at most one model.
Serialize initial experiments and group by model to avoid repeated swaps.
Do not infer usable context from the model's larger training context.

The host manager is `/home/tux/ai-stack.sh`; `/usr/local/sbin/ai-stack` is a
symlink to it (verified 2026-09-19). Use `ssh nous 'ai-stack status'` or
`doctor`, and `ssh -t nous ai-stack` for its menu. Edit the home script;
do not install a second copy. The old installed script was backed up at
`~/.local/state/ai-stack/backups/ai-stack-installed-20260919` on nous.

An alternative `bonsai.service` serves Bonsai 2 27B at port 8081 when started;
it conflicts with `llama.service`. On inspection it was inactive but both
services were enabled. The manager switches runtime services, not boot enablement. No boot policy
was changed during integration; manual switching should be explicit because
it interrupts inference. Also found
`After=systemd-modeuls-load.service` misspelled in `nvidia-ai-init.service`.
Check these settings again before proposing fixes. Broad sudo requires the user.

Normal switching is passwordless: `ssh nous 'ai-stack llama'` or
`ssh nous 'ai-stack bonsai'`. The root-owned sudoers policy grants tux only
exact systemctl start/stop/restart commands for those two services, plus
stopping both. Source: `utils/nous/90-ai-stack-service-control.sudoers`.
Do not authorize the user-writable manager itself as root. This is an
account-level grant after SSH authentication, not a per-key sudo privilege.

The MacBook T3 Nous instance uses `~/.local/bin/opencode-baseline` (mise-pinned
OpenCode) and managed `~/.config/opencode/opencode.json`. Qwen and Bonsai
passed real file-read tool tests; Bonsai also passed in T3. Nemotron initially failed tool calls, but subsequently passed a two-function
repair with explicit reasoning/tool metadata and build/plan sampling at
temperature 0.6, top-p 0.95. Ornith 1.5 9B is the first optional coding recommendation;
Gemma 4 12B and Qwen 3.5 4B are also installed. All stock models use 16K
context, and Bonsai retains 32K. These are small screening tests, not a
sustained agent benchmark. Selecting a T3 model does not switch
the host service: select the matching backend explicitly before use.

For tested harness compatibility, measured tool calls, and the Pokémon
experiment integration plan, read
`~/src/boilerplate/docs/nous-inference.md`. A responding `/v1/responses`
endpoint alone does not establish Codex tool compatibility.

Expanded results and established-benchmark research:
`~/src/boilerplate/docs/nous-model-evaluation-2026-09-19.md`. DeepSeek V4.1 Flash
is too large for practical local inference on this host. Keep the distinction
between model screening and verified project performance.

Local models are opt-in: the managed OpenCode config does not force a model,
restrict other providers or tune global build/plan agents. `nous-worker`
explicitly launches Ornith/Nemotron/Gemma/Bonsai with per-process settings,
JSON events and resumable session IDs. This works from a T3 terminal-capable
main thread as a subprocess; it is not native Codex `spawn_agent` support.
Read `docs/nous-inference.md` for invocation and tested limits. The `local-workers` skill carries the concise cross-thread recommendation:
use a bounded worker when useful, with Ornith as the launcher default. Do not
change main-thread model defaults merely because local models are available.

Worker readiness check: Ornith, Gemma and Bonsai passed fresh file-read/write
tasks launched from the active T3 main thread; Ornith also passed same-session
follow-up. Nemotron regressed to announcing a read without calling a tool,
so it remains experimental. Prefer the three tested options for bounded
worker tasks; this is operational readiness, not a general coding guarantee.
