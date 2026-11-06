"""Plan, execute, resume and grade runs.

A run is one session: every candidate it compares is measured in it, in blocks
(ABBA by default, so drift hits both sides). `run` plans and creates the run,
then re-executes `nous-eval resume <id>` inside a GPU lease in llama.slice. A
run killed by the lease runtime resumes where its durable rows stop. Grading
(sandboxed CPU work) happens after the lease returns the GPU to production.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import guards
from .candidate import manifest
from .ctx import DATA_DIR, DEFAULT_SAMPLING, Context
from .server import Server, vram_mib
from .store import Run, row_key
from .workloads import REGISTRY

PACKAGE = Path(__file__).resolve().parents[1]
NOUS_EVAL = PACKAGE / "nous-eval"
TIERS = PACKAGE / "tiers.toml"
LEASE_PORT = 18737


class PlanError(ValueError):
    pass


def load_tiers(path: Path = TIERS) -> dict:
    return tomllib.loads(path.read_text())


def blocks_for(labels: list[str], design: str) -> list[str]:
    if len(set(labels)) != len(labels):
        raise PlanError(f"duplicate candidate labels: {labels}")
    if design == "abba":
        return labels + labels[::-1]
    if design == "ab":
        return list(labels)
    raise PlanError(f"unknown design {design!r} (abba, ab)")


def plan_run(tier: str, candidates: list[dict], *, design: str | None = None, reps: int | None = None,
             workers: int | None = None, workloads: list[str] | None = None, port: int = LEASE_PORT,
             lease: bool = True, tiers: dict | None = None) -> dict:
    tiers = tiers or load_tiers()
    if tier not in tiers.get("tiers", {}):
        raise PlanError(f"unknown tier {tier!r}; tiers: {sorted(tiers.get('tiers', {}))}")
    spec = tiers["tiers"][tier]
    names = workloads or list(spec["workloads"])
    specs = []
    for name in names:
        if name not in spec["workloads"]:
            raise PlanError(f"tier {tier} has no workload {name!r}")
        options = dict(spec["workloads"][name])
        specs.append({"name": name, "version": REGISTRY[name].VERSION,
                      "items_tier": options.pop("items_tier", tier),
                      "reps": reps or options.pop("reps", 1),
                      "workers": workers or options.pop("workers", 1),
                      "opts": {k: v for k, v in options.items() if k not in ("reps", "workers")}})
    labels = [c["label"] for c in candidates]
    blocks = blocks_for(labels, design or spec.get("design", "abba"))
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return {"run_id": f"{stamp}-{tier}-{'-vs-'.join(labels)}"[:120],
            "tier": tier, "created": time.time(), "port": port, "lease": lease,
            "budget_s": spec["budget_s"], "blocks": blocks,
            "candidates": {c["label"]: c for c in candidates}, "workloads": specs,
            "tier_workloads": list(spec["workloads"]),  # promote refuses a --workloads subset
            "sampling": DEFAULT_SAMPLING, "compare": tiers["compare"]}


def lease_runtime(plan: dict) -> int:
    """Lease seconds: per-block budget plus load allowance, 25% slack (ledger M5)."""
    total = sum(plan["budget_s"] + plan["candidates"][label]["ready_timeout_s"] for label in plan["blocks"])
    return max(600, min(86400, int(total * 1.25)))


def lease_argv(plan: dict) -> list[str]:
    """argv for llama-yield; never a shell string (ledger M14)."""
    argv = [sys.executable, str(NOUS_EVAL), "resume", plan["run_id"]]
    lease = ["llama-yield", "--runtime", str(lease_runtime(plan)), "--label", f"nous-eval {plan['run_id']}"[:80],
             "--slice", "llama.slice", "--directory", str(PACKAGE)]
    if "NOUS_EVAL_ROOT" in os.environ:
        lease += ["--env", "NOUS_EVAL_ROOT=" + os.environ["NOUS_EVAL_ROOT"]]
    full = [*lease, "--", *argv]
    bad = [a for a in full if not a.isprintable()]
    if bad:
        raise PlanError(f"non-printable lease arguments: {bad!r}")
    return full


def in_lease(proc_cgroup: Path = Path("/proc/self/cgroup")) -> bool:
    return guards.LEASE_UNIT in proc_cgroup.read_text()


def start(run: Run, max_leases: int = 3) -> int:
    """Run (or continue) a planned run: under a lease if the plan wants the GPU.

    A lease that ends before the run does (its runtime ran out) is followed by
    another, after production has been checked, up to max_leases."""
    plan = run.plan
    try:
        build_items(plan)  # missing data must fail here, not after production stopped (ledger M26)
    except Exception as error:
        print(f"cannot build items ({type(error).__name__}: {error}); try: nous-eval fetch", file=sys.stderr)
        return 1
    if not plan["lease"]:
        status = execute(run)
        return grade(run) or status
    if in_lease():
        return execute(run)
    for attempt in range(1, max_leases + 1):
        checks = guards.run("host", guards.Host(plan=plan))
        _print_checks(checks)
        if guards.failed(checks):
            print("preflight failed; not taking the GPU", file=sys.stderr)
            return 1
        print(f"lease {attempt}/{max_leases} for {run.run_id}: up to {lease_runtime(plan) / 3600:.1f} h "
              f"without production", flush=True)
        status = subprocess.run(lease_argv(plan)).returncode
        healthy, detail = guards.production_health()
        print(("production ok: " if healthy else "PRODUCTION NOT HEALTHY: ") + detail, flush=True)
        if not healthy:
            return 1
        if run.done():
            return grade(run) or status
    print(f"run {run.run_id} is incomplete after {max_leases} leases; continue with: nous-eval resume {run.run_id}",
          file=sys.stderr)
    return 1


def build_items(plan: dict) -> dict[str, list[dict]]:
    return {spec["name"]: REGISTRY[spec["name"]].items(spec["items_tier"], spec["opts"], DATA_DIR)
            for spec in plan["workloads"]}


def execute(run: Run) -> int:
    plan = run.plan
    (run.path / "done.json").unlink(missing_ok=True)  # a resumed run is open until it finishes again
    if plan["lease"]:
        checks = guards.run("lease", guards.Host(plan=plan))
        _print_checks(checks)
        run.write_json(f"preflight.{int(time.time())}.json", {"checks": checks})
        if guards.failed(checks):
            run.finish("failed", reason="lease preflight", checks=checks)
            return 1
    try:
        items = build_items(plan)
    except Exception as error:
        run.finish("failed", reason=f"items: {type(error).__name__}: {error}")
        raise
    changed = _check_inputs(run, items)
    if changed:
        run.finish("failed", reason=changed)
        print(changed, file=sys.stderr)
        return 1
    finished = {row_key(r) for r in run.rows() if "error" not in r}
    block_failures = []
    for block, label in enumerate(plan["blocks"]):
        todo = [(spec, rep, item) for spec in plan["workloads"] for rep in range(spec["reps"])
                for item in items[spec["name"]]
                if (block, label, spec["name"], item["id"], rep) not in finished]
        if not todo:
            continue
        candidate = plan["candidates"][label]
        changed = _check_manifest(run, label, manifest(candidate))
        if changed:
            block_failures.append(f"block {block} ({label}): {changed}")
            print(block_failures[-1], file=sys.stderr, flush=True)
            continue
        if plan["lease"]:
            status, detail = guards.vram_free(guards.Host(plan=plan))  # ledger M29, between blocks too
            if status == "fail":
                block_failures.append(f"block {block} ({label}): {detail}")
                print(block_failures[-1], file=sys.stderr, flush=True)
                continue
        server = Server(candidate, run.path, plan["port"])
        print(f"block {block}: {label}, {len(todo)} items", flush=True)
        previous = signal.signal(signal.SIGTERM, lambda signum, frame: _killed(server))
        try:
            vram_before = _vram()
            load_s = server.start()
            _record_block(run, label, block, {"load_s": load_s, "vram_mib_before": vram_before,
                                              "vram_mib_loaded": _vram()})
            _run_items(run, plan, block, label, server.base_url, todo)
            server.check_alive()  # an engine that crashed mid-block fails the block by name
            _record_block(run, label, block, {"vram_mib_end": _vram(), "ended": time.time()})
        except Exception as error:
            block_failures.append(f"block {block} ({label}): {error}")
            print(block_failures[-1], file=sys.stderr, flush=True)
        finally:
            server.stop()
            signal.signal(signal.SIGTERM, previous)
    return _finish(run, plan, items, block_failures)


def _check_inputs(run: Run, items: dict) -> str | None:
    """Every lease of a run, and its grading, uses the same inputs (council S-06, A-05):
    the first records a fingerprint per workload, later ones must match it."""
    digests = {name: _fingerprint(name, rows) for name, rows in items.items()}
    recorded = run.read_json("inputs.json")
    if recorded is None:
        run.write_json("inputs.json", digests)
        return None
    differ = sorted(name for name in digests if recorded.get(name) != digests[name])
    return f"workload inputs changed since the run started: {differ}; start a new run" if differ else None


def _fingerprint(name: str, rows: list[dict]) -> str:
    """The items plus every data file the workload reads beyond them (its INPUTS)."""
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True).encode())
    for relative in getattr(REGISTRY[name], "INPUTS", ()):
        path = DATA_DIR / relative
        for file in sorted(path.rglob("*")) if path.is_dir() else [path]:
            if file.is_file():
                digest.update(str(file.relative_to(DATA_DIR)).encode())
                with file.open("rb") as f:
                    for chunk in iter(lambda: f.read(1 << 20), b""):
                        digest.update(chunk)
    return digest.hexdigest()


def _check_manifest(run: Run, label: str, current: dict) -> str | None:
    """A candidate's engine, weights and settings may not change mid-run (council A-05)."""
    name = f"manifest.{label}.json"
    recorded = run.read_json(name)
    if recorded is None:
        run.write_json(name, {**current, "blocks": {}})
        return None
    differ = sorted(k for k in set(recorded) | set(current) if k != "blocks" and recorded.get(k) != current.get(k))
    return f"candidate changed since the run started ({differ}); start a new run" if differ else None


