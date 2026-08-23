# Durable Safety Rules

- Never commit or push unless the user explicitly asks.
- Keep credentials and machine-local runtime state out of Git and chezmoi.
- Preserve unrelated user changes in dirty worktrees.
- Resolve destructive targets precisely; never use broad home, workspace-root, or unresolved-variable targets.
- Default chat implements itself. Do not spawn workers unless the user entered drive (`/drive`, `/board`, `/dispatch`, `/recover`, `/vibe`, or the words drive or swarm).
- In drive, Main only plans, answers hub questions, and verifies. Board state is `$PWD/docs/board`. Use `omp-board`. Do not write another project's board.
