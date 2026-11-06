---
name: model-eval
description: Weigh a new or changed model for the OMP lanes (director, escalation, worker, local) using prices, real token mix, benchmarks, and quota before adopting it.
argument-hint: "[provider/model ...]"
disable-model-invocation: true
---

# Model evaluation

Decide whether a candidate model earns a lane. Adoption itself follows the
`omp-config` upgrade path; this skill produces the decision and its evidence.

## Lanes

| Lane | Role/agent | Pool | Current |
| --- | --- | --- | --- |
| Director | `default` | Anthropic | Opus high |
| Escalation | `plan` → `architect`/`sol` | Codex | GPT-6.1 Sol (`architect` xhigh, `sol` high) |
| Release audit | `plan` → `auditor` | Codex | GPT-6.1 Sol xhigh |
| Sustained frontier | `slow` | Anthropic | Opus high |
| Escalation, second opinion | `fable` | Anthropic, capped at half | Fable medium (after Sol fails) |
| Council seats | `architect`, `fable`, `astra`, `opus` | per seat | Sol xhigh, Fable medium, Astra high, Opus high |
| Local worker | `nous`, `smol`, `tiny`, `commit` | nous GPU, no quota | Qwen3.8 27B |
| Cloud worker | `task`, `vision` | Codex | Luna medium |

A candidate must beat the incumbent for one lane on quality per unit of that
lane's pool. Near-equal quality on a different pool can still win for
escalation, because it spreads load.

## Steps

1. **Discover.** Run `omp models` after `omp-baseline check-upstream`. A model
   absent from discovery needs an OMP pin, auth, or `enabledModels` change first.
2. **Price and shape.** Run
   `python3 ~/.local/share/decent-angl/skills/model-eval/scripts/compare.py CANDIDATE [INCUMBENT]`.
   The script blends catalog prices by the real 14-day OMP token mix.
   That mix is dominated by cache reads, so read price usually drives the
   blend. `x base` compares cost against the director only within the same
   provider pool; Anthropic and Codex allowances are separate.
3. **Benchmarks.** Record at least two sources in
   (references/benchmarks.md): the vendor system card or post, plus one
   independent or cross-vendor table. Prefer agentic coding benchmarks
   (Terminal-Bench, SWE-bench Pro, DeepSWE, FrontierSWE). Note the effort
   level for every number; vendor tables mix efforts.
4. **Quota fit.** Run `omp-quota`. A lane that exhausts its pool before the
   weekly reset loses to a slightly weaker model on a pool with headroom.
5. **Smoke.** Run `omp -p --mode json --no-session --model CANDIDATE --thinking medium "Reply OK"`
   and confirm the exact `provider`/`model` in the response. Then test the
   named lane itself at its intended effort: point a scratch copy of that
   lane's agent definition (or its role in a scratch profile) at the
   candidate, dispatch it with no `effort` override, and confirm from the
   child session that the candidate, not the incumbent, served at that
   effort. For a worker or director candidate, run one real bounded task with
   an independent check. For an escalation or `auditor` candidate, copy
   `~/.omp/agent/agents/auditor.md` with its `model` set to the candidate at
   `:xhigh` and run two admission controls,
   `omp-audit --agent-file COPY --model PROVIDER/MODEL NAME PACKET CANDIDATE`
   (the copy runs as a project agent of that run only; the result says
   `release: false` and fails unless the candidate served): a realistic
   seeded defect (for example a dropped validation branch in a real diff)
   must come back BLOCK with its file:line, and the same packet without the
   defect must not come back BLOCK.
   For a council seat candidate, use that scratch seat agent at the seat's
   effort, not `omp-audit`. Give it and the incumbent seat the same realistic
   seeded/clean packet pair with the council's round-1 brief: the seeded
   defect must come back as a blocker or should with its file:line, the clean
   packet must draw no blocker or should, and you verify every finding. Compare
   verified findings, false positives and usage with the incumbent. Weigh
   incumbents with `~/.local/state/council/yield.tsv`: a seat whose last 5
   scored runs on its current model raised no verified blocker or should
   alone is a drop candidate; put it to the user with its cost.
6. **Decide.** Write a one-line verdict per lane (adopt / trial / reject) with
   the deciding number. Then adopt through `omp-config`: change the IDs in
   `config.yml` roles/`enabledModels`, and for Anthropic models add a 272K
   `contextWindow` override in `models.yml`. Run `omp-baseline validate`.
   Update (references/benchmarks.md) with the new snapshot and date.

