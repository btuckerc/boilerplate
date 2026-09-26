# Nous agent host and inference appliance

`nous` is the default host for OMP and Herdr sessions (2026-09-23) and serves
local inference. It is chezmoi machine `nous`, role `agent-host`: an allowlist
applies only `~/.omp/agent`, skills, the mise pin file and hook, Herdr config,
`.gitconfig` and the `omp-*`/`decent-angl-*`/`bw-*`/`opnsense-*` helpers. Its
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
  `~/.local/share/omp-serve-pilot/agent`. Add an OAuth account from the MacBook
  with `ssh -t -L 54545:127.0.0.1:54545 nous omp-broker-login anthropic`
  (Codex callback port 1455).
- `~/.omp/agent/host.yml` (via `PI_CONFIG_FILES`) disables the `computer`
  prelude: nous has no desktop. Mac computer use goes through the `mac` MCP
  server (Peekaboo over SSH, background-only) in `~/.omp/agent/mcp.json`. The
  Mac's forced command must be `env PEEKABOO_DISABLE_TOOLS=browser peekaboo
  mcp --bridge-socket <Peekaboo.app bridge.sock>`: the env var alone falls back
  to an ungranted local host, and the browser tool breaks Bridge startup.
  Peekaboo.app must be running (login item) for screenshots.
- `xdg-desktop-portal{,-gtk}.service` are user-masked (host-local, not
  chezmoi). `libwebkit2gtk-4.1-0` (Tauri builds) pulls them in, but with no
  display the GTK backend exits and the portal times out on every D-Bus
  activation (headless Chrome, Node CLIs). Masked, activation fails immediately.
- Mac shell: `ssh mac` (host-local `~/.ssh/config`, key
  `~/.ssh/id_ed25519_fleet`, authorized on the Mac with `from=` nous's
  tailnet IP). nous has no GitHub credentials; the Mac publishes.

OMP Serve runs from `~/.local/share/omp-serve-pilot/` using the active
`~/.local/share/omp-serve-central/agent` profile. Preserve its cloud roles,
independent auth and sessions. Read `~/src/omp-serve/README.md` and
`docs/omp-workspace-hosting-2026-09-19.md` for deployment details.

- SSH: `ssh tux@nous`; MacBook also has a local `ssh nous` alias using its
  existing `~/.ssh/id_rsa`, with agent forwarding disabled. Other clients
  install their own public key; do not copy private keys between machines.
- API: `http://nous:8080/v1`; health: `http://nous:8080/health`.
- OMP has a native, no-auth OpenAI Chat Completions `llama.cpp` provider in
  the managed shared files `~/.omp/agent/models.yml` and
  `~/.omp/agent/config.yml` (chezmoi sources `private_models.yml` and
  `private_config.yml` under `home/private_dot_omp/private_agent/`). The
  promoted Qwen3.8 profile (`Qwen3.8-27B-UD-Q4_K_XL`, since 2026-09-25)
  is 131,072 context / 8,192 output with medium reasoning; smaller models
  retain 16K presets. The provider is
  `http://nous:8080/v1`; this path does not require OpenCode.

- Service: `llama.service`; source preset/unit:
  `utils/nous/models.ini` and `utils/nous/llama.service`; models:
  `/srv/models`. Service configuration is machine-local under
  `/etc/systemd/system`, not workstation chezmoi state. The unit runs the
  pinned `/opt/llama.cpp-vulkan-f805c57a2` build (b11046 at
  `/opt/llama.cpp-vulkan` is the rollback) with `RADV_DEBUG=nocompute`.
- Exclusive GPU experiments MUST use the root-owned helper (source and install
  steps: `utils/nous/gpu-lease/`, `docs/nous-inference.md` § GPU lease):
  `llama-yield --runtime 3600 -- COMMAND [ARG...]` (from the desired working
  directory). It runs as `tux` in the singleton `llama-yield-gpu.service`,
  refuses concurrent leases or active Bonsai, orders production shutdown
  before the command, and uses systemd `ExecStopPost` to restore production
  after success, failure, caller death or timeout. Default runtime is one hour;
  `--runtime` accepts 1–86400 seconds. `--env NAME=VALUE` passes additional
  environment; HOME/USER/LOGNAME/PATH are preserved/set automatically.
  Never manually stop production for benchmarks or detach GPU work from the
  lease. `~/.local/state/gsq-eval/bench.py` enforces lease-cgroup membership.
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
- Fleet inventory: `~/.config/decent-angl/fleet.json`, role `inference`.
  `decent-angl-doctor --fleet` uses stock SSH commands plus HTTP checks and
  does not expect the workstation doctor or baseline on nous.
- Read-only inspection: `ssh tux@nous 'systemctl status llama.service;
  systemctl --failed'`. Logs: `journalctl -u llama.service`.

Current host hardware is an AMD Radeon R9700; preserve the existing loopback
API and Tailscale Serve exposure boundary.

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

Bonsai is retired from the active catalog and launcher. Historical weights and
evaluation records remain on the host/repository, but ordinary clients must
not start or select `bonsai.service`; the active endpoint is llama.cpp on
8080. Do not authorize new service-switching paths.

The root-owned service-control policy remains historical host state; broad sudo
requires the user. Preserve the existing manager rather than reinstalling it.

The MacBook T3 Nous instance uses `~/.local/bin/opencode-baseline` (mise-pinned
OpenCode) and managed `~/.config/opencode/opencode.json`. Qwen3.8 UD-Q4_K_XL is the
promoted local model (128K context / 8K output / medium reasoning); Ornith,
Nemotron, Gemma and smaller Qwen models remain explicit 16K choices. These are
small screening tests, not a sustained agent benchmark. Selecting a T3 model
does not switch the host service.

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
explicitly launches Qwen3.8/Ornith/Nemotron/Gemma with per-process settings,
JSON events and resumable session IDs. This works from a T3 terminal-capable
main thread as a subprocess; it is not native Codex `spawn_agent` support.
Read `docs/nous-inference.md` for invocation and tested limits. The `local-workers` skill carries the concise cross-thread recommendation:
use a bounded worker when useful, with Qwen3.8 as the launcher default. Do not
change main-thread model defaults merely because local models are available.

Worker readiness check: these results belong to the supervised OpenCode
`nous-worker` harness and must not be conflated with native OMP task children.
The native OMP Ornith child passed a corrective, precise-brief task in 21.6 s,
followed by the parent’s C++ compile/run check. The direct original Ornith
task failed a ceil-div/OR case, and native Gemma failed a `SIZE_MAX` overflow
case. Those older results admitted only mechanical/extraction tasks. The current
Qwen3.8 lane also admits Astra-designed bounded implementation under the
`local-workers` checks-and-one-repair protocol; design and review stay with
Luna/Astra. Bonsai separately passed
native Chat Completions file-read and CSV-write validation with exact ordered
values. Stock llama.cpp was restored after the Bonsai check. These are narrow
behavioral checks, not a final routing policy or general coding guarantee.

Laya has an isolated CPU evaluation environment at
`~/.local/share/nous-triage-eval/` on nous. It is not a service or default
router: both tested checkpoints missed important escalation cases. Keep all
model execution on nous. Results and reproduction material are in
`docs/omp-execution-policy-2026-09-19.md` and `utils/nous/triage-eval/`.