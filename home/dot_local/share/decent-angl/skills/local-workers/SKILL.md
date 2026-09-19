---
name: local-workers
description: Delegate bounded code edits, test drafting, or log analysis to local models on nous when an independently checkable worker task would save main-thread effort. Also use when asked for local subagents. Not needed for trivial edits or tightly coupled reasoning.
---

# Local workers

Consider one local worker for a self-contained task while the main thread
continues useful work. Use judgment, not a delegation quota. Keep architecture,
integration and final verification with the parent. Existing project rules apply.

`nous-worker` defaults to **Ornith**. **Gemma** is an optional alternative;
**Bonsai** requires its separate backend. Nemotron remains experimental because
tool execution is inconsistent. These are tested bounded workers, not assumed
replacements for the parent model.

```sh
nous-worker --dir /absolute/task-directory 'Task, allowed files, constraints, expected output and acceptance checks.'
nous-worker --dir /absolute/task-directory --session SESSION_ID 'Bounded follow-up.'
```

Use `--model gemma` or `--model bonsai` explicitly, including when resuming
those sessions. `--read-only` supports analysis. Prompts may come from stdin.
Workers receive the task and directory context, not the parent conversation.
Supply the necessary facts; do not copy the whole thread.

Collect JSON events and the session ID with the task's evidence. Inspect actual
file changes and run the relevant checks in the parent. A claimed result or
successful process exit is not verification. If a worker stalls or fails,
give at most one focused correction, then finish in the parent or choose a
stronger model; avoid model-shopping loops.

Run one nous request at a time: the GPU has one inference slot. File tools
run on the workstation; shell/web/further delegation are disabled. OpenCode
permissions are not an OS sandbox, so use a scoped task directory or approved
checkout and respect one-writer ownership. The parent handles builds.

This is an OpenCode subprocess, not a native Codex `spawn_agent` child.
It works from terminal-capable T3/Codex/OMP threads without changing their
main model. If the command or host is unavailable, continue the main task;
do not bootstrap a machine or interrupt another inference job just to delegate.
The launcher does not switch services. For intentional backend switching or
host maintenance, use platform-ops; ordinary workers need no host setup.
