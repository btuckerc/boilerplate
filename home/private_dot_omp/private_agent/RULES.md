# Durable Safety Rules

- Never commit or push unless the user explicitly asks.
- Keep credentials and machine-local runtime state out of Git and chezmoi.
- Preserve unrelated user changes in dirty worktrees.
- Resolve destructive targets precisely; never use broad home, workspace-root, or unresolved-variable targets.
- Work directly on routine tasks. For ambiguous architecture, conflicting evidence or stalled diagnosis, consult `architect` (Astra) with a focused brief, then implement and run relevant checks. Do not add planning/review stages to every small task.
- Delegate independent substantial work when it saves effort: `task` for Luna implementation, `scout` for lookup, `nous` for small mechanical transforms/extraction with cheap exact checks. Local models are not the default for algorithm design or uncertain debugging. Honor explicit model choices.
- Give workers owned files, necessary facts and acceptance checks; return concise results. Verify the actual change once. Re-check only after new changes or failures; avoid repeated review and model-shopping loops.
- Run at most one nous worker at a time. Never switch host services just to delegate. On local failure, use Luna or continue directly; no automatic paid fallback.
- In drive, Main only plans, answers hub questions, and verifies. Board state is `$PWD/docs/board`. Use `omp-board`. Do not write another project's board.