## Nous GPU experiments

Never manually stop `llama.service` for an experiment. Local models, quants,
engines and serving settings are measured with `nous-eval`
(`~/src/boilerplate/utils/nous/eval`, docs `docs/nous-eval.md` there), which
takes the GPU through the lease itself:

```sh
cd ~/src/boilerplate/utils/nous/eval
./nous-eval preflight
./nous-eval run t2 --incumbent -c candidates/CANDIDATE.toml   # in a systemd-run --user unit
```

A candidate is a TOML file: the production incumbent is derived from its live
nous-serve spec; serving candidates name a nous-serve spec and optional
overrides; llama.cpp candidates use a preset section. The Quark arm reuses the
production vLLM spec; `llamacpp-rvn-heretic` preserves the previous Vulkan
production model as a comparison/rollback arm. T1 checks it works, T2 (ABBA)
is promotion evidence for speed, depth, cache, concurrency, vision and tool
calls, and T3 is LCB 258 for coding accuracy. A mistake that costs a run gets
an entry in its `ledger.toml` and a guard or regression test.

For radiance release work, `./nous-eval canary` fetches latest release metadata,
derives the documented image tag, exports it, and runs the canary tier. Reuse
the candidate path it prints for `./nous-eval run t3 --incumbent -c PATH`,
then run `./nous-eval promote LABEL --run CANARY_RUN --run T3_RUN`. Promotion
only prints instructions: review and update both the repo and installed
`/etc/nous-inference/serve.toml`, then restart `llama.service`. `rollback`
prints the previous-spec restore/restart steps. The old Vulkan
`llamacpp-rvn-heretic` remains a comparison arm, not production.
Other exclusive-GPU work runs under the root-owned, host-local `llama-yield`
helper:

```sh
llama-yield --runtime 3600 --slice llama.slice -- COMMAND [ARG...]
```

The command runs as `tux` in the current directory in the single
`llama-yield-gpu.service` lease. Concurrent leases are refused. systemd stops
production first, kills the entire experiment process group at its deadline,
and restores enabled production even if the caller dies or the command fails.
The default deadline is 3600 seconds; `--runtime` accepts 1–86400 seconds.
`--slice llama.slice` runs it on production's CPUs; benchmarks need it.
Use `--env NAME=VALUE` before `--` for extra environment variables; only
HOME/USER/LOGNAME/PATH are otherwise passed. Do not launch detached GPU work
outside the lease.

During a lease, `llama-placeholder.service` answers every path and method on
loopback port 8080 (also through Tailscale Serve) with HTTP 503, JSON
`error.type=unavailable_error`, a public command-basename label and UTC deadline,
`error.resume_at` (Unix seconds), and integer `Retry-After` seconds remaining.
The deadline is the runtime hard cap, not an expected completion time; inference
returns when the command finishes, which may be earlier.
Use `--label LABEL` before `--` to override the public label (1–80 printable
characters; do not include secrets). This is intentional unavailability, not
a broken inference endpoint. Benchmarks must use their own ports, never 8080.
The placeholder stops with the lease and releases the port before production
starts; the watchdog repairs it during active leases and stops stale instances.

Afterwards verify `systemctl is-active llama.service` and
`curl -f http://127.0.0.1:8080/v1/models`. Recovery is asynchronous.
Recovery never starts disabled llama or displaces active/transitioning Bonsai.
The enabled `llama-watchdog.timer` checks every two minutes and recovers
enabled llama after over five inactive minutes when neither a lease nor Bonsai
is active. Intentional long stops require
`sudo systemctl disable --now llama.service`; resume with
`sudo systemctl enable --now llama.service`.

Local quant/engine candidates: rank quants by KLD against a Q8_0 reference
(`llama-perplexity --kl-divergence-base`, 40×512 wikitext chunks); HumanEval+
no longer discriminates (IQ3_S through Q5 all 155–156/164). Accuracy, speed,
depth and vision gates are the `nous-eval` tiers above.

## Rules of thumb

- Medium effort is the default for workers; raise it only on a measured gain.
  On CursorBench, Opus 5.5 high scored +3.5 points for about +33% cost per
  task. The director runs Opus high because the Anthropic pool had headroom.
- Local first: a nous model that passes the worker's contracts costs no
  subscription quota.
- One lane per model family per pool is enough. Do not add a lane that no rule
  routes to.