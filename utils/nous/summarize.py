#!/usr/bin/env python3
"""Summarize saved checks; decode throughput is not end-to-end latency."""
import json
import statistics
from pathlib import Path

root = Path(__file__).resolve().parent / "results"
summary = {"api": {}, "coding": {}}
for path in sorted(root.glob("*.jsonl")):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    if not rows:
        continue
    speeds = [call["response"].get("timings", {}).get("predicted_per_second")
              for row in rows for call in row["calls"]]
    speeds = [v for v in speeds if v]
    successful = [r["seconds"] for r in rows if r["passed"]]
    summary["api"][path.stem] = {
        "checks": len(rows), "passed": sum(r["passed"] for r in rows),
        "median_task_seconds": statistics.median(r["seconds"] for r in rows),
        "median_success_seconds": statistics.median(successful) if successful else None,
        "median_decode_tokens_per_second": statistics.median(speeds) if speeds else None,
        "truncated_calls": sum(call["response"]["choices"][0].get("finish_reason") == "length"
                               for row in rows for call in row["calls"]),
        "failures": [{"task":r["task"],"repeat":r["repeat"],"error":r.get("error"),
                      "actual":r.get("actual")} for r in rows if not r["passed"]],
    }
for path in sorted(root.glob("*-coding.json")):
    row = json.loads(path.read_text())
    events = []
    for line in (row.get("stdout") or "").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "tool_use":
            events.append(event.get("part", {}).get("tool"))
    summary["coding"][path.stem] = {"seconds":row["seconds"],"tools":events,
        "grade":row.get("grade"),"timeout":row.get("timeout",False),
        "total_seconds":row.get("total_seconds",row["seconds"])}
(root / "summary.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary,indent=2))
