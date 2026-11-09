# Nous agent host and inference appliance

`nous` is the default host for OMP and Herdr sessions (2026-09-23) and serves
local inference. It is chezmoi machine `nous`, role `agent-host`: an allowlist
applies only `~/.omp/agent`, skills, the mise pin file and hook, Herdr config,
`.gitconfig` and the `omp-*`/`decent-angl-*`/`op-secret`/`opnsense-*` helpers. Its
shell rc files, services and packages stay host-owned. `omp-baseline apply`
installs only the agent toolchain there; the host-local
`~/.config/mise/conf.d/agent-host.toml` disables the workstation tools.

- Home base: `~/hearth` (chezmoi `home/hearth`, agent-host only). Its
  `AGENTS.md` holds only non-inferable instructions (where projects go, the
  inbox, per-project `AGENTS.md` policy); overviews stay here, because context
  files that summarize a repo raise cost without raising success
  (arXiv 2602.11988). `inbox/` holds ideas, `bin/new-project` creates a repo
  plus bare remote, and `src`/`git`/`boilerplate`/`evals`/`models` are
  shortcuts. Interactive shells that start in `~` land there (host-local
  `.bashrc`).
- Repos: `~/src` → `/srv/workspaces/repos`. Active entries are symlinks into
  `mac-20260923/` (the MacBook `~/src` mirror, including uncommitted work);
  09-20 imports stay under `imported-*` and replaced real directories under
  `.pre-mac-20260923/`. Bare repos: `/srv/workspaces/git/<name>.git`
  (`nous` remote, local path on this host). Migration scripts and the resumable
  transfer live in the MacBook's `~/.local/state/nous-migration/`.
  `nous-git-mirror.timer` (chezmoi, enabled once by hand) pushes `--mirror`
  copies of every bare repo to the mini's `/Users/admin/srv/git` nightly at
  04:30; there is no other backup of nous. Machine-local git settings (the gh
  credential helper) live in `~/.gitconfig.local`.
- Auth: the CLI is a broker client via host-local `~/.omp/agent/.env`
  (`OMP_AUTH_BROKER_URL`) and `~/.omp/auth-broker.token`. The broker
  (`omp-auth-broker.service`) stores credentials under
  `~/.local/share/omp-serve-pilot/agent`. OMP cloud inference uses only Codex.
  Add a Codex OAuth account from the MacBook with
  `ssh -t -L 1455:127.0.0.1:1455 nous omp-broker-login openai-codex`.
- `~/.omp/agent/host.yml` (via `PI_CONFIG_FILES`) disables the `computer`
  prelude: nous has no desktop. Mac computer use goes through the `mac` MCP
  server (Peekaboo over SSH, background-only) in `~/.omp/agent/mcp.json`. The
  Mac's forced command must be `env PEEKABOO_DISABLE_TOOLS=browser peekaboo
  mcp --bridge-socket <Peekaboo.app bridge.sock>`: the env var alone falls back
  to an ungranted local host, and the browser tool breaks Bridge startup.
  Peekaboo.app must be running (login item) for screenshots; if the bridge
  reports `bridge.sock` unavailable while the app runs, quit and reopen it.
  Keep the entry's ssh `ConnectTimeout=3`: `omp -p` waits for MCP startup
  before its first request, so a sleeping Mac cost every headless launch the
  full timeout (10 s → 3.4 s to first request with 3). Claude Code registers
  the same server at user scope in host-local `~/.claude.json`
  (`claude mcp add-json -s user mac '{"type":"stdio","command":"ssh","args":[…]}'`
  with the `mcp.json` args); check with `claude mcp get mac`.
- `xdg-desktop-portal{,-gtk}.service` are user-masked (host-local, not
  chezmoi). `libwebkit2gtk-4.1-0` (Tauri builds) pulls them in, but with no
  display the GTK backend exits and the portal times out on every D-Bus
  activation (headless Chrome, Node CLIs). Masked, activation fails immediately.
- Mac shell: `ssh mac` (host-local `~/.ssh/config`, key
  `~/.ssh/id_ed25519_fleet`, authorized on the Mac with `from=` nous's
  tailnet IP). nous publishes boilerplate to GitHub through a repo-scoped
  deploy key (`~/.ssh/boilerplate_deploy`, host alias `github-boilerplate`,
  the push URL of `origin`); `master` refuses force-pushes and deletion.

OMP Serve runs from `~/.local/share/omp-serve-pilot/` using the active
`~/.local/share/omp-serve-central/agent` profile. Preserve its cloud roles,
independent auth and sessions. Read `~/src/omp-serve/README.md` and
`docs/omp-workspace-hosting-2026-09-19.md` for deployment details.

- SSH: `ssh tux@nous`; MacBook also has a local `ssh nous` alias using its
  existing `~/.ssh/id_rsa`, with agent forwarding disabled. Other clients
  install their own public key; do not copy private keys between machines.
- API: `http://nous:8080/v1`; health: `http://nous:8080/health`.
- OMP uses the built-in, no-auth `vllm` provider at
  `http://100.83.125.83:8080/v1`, configured in
  `~/.omp/agent/models.yml` and `~/.omp/agent/config.yml` (chezmoi sources
  `private_models.yml` and `private_config.yml` under
  `home/private_dot_omp/private_agent/`). It serves only
  `Qwen3.8-27B-Swift-Heretic-MXFP4`: 262,144 context / 8,192 output, text and
  image input, medium reasoning. The profile's OpenAI Chat Completions API
  comes from vLLM's OpenAI-compatible endpoint.