def _killed(server: Server) -> None:
    """SIGTERM (the lease ran out or was stopped): free the GPU, then exit.

    Rows are already durable; resume continues the run."""
    print("terminated: stopping the candidate", file=sys.stderr, flush=True)
    server.kill()
    os._exit(143)


def _run_items(run: Run, plan: dict, block: int, label: str, base_url: str, todo: list) -> None:
    candidate = plan["candidates"][label]
    lock = threading.Lock()

    def one(task):
        spec, rep, item = task
        module = REGISTRY[spec["name"]]
        ctx = Context(base_url, candidate["model"], sampling=plan["sampling"], request=candidate["request"],
                      seed=1000 * rep, data_dir=DATA_DIR, run_dir=run.path)
        row = {"block": block, "candidate": label, "workload": spec["name"], "version": spec["version"],
               "item": item["id"], "rep": rep, "seed": ctx.seed}
        started = time.time()
        try:
            row.update(module.run_item(ctx, item))
            row["reasoning_leak"] = ctx.leaks > 0
        except Exception as error:
            row["error"] = f"{type(error).__name__}: {error}"[:1000]
        row["ts"], row["elapsed_s"] = time.time(), time.time() - started
        with lock:
            run.append(row)
            if ctx.replies:
                run.append({**{k: row[k] for k in ("block", "candidate", "workload", "item", "rep")},
                            "replies": ctx.replies}, "replies.jsonl")

    for spec in plan["workloads"]:
        mine = [t for t in todo if t[0] is spec]
        with ThreadPoolExecutor(max_workers=spec["workers"]) as pool:
            list(pool.map(one, mine))


