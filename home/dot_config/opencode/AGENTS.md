Operate quietly. Ship diffs and passing tests. Ask only when action is irreversible.

## Defaults

- Use the **Build** agent by default (full tools). Switch to **Plan** only for multi-file or risky refactors. :contentReference[oaicite:4]{index=4}
- Prefer official docs. For library or framework questions, **use context7** and cite the exact source URL you used. :contentReference[oaicite:5]{index=5}
- Keep output minimal:
  - Actions taken (bullets)
  - Diffs/patches
  - Test/log summaries
  - Next steps (if any)

## Workflow

1. Short plan: goal, files, tests to run.
2. Implement in small, reversible patches.
3. Run fast checks locally:
   - Lint/format
   - Unit/integration tests
   - Type checks
4. If any check fails, fix before proceeding.
5. Summarize: what changed, why, verification.

## Tool use

- File ops and edits: allowed.
- `bash`: allowed for local dev tasks and test runs.
- Always show the command list before long-running or network-heavy steps.
- Never run destructive or billing-impacting ops without a one-line confirmation request:
  - Dropping or rewriting DB data
  - Cloud infra changes or charges
  - `rm -rf`, mass renames, or history rewrites

## Context discipline

- Load only what’s needed. Avoid mass-reading the repo.
- Use **context7** for APIs, migrations, and framework changes. Include version when relevant. :contentReference[oaicite:6]{index=6}
- Do not paste full docs; quote only the lines used.

## Code quality

- Match the project’s style and patterns.
- Name things clearly. Keep functions small.
- Add/adjust tests for new logic or bug fixes.
- Watch performance: avoid N+1, needless I/O, and O(n²) loops on hot paths.

## Security

- Validate inputs at boundaries.
- Respect authz checks.
- Don’t log secrets or PII.
- Watch for XSS, SQLi, CSRF, SSRF, unsafe deserialization.

## Languages

- **TypeScript/JS**: ES2022+, async/await, strict types.
- **Python**: PEP 8, type hints on public funcs, narrow exceptions.
- **Rails**: Thin controllers, AR scopes/concerns, strong params, CSRF helpers.

## Tests & evidence

- Run tests before and after changes; include a short diff of failures fixed.
- For UI flows, generate or update Playwright tests (if available) and keep them deterministic.

## Metrics (tracked outside this file)

- Task completion time, PR cycle time, first-CI pass rate, rework rate. RCTs show large speed gains for scoped coding tasks; validate locally with these metrics. :contentReference[oaicite:7]{index=7}
