# Local lane rules

- Every model here is the local Qwen on nous; there is no cloud model to escalate to. The llama.cpp server has one slot, so subagents take turns on the GPU: delegate only work that splits into independent slices, give each a scoped brief with an acceptance command, and verify results yourself.
- Never commit or push unless the user explicitly asks.
- Keep credentials and machine-local runtime state out of Git and chezmoi.
- Preserve unrelated user changes in dirty worktrees.
- Resolve destructive targets precisely; never use broad home, workspace-root, or unresolved-variable targets.
- There is no release auditor here. Work that needs one under the default profile's RULES (high-consequence control-plane, security, data-loss or cross-file integration changes, or an explicit audit request) waits for it there; its absence is not an exemption.
- Run the code you change and report only checks you actually ran; flag anything unverified in plain words.
