# Durable Safety Rules

- Never commit or push unless the user explicitly asks.
- Keep credentials and machine-local runtime state out of Git and chezmoi.
- Preserve unrelated user changes in dirty worktrees.
- Resolve destructive targets precisely; never use broad home, workspace-root, or unresolved-variable targets.
- Astra directs; keep trivial work direct. Prefer `nous` for bounded implementation with clear scope, contract and runnable acceptance, plus mechanical edits/extraction. Settle risky design decisions, not every implementation detail. Use `task` (Luna) for unresolved design, novel algorithms, uncertain debugging, broad/tool-rich work, large context or a failed local repair.
- Give workers fresh scoped briefs: owned files, contract, risky invariants and acceptance command; reuse supplied requirements rather than writing a full solution or transcript. State observable edge cases explicitly. Return paths, checks, short summary and blockers. The parent runs independent checks and reviews the result before acceptance.
- Supervise at natural checkpoints with `hub`; check unexpected silence, steer as needed, cancel/escalate blockers or budget overruns. After local failure, allow at most one focused repair before Luna or direct work; ordinary steering remains unrestricted.
- When blocked solely on a bounded local child, prefer native eval `agent(..., {agent:"nous"})`, a finite handle wait, and the pre-agreed parent check in one cell. Keep the handle for cancellation; the cell timeout alone does not bound agent waiting. Use background task/hub when there is independent work or active steering.
- Omit task `effort` for configured medium. Use `lo` for routine cloud tasks; retain medium for local implementation. Coarse `med` is model-relative (currently high on Astra/Luna); do not use it to request medium. Reserve `hi` for justified difficult cloud work, not local retries.
- No compulsory classifier, swarm, planner, routine `architect`, transcript polling or advisor loop.
- Run one nous worker at a time. Never switch host services just to delegate or silently fall back to paid inference.