def _record_block(run: Run, label: str, block: int, values: dict) -> None:
    name = f"manifest.{label}.json"
    data = run.read_json(name)
    data["blocks"].setdefault(str(block), {}).update(values)
    run.write_json(name, data)


def _vram() -> int | None:
    try:
        return vram_mib()
    except (OSError, RuntimeError):
        return None


def _finish(run: Run, plan: dict, items: dict, block_failures: list[str]) -> int:
    rows = run.rows()
    present = {row_key(r) for r in rows}
    expected = {(block, label, spec["name"], item["id"], rep)
                for block, label in enumerate(plan["blocks"]) for spec in plan["workloads"]
                for rep in range(spec["reps"]) for item in items[spec["name"]]}
    errors = [f"{r['workload']}/{r['item']}#{r['rep']} {r['candidate']}: {r['error']}" for r in rows if "error" in r]
    leaks = [f"{r['workload']}/{r['item']}#{r['rep']} {r['candidate']}" for r in rows if r.get("reasoning_leak")]
    missing = len(expected - present)
    ok = not (errors or leaks or missing or block_failures)
    run.finish("ok" if ok else "failed", errors=errors[:50], error_count=len(errors), leaks=leaks[:50],
               missing=missing, block_failures=block_failures)
    print(f"run {run.run_id}: {'ok' if ok else 'FAILED'}; {len(errors)} errors, {len(leaks)} reasoning leaks, "
          f"{missing} missing, {len(block_failures)} failed blocks", flush=True)
    return 0 if ok else 1


def grade(run: Run) -> int:
    """Grade NEEDS_GRADE rows not yet graded. Outside the lease: CPU only."""
    plan = run.plan
    changed = _check_inputs(run, build_items(plan))  # grading data is an input too
    if changed:
        print(changed, file=sys.stderr)
        return 1
    graded = {row_key(r): r for r in run.graded_rows() if r.get("graded")}
    for spec in plan["workloads"]:
        module = REGISTRY[spec["name"]]
        if not module.NEEDS_GRADE:
            continue
        pending = [r for r in run.rows()
                   if r["workload"] == spec["name"] and "error" not in r and row_key(r) not in graded]
        if pending:
            print(f"grading {len(pending)} {spec['name']} rows", flush=True)
            for row in module.grade(pending, DATA_DIR):
                graded[row_key(row)] = {**row, "graded": True}
    if graded:
        run.write_graded(list(graded.values()))
    return 0


def parse_overrides(pairs: list[str]) -> dict:
    out = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not re.match(r"^[A-Za-z0-9_.-]+$", key):
            raise PlanError(f"--set wants key=value (a preset key, flag or env name), got {pair!r}")
        out[key] = value
    return out


def _print_checks(checks: list[dict]) -> None:
    for c in checks:
        print(f"{c['status']:>5}  {c['id']}: {c['detail']}", flush=True)


def describe(run: Run) -> str:
    plan, done = run.plan, run.done()
    return json.dumps({"run_id": run.run_id, "tier": plan["tier"], "blocks": plan["blocks"],
                       "rows": len(run.rows()), "done": done}, indent=2)
