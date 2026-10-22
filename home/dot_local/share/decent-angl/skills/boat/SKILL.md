---
name: boat
description: Run tests, builds, benchmarks or evaluation episodes on disposable boat.dev cloud VMs to parallelize beyond nous. Not for coding agents or work needing nous's GPU, USB boards or tailnet.
---

# Boat sandboxes

Boat gives disposable Ubuntu 24.04 VMs (root, Docker, systemd, bwrap,
Clang 18, Python 3.12, no GPU), billed per second. Use it as execution
capacity, not agent capacity: OMP, Luna and Sol stay on nous; Boat runs the
deterministic work (test shards, evaluation episodes, heavy builds, clean-Linux
repros) so a hill climb or sweep can fan out without memory pressure on nous.

Do not run `boat prompt` or other agents in sandboxes: same model quota, none
of our rules or skills. Work needing the GPU, the USB hub boards, the tailnet
or the canonical git remotes stays on nous.

## Account

- Personal account. Trial until the first payment: 2 sandboxes at once, starts
  5/min, 25/h, 75/day, TTL at most 2 h, no `large`/`xlarge`, 25 h compute.
  `boat limits` shows the live numbers; code should read them, not hardcode.
- Each host's CLI is signed in with its own `ci` key (`nous-agents`,
  `mac-agents`; expire 2027-10-22): create, run and delete its own sandboxes
  and snapshots, no billing or key admin. The key file is
  `~/.config/boat/agents.key` (0600). Re-login:
  `boat login --key-stdin < ~/.config/boat/agents.key`.
- The full-access key is `~/hearth/.boat.env` on nous, for key, billing or
  proxy changes only. Never print a key or put one in a sandbox.
- Auto-refill stays off: the balance is the spending ceiling.

## Rules

- Every sandbox: `--no-env`, a `--ttl` of job time plus margin, and
  `--no-snapshots` (a stop then erases it) unless you are building a template.
  Delete in `finally`; after a run `boat list` shows nothing of yours.
- One-off job: `boat run --push DIR --type T --timeout S -- CMD` creates,
  copies the git-tracked files, runs, prints the cost and deletes.
- Fan-out: a versioned named snapshot as template (`NAME-vN`; 10 are free),
  one fresh sandbox per job, starts paced to the per-minute limit. A
  `429 rate_limited` start creates nothing: wait out its window.
- Scripts: output is JSON when piped. `boat exec ID --stream --json --timeout 0
  -- 'cmd'` yields stdout/stderr/exit frames; use `bash -c`, not `bash -lc`.
  `boat scp` results back before deleting.
- No public ports (`boat host`) or tailnet in sandboxes unless asked.
- Private inputs (game ROMs, save files, provider keys) need Tucker's go-ahead
  for that input. Then also `--no-monitoring`, one ROM-bearing sandbox at a time,
  only logs, summaries and hashes come back, never a template containing them.

## Integrations

- s3-amoled host tests:
  `scripts/linux-host-tests.py --boat [--shards N --out DIR] [--suite S]`
  runs on template `pebble-qa-v1` (rebuild: `--boat-provision NAME`).
  `scripts/boat_sandbox.py` there is the reference create/run/fetch/delete
  helper to copy for new consumers.
