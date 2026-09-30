---
name: codex-computer-use
description: macOS only. Operate desktop apps (Safari/Robinhood, Google Calendar, System Settings) through Codex Computer Use with `codex-cu`. Use for any host UI task instead of the eval `computer` prelude.
---

# Codex Computer Use

Run `codex-cu "task"` through bash with `timeout: 600`. It runs Sol high in
`codex exec` with Codex's own Computer Use tools (shell disabled by prompt) and
prints Codex's final message. `--effort low` suits simple reads. Never call
`codex-cu` from inside a job. OMP cannot call the Computer Use service directly:
it accepts only OpenAI-signed senders.

## Writing a job

- One job per call: one read, one order, one calendar change. A Robinhood
  snapshot takes about a minute.
- State exact values, what must not be touched, and the output format.
- Say "open a new tab and close it when done". The user keeps working
  meanwhile; do not ask them to clear the desktop.
- Consequential actions (orders, cancels, deletes, sends) need the user's
  approval first. Put the approved values in the job and require: "submit only
  if the review screen shows exactly these values; otherwise do not submit and
  report what differs". Verify the result with a separate read-only job.

## Exit codes

- `3`: session stopped (Esc, overlay Stop, or state left by an earlier stop).
  If nobody stopped it, run `codex-cu --reset` and retry once.
- `4`: app not approved. The user approves it once in the Codex app. The
  approved list is `ComputerUseAppApprovals.json` in
  `~/Library/Group Containers/2DC432GLL2.com.openai.sky.CUAService/Library/Application Support/Software/`.
- `1`: `codex exec` failed; read the log path it prints.

## Robinhood

- Limit orders take whole shares only. Put liquid-ETF limit buys at the ask so
  they fill.
- To choose which shares are sold for tax purposes: order form, then
  "Sell in", then "Tax lots".
