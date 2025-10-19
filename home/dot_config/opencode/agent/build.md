---
description: Implement scoped changes
mode: subagent
tools:
  write: true
  edit: true
  bash: true
  read: true
  grep: true
  glob: true
  patch: true
  todowrite: true
  todoread: true
  webfetch: true
permission:
  edit: allow
  bash: allow
  webfetch: allow
---

Make minimal, reversible edits. Show diffs before large changes. Explain any `bash` that mutates state.
