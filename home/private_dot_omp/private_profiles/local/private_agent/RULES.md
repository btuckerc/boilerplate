# Local lane rules

- Every model here is the local Qwen on nous; there is no cloud model to escalate to. vLLM batches up to 8 sequences; subagents can run concurrently within the shared VRAM KV pool, so keep concurrency bounded at 4 and delegate only work that splits into independent slices, with a scoped brief and acceptance command.
- Never commit or push unless the user explicitly asks.
- Keep credentials and machine-local runtime state out of Git and chezmoi.
- Preserve unrelated user changes in dirty worktrees.
- Resolve destructive targets precisely; never use broad home, workspace-root, or unresolved-variable targets.
- There is no release auditor here. Work that needs one under the default profile's RULES (high-consequence control-plane, security, data-loss or cross-file integration changes, or an explicit audit request) waits for it there; its absence is not an exemption.
- Run the code you change and report only checks you actually ran; flag anything unverified in plain words.
