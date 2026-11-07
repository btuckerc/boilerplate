---
name: model-eval
description: Weigh a new or changed model for the agent lanes (Claude Code director, agent-run workers, consults and audits, legacy OMP roles, local) using prices, real token mix, benchmarks, and quota before adopting it.
argument-hint: "[provider/model ...]"
disable-model-invocation: true
---

# Model evaluation

Decide whether a candidate model earns a lane. Adoption follows step 6; this
skill produces the decision and its evidence.

## Lanes

| Lane | Entry point | Pool | Current |
| --- | --- | --- | --- |
| Director | `claude` (settings `model`) | Claude Max | Opus 5.5 high |
| Implementation | `agent-run sol` | Codex | GPT-6.1 Sol high |
| Escalation consult | `agent-run ask --model sol` | Codex | GPT-6.1 Sol xhigh |
| Release audit | `agent-run audit` | Codex | GPT-6.1 Sol xhigh |
| Extraction | `agent-run ask --model luna` | Codex | Luna low |
| Council seats | `agent-run ask --model sol/fable/astra/opus` | per seat | Sol xhigh, Fable high, Astra high, Opus high |
| Local worker | `agent-run local`, `omp-local` | nous GPU, no quota | Qwen3.8 27B |
| Legacy OMP roles | `config.yml` roles | Codex | Sol high default, Luna `task`/`vision` |

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
4. **Quota fit.** Run `agent-quota`. A lane that exhausts its pool before the
   weekly reset loses to a slightly weaker model on a pool with headroom.
5. **Smoke.** Confirm the exact served model first: `codex exec -m CANDIDATE`
   (rollout `turn_context.model`), `claude -p --model CANDIDATE
   --output-format json` (`modelUsage`), or for an OMP role
   `omp -p --mode json --no-session --model CANDIDATE "Reply OK"`. Then test
   the named lane itself at its intended effort: for an `agent-run` lane, a
   scratch copy of `agent-run` with only that model-map entry changed (run it
   with `AGENT_RUN_HOME` set to a scratch directory); for an OMP role, a scratch
   profile. The receipt must show the candidate served with no verification
   issue. For a worker or director candidate, run one real bounded task with
   an independent check. For an escalation or audit candidate, run two
   admission controls through the scratch `agent-run audit`: a realistic
   seeded defect (for example a dropped validation branch in a real diff)
   must come back BLOCK with its file:line, and the same packet without the
   defect must not come back BLOCK.
   For a council seat candidate, give the scratch seat and the incumbent the
   same realistic seeded/clean packet pair with the council's round-1 brief:
   the seeded defect must come back as a blocker or should with its file:line,
   the clean packet must draw no blocker or should, and you verify every
   finding. Compare verified findings, false positives and usage with the
   incumbent. Weigh
   incumbents with `council-yield summary` (from
   `~/.local/state/council/yield.tsv`): a seat with no verified blocker or
   should alone in its last 5 scored runs on its current model is a drop
   candidate; put it to the user with its cost.
6. **Decide.** Write a one-line verdict per lane (adopt / trial / reject) with
   the deciding number. Then adopt: an `agent-run` lane is its model map
   (`CODEX_MODELS` and the Claude ids in `executable_agent-run`) plus the
   lane text in `~/.claude/CLAUDE.md` and the council seat table; confirm with
   one `agent-run ask` whose receipt shows no verification issue. The
   director is `model` and `modelSettings` in the Claude `modify_settings.json`.
   Legacy OMP roles go through `omp-config`: change the IDs in `config.yml`
   roles/`enabledModels` and run `omp-baseline validate`.
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
  task. The director runs Opus high because the Claude pool had headroom.
- Local first: a nous model that passes the worker's contracts costs no
  subscription quota.
- One lane per model family per pool is enough. Do not add a lane that no rule
  routes to.