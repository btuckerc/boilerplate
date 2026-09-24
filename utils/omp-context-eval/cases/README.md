# OMP context evaluation fixtures

Each directory is an independently runnable, synthetic acceptance fixture. The
`case.json` file is the harness contract: `task` is the worker prompt,
`allowed_files` and `allowed_tools` bound the work, and `checks` describe the
oracle. A runner should copy the case to a disposable directory, present only
the listed task and files, run the worker, then invoke `oracle.py` from the
case directory. Oracle results come from file contents or executable behavior;
worker self-report is never accepted.

These fixtures are a quality ablation set, not a published benchmark or a
claim about aggregate model capability. They deliberately mix mechanical work
with a reasoning edge case and should be run as paired baseline/ablation trials
with the same prompt, tool permissions, context limit, timeout, and retry
policy.
