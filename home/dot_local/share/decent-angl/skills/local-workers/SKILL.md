---
name: local-workers
description: Route independently checkable work to nous or Luna during multi-step coding, test drafting, research synthesis, or log analysis. Prefer local workers for bounded file tasks and Luna for broader tool work; keep demanding decisions with the main model. Not needed for trivial edits.
---

# Local workers

Choose routing without asking the user to pick a model. Astra is the OMP
director. Prefer local-first for independently checkable bounded implementation
with clear scope, contract and runnable acceptance; settle risky design decisions
without pre-solving routine implementation details. Do not
send a task to Luna merely because its output is code. Suitable examples are a
small API/caller migration, explicit configuration precedence, and a small
state machine with director-specified transitions. Mechanical edits, extraction
and supplied-log summaries remain local candidates.
Use Luna medium for unresolved design, novel algorithms, uncertain debugging,
broad/tool-rich changes, large context, or a failed focused local repair.
Normal checkpoint and user-directed steering remains available.
Consult `architect` only for an unresolved ambiguity. In Codex, keep those
decisions with the parent or an explicitly selected frontier worker. Trivial
work stays in the parent when delegation would cost more; there is no
classifier, swarm or planner tax.

For native Codex Luna workers, use a fresh brief (`fork_turns="none"`,
`model="gpt-5.6-luna"`) rather than copying the parent thread. Medium suits
ordinary implementation and tests; preserve explicit user model/effort choices.
Full-history forks inherit the parent model, so they are not the cheap-worker
path. OMP callers use their supported equivalent. For a native OMP `nous`
child, leave the task-item `tools` field unset unless the names are functions
explicitly declared with OMP's `@tool` evaluation mechanism; those names are
not a sandbox for built-in file tools, and
OMP may add `hub` to a non-read-only child. Give exact input/output paths and
ask for the result via `write`/`yield`; the parent runs checks because the
worker may not have the required verification command or tool.

`nous-worker` defaults to the promoted **Qwen3.8-27B-UD-Q5_K_M** on the
serial nous llama.cpp service (65,536 context / 8,192 output, medium
reasoning). **Ornith**, **Nemotron** and **Gemma** remain explicit smaller or
experimental choices at their 16K profiles. Bonsai is retired from the active
launcher and catalog; historical evaluation records and host weights are
unchanged. They are supervised workers, not replacements for Astra's design and
acceptance decisions or a blanket substitute for Luna. A local pass is evidence
for the checked contract only; the parent reviews the artifact as well as checks.

## Bounded local-first protocol

Before delegation, establish a runnable acceptance check and a compact brief:
owned files, exact contract, risky invariants, acceptance command, non-goals and
artifact handoff. Reuse supplied requirements; add only missing design decisions.
There is no minimum word count. Prefer roughly 100–150 words when sufficient,
not a full solution or transcript. Make observable edge cases explicit: for
example, whether expired entries consume cache capacity. Reuse repository
patterns. If resolving uncertainty costs more than doing the small task, stay direct.
Use the existing Astra director; do not launch an extra Astra planner/supervisor
per slice. Group compatible edits under one ownership boundary rather than
delegating individual lines. While the worker runs, do useful independent
parent work when available; avoid repeated status/reasoning turns. Dispatch
and verification also consume cloud context, so local output alone is not
proof of net subscription savings.

In OMP, avoid paid wait-only turns when blocked solely on one bounded local job.
Use native eval `agent(brief, {agent: "nous"})`, await the handle with an explicit
timeout, then run the pre-agreed parent acceptance through `tool.bash` in that
same cell and display both results. For a small slice, JavaScript
`await h.wait({timeout: 180})` bounds the wait; retain `h`, and on timeout use
`await h.cancel()` before escalation. Inspect `await h.status()` when needed.
A numeric JavaScript argument silently fails to set this timeout in OMP 18.2.6.
Eval's cell timeout pauses during agent waits and is not a worker deadline.
This remains a native OMP child, not a shell-launched nested harness. Keep `blocking: false`:
when independent parent work or active steering is useful, use background
task/hub normally. Do not globally serialize workers or weaken artifact review.

