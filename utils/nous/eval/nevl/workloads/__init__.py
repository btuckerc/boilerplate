"""Workload modules, by NAME. Interface: see any module (speed.py is the simplest).

NAME, VERSION (bump when items or scoring change), METRICS {field: "higher" |
"lower" | "rate"}, MUST_PASS and REPORTED (metric roles, see compare.py),
NEEDS_GRADE, items(tier, opts, data_dir), run_item(ctx, item) -> row,
summarize(rows), optional grade(rows, data_dir), fetch(data_dir) and INPUTS (data
files or directories, relative to data_dir, read beyond the items: the runner
fingerprints them so a resume or grade never mixes two versions).
"""
from . import concurrency, grounding, lcb, longctx, replay, speed, toolcall, vision

REGISTRY = {m.NAME: m for m in (speed, longctx, replay, concurrency, toolcall, lcb, vision, grounding)}