- Service: `llama.service`; unit source `utils/nous/llama.service`; serve CLI
  source `utils/nous/serve/`, installed as `/usr/local/bin/nous-serve` and
  configured by `/etc/nous-inference/serve.toml`. It launches the vLLM image
  rootfs `/srv/models/engines/vllm-sly-radiance-1.9.1-rocm10.1`; model weights
  are under `/srv/models/vllm`; compile caches under
  `/srv/workspaces/vllm-cache/home`. Service configuration is machine-local
  under `/etc/systemd/system`, not workstation chezmoi state. No Mesa drop-in
  is used: vLLM runs ROCm/HIP.
- vLLM batches up to 8 sequences with a shared 399,968-token VRAM KV pool;
  there is no host prompt cache. `llama-speedcheck.timer` restarts production
  when ROCm decode is stuck in its slow state (ROCm/ROCm#6347). A stop drains
  in-flight replies for up to 120 s; new requests meanwhile get HTTP 500.
- CPUs 8-11 belong to `llama.slice` (production llama only); `system.slice`
  and `user.slice`, including agents and GPU leases without `--slice`, run on
  0-7,12-31 (`utils/nous/cpu-reserve/`). Do not widen them without measuring decode under load.
- Exclusive GPU experiments MUST use the root-owned helper (source and install
  steps: `utils/nous/gpu-lease/`, `docs/nous-inference.md` § GPU lease):
  `llama-yield --runtime 3600 [--slice llama.slice] -- COMMAND [ARG...]` (from
  the desired working directory). It runs as `tux` in the singleton
  `llama-yield-gpu.service`, refuses concurrent leases or active Bonsai, orders
  production shutdown before the command, and uses systemd `ExecStopPost` to
  restore production after success, failure, caller death or timeout; a
  TERM/INT/HUP to the caller stops the lease under its lock once the start job
  is done, and the caller restores production again after every lease. Default
  runtime is one hour; `--runtime` accepts 1–86400 seconds. `--slice
  llama.slice` puts the lease on production's CPUs 8-11 (benchmarks need it).
  `--env NAME=VALUE` passes additional environment; HOME/USER/LOGNAME/PATH are
  preserved/set automatically. Never manually stop production for benchmarks
  or detach GPU work from the lease.
- Inference candidates (engines, builds, quants, settings) are measured with
  `utils/nous/eval/nous-eval` (`docs/nous-eval.md`), which leases the GPU
  itself and checks production health afterwards.
- During leases, `llama-placeholder.service` owns loopback 8080.
  Every path/method returns HTTP 503 with `Content-Type: application/json`,
  integer `Retry-After` seconds remaining and
  `{"error":{"code":503,"type":"unavailable_error","message":"nous GPU is in use by LABEL; inference resumes when it finishes, by HH:MM UTC at the latest.","resume_at":UNIX_SECONDS}}`.
  The public label defaults to the command basename; `--label LABEL` overrides
  it (1–80 printable characters, no secrets). Deadline/label come from the
  actual lease into root-written `/run/llama-yield/lease.json`. Tailscale Serve
  preserves this response. Benchmarks use separate ports, never 8080.
  The lease's `PropagatesStopTo` stops the placeholder, and cleanup also
  synchronously stops it; llama's `Conflicts`/`After` drop-in orders production
  starts after port release. Reverse `BindsTo`/`PartOf` bindings would pin the
  transient lease name and prevent subsequent leases, so are not used.
  No ordering edge to the lease avoids a cleanup deadlock. The watchdog repairs
  missing placeholders for active leases and
  stops stale ones; HTTP 503 does not count as production being up.
- `llama-watchdog.timer` checks every two minutes; after more than
  five inactive minutes it starts enabled llama only without an active lease
  or active/transitioning Bonsai. Both lease cleanup and watchdog respect
  disabled llama. Intentional long stops MUST use
  `sudo systemctl disable --now llama.service`; resume using
  `sudo systemctl enable --now llama.service`. Inspect
  `journalctl -u llama-watchdog.service -u llama-yield-gpu.service`.
  Policy probes: `llama-yield --watchdog --dry-run --assume-bonsai-active`
  and `llama-yield --watchdog --dry-run --assume-llama-disabled`.
  After a lease, verify `systemctl is-active llama.service` and HTTP 200 from
  `curl -f http://127.0.0.1:8080/v1/models`; restore starts asynchronously.
- GPU power: `/etc/udev/rules.d/80-nous-r9700-runpm.rules` pins
  `power/control=on` for 0000:03:00.0. Without it the R9700 enters BACO
  runtime suspend when idle, which evicts the loaded model to system RAM/swap
  (dmesg "SMU is resumed successfully!"). `vm.swappiness = 10` lives in
  `/etc/sysctl.d/90-nous-inference.conf`. OverDrive/undervolt is unavailable
  (ppfeaturemask bit 0x4000 clear); decode already runs at the 300 W cap.
- NIC: onboard I226-V (`igc`, `eno2`, 0000:09:00.0) can stop receiving with
  carrier and tx up (2026-10-30, 8 h outage; host alive, unreachable). udev
  `81-nous-i226-aspm.rules` disables its PCIe ASPM L1; `nous-nic-watchdog.timer`
  (every minute) bounces `eno2` after 3 min of frozen `rx_packets` plus
  unreachable gateway, rebinds `igc` after 6. Unreachable nous: check sysstat
  `sar -n DEV` and `journalctl -u nous-nic-watchdog` before assuming a hang.
  Sources: `utils/nous/nic-guard/`, `docs/nous-inference.md` § NIC guard.
- Docker is rootless only (user `docker.service`, context `rootless`, data
  `/srv/workspaces/docker`). Rootful docker/containerd are masked and `tux` is
  not in the `docker` group: never unmask them, re-add the group or point
  `data-root` at `/` (small, was 96% full). Containers cannot touch `eno2`,
  host routes or firewall. § Rootless Docker in `docs/nous-inference.md`.
- Memory (128 GB DDR5 since 2026-10-01; was 32 GB). Guard added after the
  2026-09-28 OOM freeze (RAM-backed `/tmp` held ~10 GiB of agent scratch, plus
  11 agent sessions and llama's then 8 GiB host prompt cache):
  `nous-tmp-clean.timer` deletes top-level `/tmp` entries
  owned by tux that have gone unmodified for 12 h (2 h under memory pressure)
  and that no process references. `earlyoom` (`-m 5,3 -s 10,5`) kills single
  processes before the kernel OOM path thrashes the host, preferring
  chrome/pytest/compilers and avoiding vLLM (`vllm`, `VLLM::EngineCor`),
  llama-server, sshd, tailscaled, herdr, omp and claude. llama has `OOMScoreAdjust=-500`; swap is a 32 GiB swapfile at
  `/srv/models/.swap/swapfile` (keep that directory 0755); zswap (lzo, 10%) is
  on via GRUB; `tmp.mount` is masked, so `/tmp` is ext4 on `/`. Never cap the
  whole herdr/agent tree or set llama `MemorySwapMax=0` (rejected:
  performance/capability cost). A long build loop may get its own scope at ~2x
  measured peak `MemoryMax`, no CPU quota (Emerald hill-climb:
  `emerald-hill-dev.scope`, 16G). `omp-chrome-reaper.timer` stops an OMP
  headless Chrome after 30 min of zero tree CPU (`browser.idleCloseSec` closes
  tabs only; OMP relaunches Chrome on next use). Sources and install:
  `utils/nous/memory-guard/`, `docs/nous-inference.md` § Memory guard.
- Fleet inventory: `~/.config/decent-angl/fleet.json`, role `inference`.
  `decent-angl-doctor --fleet` uses stock SSH commands plus HTTP checks and
  does not expect the workstation doctor or baseline on nous.
- Read-only inspection: `ssh tux@nous 'systemctl status llama.service;
  systemctl --failed'`. Logs: `journalctl -u llama.service`.

Current host hardware is an AMD Radeon R9700; preserve the existing loopback
API and Tailscale Serve exposure boundary.


The host manager is `/home/tux/ai-stack.sh`; `/usr/local/sbin/ai-stack` is a
symlink to it (verified 2026-09-19). Use `ssh nous 'ai-stack status'` or
`doctor`, and `ssh -t nous ai-stack` for its menu. Edit the home script;
do not install a second copy. The old installed script was backed up at
`~/.local/state/ai-stack/backups/ai-stack-installed-20260919` on nous.

Bonsai is retired from the active catalog and launcher. Historical weights and
evaluation records remain on the host/repository, but ordinary clients must
not start or select `bonsai.service`; the active endpoint is the single vLLM
model on port 8080. Do not authorize new service-switching paths.

The root-owned service-control policy remains historical host state; broad sudo
requires the user. Preserve the existing manager rather than reinstalling it.

The MacBook T3 Nous instance uses `~/.local/bin/opencode-baseline` (mise-pinned
OpenCode) and managed `~/.config/opencode/opencode.json`. It targets the single
Swift Heretic Qwen3.8 model (256K context / 8K output / medium reasoning), with
text and image input. These are small screening tests, not a sustained agent
benchmark. Selecting a T3 model does not switch the host service.

For tested harness compatibility, measured tool calls, and the Pokémon
experiment integration plan, read
`~/src/boilerplate/docs/nous-inference.md`. A responding `/v1/responses`
endpoint alone does not establish Codex tool compatibility.

Expanded results and established-benchmark research:
`~/src/boilerplate/docs/nous-model-evaluation-2026-09-19.md`. DeepSeek V4.1 Flash
is too large for practical local inference on this host. Keep the distinction
between model screening and verified project performance.

`omp-local` is the fully local OMP lane (profile `local`): every role on the
promoted Swift Heretic Qwen, cloud providers disabled. It shares the built-in
vLLM endpoint.

Local models are opt-in: the managed OpenCode config does not force a model,
restrict other providers or tune global build/plan agents. `nous-worker`
launches the single Qwen3.8 model with per-process settings, JSON events and
resumable session IDs. This works from a T3 terminal-capable main thread as a
subprocess; it is not native Codex `spawn_agent` support. Read
`docs/nous-inference.md` for invocation and tested limits. The `local-workers`
skill carries the concise cross-thread recommendation: use a bounded worker
when useful. Do not change main-thread model defaults merely because local
models are available.

Worker readiness check: these results belong to the supervised OpenCode
`nous-worker` harness and must not be conflated with native OMP task children.
The native OMP Ornith child passed a corrective, precise-brief task in 21.6 s,
followed by the parent’s C++ compile/run check. The direct original Ornith
task failed a ceil-div/OR case, and native Gemma failed a `SIZE_MAX` overflow
case. Those older results admitted only mechanical/extraction tasks. The current
Qwen3.8 lane also admits director- or Sol-designed bounded implementation under the
`local-workers` checks-and-one-repair protocol; design and review stay with
the director/Sol. Bonsai separately passed
native Chat Completions file-read and CSV-write validation with exact ordered
values. Stock llama.cpp was restored after the Bonsai check. These are narrow
behavioral checks, not a final routing policy or general coding guarantee.

Laya has an isolated CPU evaluation environment at
`~/.local/share/nous-triage-eval/` on nous. It is not a service or default
router: both tested checkpoints missed important escalation cases. Keep all
model execution on nous. Results and reproduction material are in
`docs/omp-execution-policy-2026-09-19.md` and `utils/nous/triage-eval/`.