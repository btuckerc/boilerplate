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

The host manager is `/home/tux/ai-stack.sh`: use `ssh nous '~/ai-stack.sh status'`
or `doctor`, and `ssh -t nous '~/ai-stack.sh'` for its menu. The bare
`ai-stack` command resolves to an older `/usr/local/sbin/ai-stack`; do not
assume they are synchronized. Use the newer script for explicit switches.

An alternative `bonsai.service` serves Bonsai 2 27B at port 8081 when started;
it conflicts with `llama.service`. On inspection it was inactive but both
services were enabled. The manager switches runtime services, not boot enablement. No boot policy
was changed during integration; manual switching should be explicit because
it interrupts inference. Also found
`After=systemd-modeuls-load.service` misspelled in `nvidia-ai-init.service`.
Check these settings again before proposing fixes. Sudo requires the user.

For tested harness compatibility, measured tool calls, and the Pokémon
experiment integration plan, read
`~/src/boilerplate/docs/nous-inference.md`. A responding `/v1/responses`
endpoint alone does not establish Codex tool compatibility.
