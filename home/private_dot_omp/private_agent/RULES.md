# Durable Safety Rules

- Never commit or push unless the user explicitly asks.
- Keep credentials and machine-local runtime state out of Git and chezmoi.
- Preserve unrelated user changes in dirty worktrees.
- Resolve destructive targets precisely; never use broad home, workspace-root, or unresolved-variable targets.
