"""Compare two candidates measured in the same run (ledger M13: never across sessions).

Metric kinds come from each workload's METRICS:
    "higher"/"lower"  timing-like; geometric-mean ratio, verdict against the speed tolerance
    "rate"            0..1 outcome; mean difference, non-inferiority verdict against the margin
Either way items are the resampling unit: reps and blocks of one item are averaged
first (cluster bootstrap), so repeats of one prompt never count as independent evidence.

Each metric has a role, from the workload's MUST_PASS and REPORTED:
    must pass   the verdict needs it to pass
    may fail    a significant loss fails the candidate; it need not prove a pass
                (small item sets that cannot certify non-inferiority)
    reported    shown, never decides (reference-dependent or exploratory)
A candidate that ran in two blocks (ABBA) also gets an A/A row: its second block
against its first, the run's own noise floor. A must-pass ratio whose A/A drifts
by more than twice the tolerance makes the run unstable: it cannot pass (ledger M44).
"""
from __future__ import annotations

import statistics
from collections import defaultdict

from . import stats
from .store import Run
from .workloads import REGISTRY


class CompareError(ValueError):
    pass


def compare(run: Run, a: str | None = None, b: str | None = None) -> dict:
    """B against A. With one candidate (b omitted or equal to a) only its A/A noise is reported."""
    plan = run.plan
    labels = list(dict.fromkeys(plan["blocks"]))
    a = a or labels[0]
    b = b or next((x for x in labels if x != a), a)
    for label in (a, b):
        if label not in plan["candidates"]:
            raise CompareError(f"{label!r} was not measured in run {run.run_id}; cross-run comparison is refused")
    rows = run.graded_rows()
    rules = plan["compare"]
    done = run.done() or {}
    report = {"run_id": run.run_id, "tier": plan["tier"], "a": a, "b": b,
              "complete": done.get("status") == "ok", "workloads": {}}
    for spec in plan["workloads"]:
        name = spec["name"]
        module = REGISTRY[name]
        if module.VERSION != spec["version"]:
            raise CompareError(f"{name}: plan has version {spec['version']}, code has {module.VERSION}")
        mine = [r for r in rows if r["workload"] == name]
        if any(r["version"] != spec["version"] for r in mine):
            raise CompareError(f"{name}: rows from another workload version")
        if module.NEEDS_GRADE and any("error" not in r and "graded" not in r for r in mine):
            raise CompareError(f"{name}: ungraded rows; run `nous-eval grade {run.run_id}` first")
        report["workloads"][name] = _workload(module, mine, a, b, plan["blocks"], rules)
    report["unstable"] = _unstable(report, rules["tolerance"])
    report["verdict"] = _overall(report)
    return report


def _unstable(report: dict, tolerance: float) -> list[str]:
    """Must-pass ratio metrics whose A/A effect lies outside 1 -/+ 2x tolerance.

    ABBA cancels slow drift; a swing this large means the engine ran in two
    states (it did: vLLM's host loop on P- or E-cores), and their mean is no
    measurement of either."""
    low, high = 1 - 2 * tolerance, 1 / (1 - 2 * tolerance)
    return [f"{name}/{x['metric']} {x['label']} A/A {x['effect']:.3f}"
            for name, w in report["workloads"].items()
            for x in w["aa"]
            if x["kind"] != "rate" and x["effect"] is not None and not low <= x["effect"] <= high
            and x["metric"] in REGISTRY[name].MUST_PASS]


def _workload(module, rows: list[dict], a: str, b: str, blocks: list[str], rules: dict) -> dict:
    good = [r for r in rows if "error" not in r]
    sides = list(dict.fromkeys((a, b)))
    out = {"metrics": [], "aa": [],
           "errors": {x: sum(1 for r in rows if r["candidate"] == x and "error" in r) for x in sides},
           "leaks": {x: sum(1 for r in rows if r["candidate"] == x and r.get("reasoning_leak")) for x in sides},
           "summary": {x: module.summarize([r for r in rows if r["candidate"] == x]) for x in sides}}
    if a != b:
        for metric, kind in module.METRICS.items():
            result = _metric(good, metric, kind, lambda r, x: r["candidate"] == x, a, b, rules)
            out["metrics"].append({"metric": metric, "kind": kind, "role": _role(module, metric), **result})
    for label in sides:
        own = [i for i, x in enumerate(blocks) if x == label]
        if len(own) < 2:
            continue
        first, last = own[0], own[-1]
        for metric, kind in module.METRICS.items():
            result = _metric([r for r in good if r["candidate"] == label], metric, kind,
                             lambda r, blk: r["block"] == blk, first, last, rules)
            out["aa"].append({"label": label, "metric": metric, "kind": kind, **result})
    return out


