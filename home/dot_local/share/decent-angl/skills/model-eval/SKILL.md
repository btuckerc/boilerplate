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
| Director | `default` | Anthropic | Opus medium |
| Escalation | `plan` → `architect`/`astra` | Codex | Astra medium |
| Escalation, second opinion | `fable` | Anthropic, capped at half | Fable medium |
| Local worker | `task`, `smol`, `tiny`, `commit`, `nous` | nous GPU, no quota | Qwen3.8 27B |
| Cloud worker | `luna` agent, `vision` | Codex | Luna medium |

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
   and confirm the exact `provider`/`model` in the response. For a worker or
   director candidate, also run one real bounded task with an independent check.
6. **Decide.** Write a one-line verdict per lane (adopt / trial / reject) with
   the deciding number. Then adopt through `omp-config`: change the IDs in
   `config.yml` roles/`enabledModels`, and for Anthropic models add a 272K
   `contextWindow` override in `models.yml`. Run `omp-baseline validate`.
   Update (references/benchmarks.md) with the new snapshot and date.

## Nous GPU experiments

Never manually stop `llama.service` for an experiment. On nous, run every
exclusive-GPU benchmark under the root-owned, host-local `llama-yield` helper:

```sh
cd ~/.local/state/gsq-eval
llama-yield --runtime 3600 -- python3 bench.py LABEL [options]
```

The command runs as `tux` in the current directory in the single
`llama-yield-gpu.service` lease. Concurrent leases are refused. systemd stops
production first, kills the entire experiment process group at its deadline,
and restores enabled production even if the caller dies or the command fails.
The default deadline is 3600 seconds; `--runtime` accepts 1–86400 seconds.
Use `--env NAME=VALUE` before `--` for extra environment variables; only
HOME/USER/LOGNAME/PATH are otherwise passed. Do not launch detached GPU work
outside the lease. `bench.py` refuses execution outside a lease cgroup.

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
no longer discriminates (IQ3_S through Q5 all 155–156/164). Quality gate is
LCB60 (`lcb_gen.py MODEL OUT URL` + `lcb_grade.py OUT`, 2025+ medium/hard) run
through `bench.py LABEL --short 0 --run "..."` on :18737, plus
`bench.py --ctx 131072 --long … --replay 8` for depth and cache behavior.

## Rules of thumb

- Medium effort is the default; raise it only on a measured gain. On
  CursorBench, Opus 5.5 high scored +3.5 points for about +33% cost per task.
- Local first: a nous model that passes the worker's contracts costs no
  subscription quota.
- One lane per model family per pool is enough. Do not add a lane that no rule
  routes to.