---
name: local-workers
description: Route independently checkable work to nous or Luna during multi-step coding, test drafting, research synthesis, or log analysis. Prefer local workers for bounded file tasks and Luna for broader tool work; keep demanding decisions with the main model. Not needed for trivial edits.
---

# Local workers

Choose routing without asking the user to pick a model. Native nous is limited
to small mechanical transforms, extraction and predetermined edits with cheap
parent verification. Use Luna medium for ordinary code and tests, broader tool
work, larger context, or local-worker failure. In OMP, consult the read-only
`architect` agent (`@plan`, Astra medium) only for ambiguous architecture,
conflicting evidence or stalled diagnosis. In Codex, keep those decisions with
the parent or an explicitly selected frontier worker. Routine edits do not require a
planning or review stage. Trivial work stays in the parent when delegation
would cost more. Existing project rules apply; no delegation quota.

For native Codex Luna workers, use a fresh brief (`fork_turns="none"`,
`model="gpt-5.6-luna"`) rather than copying the parent thread. Medium suits
ordinary implementation and tests; preserve explicit user model/effort choices.
Full-history forks inherit the parent model, so they are not the cheap-worker
path. OMP callers use their supported equivalent.

`nous-worker` defaults to **Ornith**. **Gemma** is an optional alternative;
**Bonsai** requires its separate backend. Ornith and Gemma failed novel
algorithmic edge cases, so do not auto-route algorithmic work to local models.
These remain bounded mechanical/extraction workers, not replacements for Luna
or the parent model.

```sh
nous-worker --dir /absolute/task-directory 'Task, allowed files, constraints, expected output and acceptance checks.'
nous-worker --dir /absolute/task-directory --session SESSION_ID 'Bounded follow-up.'
```

Use `--model gemma` or `--model bonsai` explicitly, including when resuming
those sessions. `--read-only` supports analysis. Prompts may come from stdin.
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
successful process exit is not verification. If a worker stalls or fails,
give at most one focused correction, then finish in the parent or choose a
stronger model; avoid model-shopping loops.

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