def _role(module, metric: str) -> str:
    if metric in module.MUST_PASS:
        return "must pass"
    return "reported" if metric in module.REPORTED else "may fail"


def _metric(rows, metric, kind, select, a, b, rules) -> dict:
    if kind not in ("rate", "higher", "lower"):
        raise CompareError(f"unknown metric kind {kind!r} for {metric}")
    unit = lambda r: r["item"]
    values = {a: defaultdict(list), b: defaultdict(list)}
    for row in rows:
        value = row.get(metric)
        if value is None:
            continue
        for side in (a, b):
            if select(row, side):
                values[side][unit(row)].append(float(value))
    shared = sorted(set(values[a]) & set(values[b]), key=str)
    pairs = [(statistics.fmean(values[a][k]), statistics.fmean(values[b][k])) for k in shared]
    if kind == "rate":
        result = stats.rate_difference(pairs, rules["margin"])
    else:
        result = stats.ratio(pairs, kind == "higher", rules["tolerance"])
    result["a_mean"] = statistics.fmean(p[0] for p in pairs) if pairs else None
    result["b_mean"] = statistics.fmean(p[1] for p in pairs) if pairs else None
    result["unpaired"] = len(set(values[a]) ^ set(values[b]))
    return result


def _overall(report: dict) -> str:
    """fail: B errored or leaked anywhere, or any deciding metric failed.
    pass: the run finished ok, A is clean too, and every must-pass metric passed.
    Otherwise inconclusive."""
    a, b = report["a"], report["b"]
    workloads = list(report["workloads"].values())
    if any(w["errors"][b] or w["leaks"][b] for w in workloads):
        return "fail"
    deciding = [m for w in workloads for m in w["metrics"] if m["role"] != "reported"]
    if any(m["verdict"] == "fail" for m in deciding):
        return "fail"
    must = [m for m in deciding if m["role"] == "must pass"]
    a_clean = not any(w["errors"][a] or w["leaks"][a] for w in workloads)
    if (report["complete"] and a_clean and not report["unstable"] and must
            and all(m["verdict"] == "pass" for m in must)):
        return "pass"
    return "inconclusive"


def markdown(report: dict) -> str:
    a, b = report["a"], report["b"]
    lines = [f"# {b} vs {a} (run {report['run_id']}, {report['tier']})", "",
             f"Verdict: **{report['verdict']}**" + ("" if report["complete"] else " (run not finished ok)"), ""]
    if report["unstable"]:
        lines += ["Unstable (A/A beyond twice the tolerance; no pass until a stable rerun): "
                  + "; ".join(report["unstable"]), ""]
    lines += ["Ratio metrics: B/A oriented so >1 is better. Rate metrics: B-A difference.", "",
              f"| workload | metric | role | n | {a} | {b} | effect | 95% CI | verdict |",
              "|---|---|---|---:|---:|---:|---:|---|---|"]
    for name, w in report["workloads"].items():
        for m in w["metrics"]:
            lines.append(f"| {name} | {m['metric']} | {m['role']} | {m['n']} | {_num(m['a_mean'])} | "
                         f"{_num(m['b_mean'])} | {_num(m['effect'])} | {_num(m['lo'])} .. {_num(m['hi'])} | "
                         f"{m['verdict']} |")
    noise = [(name, x) for name, w in report["workloads"].items() for x in w["aa"]]
    if noise:
        lines += ["", "## A/A noise (last block vs first block of the same candidate)", "",
                  "| workload | candidate | metric | n | effect | 95% CI |", "|---|---|---|---:|---:|---|"]
        for name, x in noise:
            lines.append(f"| {name} | {x['label']} | {x['metric']} | {x['n']} | {_num(x['effect'])} | "
                         f"{_num(x['lo'])} .. {_num(x['hi'])} |")
    lines += ["", "## Summaries", ""]
    for name, w in report["workloads"].items():
        lines.append(f"- **{name}**: errors {w['errors']}, reasoning leaks {w['leaks']}")
        for label, summary in w["summary"].items():
            lines.append(f"  - {label}: " + ", ".join(f"{k}={_num(v)}" for k, v in summary.items()))
    return "\n".join(lines) + "\n"


def _num(x) -> str:
    if x is None:
        return "-"
    if isinstance(x, float):
        return f"{x:.4g}"
    if isinstance(x, dict):
        return "{" + ", ".join(f"{k}: {_num(v)}" for k, v in x.items()) + "}"
    return str(x)


def write(run: Run, report: dict) -> str:
    stem = f"compare.{report['a']}.{report['b']}"
    run.write_json(stem + ".json", report)
    text = markdown(report)
    (run.path / f"{stem}.md").write_text(text)
    return text