Run one local attempt, then run the targeted check in the parent. On failure,
send one focused correction (normally <=150 words) with the actual counterexample,
expected versus observed behavior, and violated invariant. Re-run the full
targeted check after the repair. A remaining failure, scope expansion, context
limit, or stalled worker goes to Astra/Luna; no model-shopping or repair loop.
Use a roughly 150-second attempt target / 180-second supervised deadline for
small slices; a larger budget needs a concrete task-specific reason.

OMP exposes per-task `effort` without adding a classifier call. Omit it to keep
the configured medium default. Prefer `lo` when routine cloud work is selected;
retain medium for uncertain debugging, unresolved design and failed local repairs.
In a six-attempt-per-arm screen, low and medium both passed; low used 43% fewer
output tokens. This is worker-only evidence, not a subscription-savings claim.
`lo` maps to low on the current Astra/Luna catalog; `med` maps to high there,
not medium. Keep local implementation at medium:
the low-effort summarizer trial passed but took substantially longer. Do not
use local `hi` as a repair strategy; prior xhigh output hit its token cap.
Recheck native model discovery before assuming these mappings after an upgrade.

The gated Qwen3.8 pilot matched Luna on eight attempts across four small synthetic
task families with frozen Astra briefs, not repository-scale autonomous work.
It justifies this bounded lane, not a general parity or subscription-savings
claim. Keep foreground work direct when local queuing/latency costs more than
the cloud usage it can avoid. Do not route vision work to the text-only local
deployment. Do not enable an automatic cloud fallback.

Native local children remain background-capable so the director can inspect
compact `hub` status at natural checkpoints, send corrections as evidence and
requirements warrant, and cancel/escalate a blocker or budget overrun. Allow
at most one failed-check repair; normal clarification and requirement steering
is not capped. Steering is delivered at model/tool boundaries;
do not poll full transcripts or add a watchdog loop.

```sh
nous-worker --dir /absolute/task-directory 'Task, allowed files, constraints, expected output and acceptance checks.'
nous-worker --dir /absolute/task-directory --session SESSION_ID 'Bounded follow-up.'
```

Use `--model ornith`, `--model nemotron`, or `--model gemma` explicitly,
including when resuming those sessions. `--read-only` supports analysis. Prompts may come from stdin.
Workers receive the task and directory context, not the parent conversation.
Supply the relevant paths, observed input/schema, acceptance criteria and
expected return format; do not copy the whole thread. Include only the project
rules needed for that task, and keep the parent responsible for validation.

The launcher returns a compact summary, session ID and evidence directory;
full events stay on disk (`--format json` opts into raw events). Read only the
needed evidence. Keep briefs scoped to the files and facts the worker needs.
Provide ordinary text/code files, not long JSON strings that file tools may
truncate. The default deadline is 180 seconds and step budget 12; increase
these explicitly only for a justified bounded task. A busy/unreachable host
returns promptly so the parent can use Luna or continue itself. The launcher's
per-process provider/model pins keep auxiliary inference local. Inspect actual
file changes and run the relevant checks in the parent. A claimed result or
successful process exit is not verification. Give at most one focused repair
after a failed check, then finish in the parent or choose a stronger model;
ordinary steering remains available and there are no model-shopping loops.

Run one nous request at a time: the GPU has one inference slot. The launcher
locks concurrent workers on this workstation; other clients still need coordination. File tools
run on the workstation; shell/web/further delegation are disabled. OpenCode
permissions are not an OS sandbox, so use a scoped task directory or approved
checkout and respect one-writer ownership. The parent handles builds.

This is an OpenCode subprocess, not a native Codex `spawn_agent` child. Keep
this OpenCode nous-worker path for Codex/T3 use, with fresh briefs, scoped
directories, no shell/web/delegation, parent-side verification, and no paid
fallback. Native OMP task children are a separate bounded lane.
It works from terminal-capable T3/Codex/OMP threads without changing their
main model. If the command or host is unavailable, continue the main task;
do not bootstrap a machine or interrupt another inference job just to delegate.
The launcher does not switch services. For intentional backend switching or
host maintenance, use platform-ops; ordinary workers need no host setup. Any
Jev OMP triage is optional decision support only when the user explicitly
provides the request; it must not make automatic classifier calls or alter
permissions or model selection.
