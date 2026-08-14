---
description: High-signal code review pass
argument-hint: "[scope]"
model: openai-codex/gpt-5.4
thinking: high
restore: true
---
Review $@ for correctness, regressions, edge cases, and missing verification.

Lead with concrete findings and file references. If you find no substantive issues, say that clearly and call out any remaining test gap.
