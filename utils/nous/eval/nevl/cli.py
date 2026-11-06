"""nous-eval: measure local inference candidates against production, safely."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import build, guards, store
from .candidate import incumbent, load
from .compare import compare, write
from .ctx import DATA_DIR
from .runner import LEASE_PORT, describe, grade, in_lease, parse_overrides, plan_run, start
from .workloads import REGISTRY


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nous-eval", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("preflight", help="host guards (no GPU)")

    p = sub.add_parser("run", help="plan a run and execute it (under a GPU lease unless --no-lease)")
    p.add_argument("tier")
    p.add_argument("-c", "--candidate", action="append", default=[], type=Path, help="candidate TOML")
    p.add_argument("--incumbent", action="store_true", help="include production, derived from the live unit")
    p.add_argument("--design", choices=["abba", "ab"])
    p.add_argument("--reps", type=int)
    p.add_argument("--workers", type=int)
    p.add_argument("--workloads", help="comma-separated subset of the tier's workloads")
    p.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                   help="one-factor tuning: measure every -c candidate both as-is and with these "
                        "overrides (preset keys, or start-argv flags for command candidates)")
    p.add_argument("--no-lease", action="store_true", help="CPU smoke runs only; never the GPU")
    p.add_argument("--port", type=int, default=LEASE_PORT)
    p = sub.add_parser("plan", help="resolve candidates and print the frozen plan without executing")
    p.add_argument("tier")
    p.add_argument("-c", "--candidate", action="append", default=[], type=Path, help="candidate TOML")
    p.add_argument("--incumbent", action="store_true")
    p.add_argument("--design", choices=["abba", "ab"])
    p.add_argument("--reps", type=int)
    p.add_argument("--workers", type=int)
    p.add_argument("--workloads")
    p.add_argument("--port", type=int, default=LEASE_PORT)

    for name, text in (("resume", "continue a run"), ("grade", "grade a run's rows"), ("show", "run status")):
        sub.add_parser(name, help=text).add_argument("run_id")

    p = sub.add_parser("compare", help="compare two candidates of one run")
    p.add_argument("run_id")
    p.add_argument("--a")
    p.add_argument("--b")

    sub.add_parser("ls", help="list runs")
    sub.add_parser("incumbent", help="print production as a resolved candidate")
    p = sub.add_parser("fetch", help="download or build workload datasets")
    p.add_argument("workloads", nargs="*")

    p = sub.add_parser("build", help="build llama.cpp at a ref (in a systemd user unit)")
    p.add_argument("ref")
    p.add_argument("--backend", default="vulkan")
    p.add_argument("--patch", type=Path)
    p.add_argument("--here", action="store_true", help="build in this process")

    sub.add_parser("canary", help="export and measure latest radiance release")
    sub.add_parser("watch", help="check upstream model and engine changes")
    p = sub.add_parser("promote", help="check evidence, print promotion steps")
    p.add_argument("label")
    p.add_argument("--run", action="append", required=True, dest="runs")
    sub.add_parser("rollback", help="print the steps to undo the last promotion")

    args = parser.parse_args(argv)
    return COMMANDS[args.command](args)


def cmd_preflight(args) -> int:
    checks = guards.run("host")
    for c in checks:
        print(f"{c['status']:>5}  {c['id']}: {c['detail']}")
    return 1 if guards.failed(checks) else 0


def cmd_run(args) -> int:
    if args.port == 8080:
        print("port 8080 is production", file=sys.stderr)
        return 2
    overrides = parse_overrides(args.set)
    if overrides and not args.candidate:
        print("--set varies -c candidates; production itself never changes", file=sys.stderr)
        return 2
    candidates = [incumbent()] if args.incumbent else []
    for path in args.candidate:
        candidates.append(load(path))
        if overrides:
            candidates.append(load(path, overrides))  # same session, one factor apart
    if not candidates:
        print("no candidates: use --incumbent and/or -c FILE", file=sys.stderr)
        return 2
    plan = plan_run(args.tier, candidates, design=args.design, reps=args.reps, workers=args.workers,
                    workloads=args.workloads.split(",") if args.workloads else None,
                    port=args.port, lease=not args.no_lease)
    run = store.Run.create(plan)
    print(f"run {run.run_id}: blocks {plan['blocks']}", flush=True)
    return _start_and_compare(run)


def cmd_plan(args) -> int:
    candidates = [incumbent()] if args.incumbent else []
    candidates.extend(load(path) for path in args.candidate)
    if not candidates:
        print("no candidates: use --incumbent and/or -c FILE", file=sys.stderr)
        return 2
    plan = plan_run(args.tier, candidates, design=args.design, reps=args.reps, workers=args.workers,
                    workloads=args.workloads.split(",") if args.workloads else None,
                    port=args.port, lease=False)
    print(json.dumps(plan, indent=2))
    return 0


def cmd_resume(args) -> int:
    return _start_and_compare(store.Run.open(args.run_id))


def _start_and_compare(run: store.Run) -> int:
    status = start(run)
    done = run.done()
    if in_lease() or not done:
        return status
    if not run.rows():
        print(f"run {run.run_id} {done['status']} before measuring anything: {done.get('reason', '')}",
              file=sys.stderr)
        return status or 1
    labels = list(dict.fromkeys(run.plan["blocks"]))
    pairs = [(labels[0], other) for other in labels[1:] or labels]
    # each --set variant against its own base, the one-factor comparison
    pairs += [(base, variant) for base in labels[1:] for variant in labels
              if variant.startswith(base + ".") and (base, variant) not in pairs]
    for a, b in pairs:
        print(write(run, compare(run, a, b)))
    return status


def cmd_grade(args) -> int:
    return grade(store.Run.open(args.run_id))


def cmd_show(args) -> int:
    print(describe(store.Run.open(args.run_id)))
    return 0


def cmd_compare(args) -> int:
    run = store.Run.open(args.run_id)
    report = compare(run, args.a, args.b)
    print(write(run, report))
    return 0 if report["verdict"] != "fail" else 1


def cmd_ls(args) -> int:
    for r in store.list_runs():
        print(f"{r['run_id']}  {r['status']:>6}  {r['candidates']}")
    return 0


def cmd_incumbent(args) -> int:
    print(json.dumps(incumbent(), indent=2))
    return 0


def cmd_fetch(args) -> int:
    for name in args.workloads or list(REGISTRY):
        if hasattr(REGISTRY[name], "fetch"):
            print(f"fetching {name}", flush=True)
            REGISTRY[name].fetch(DATA_DIR)
    return 0


def cmd_build(args) -> int:
    if not args.here:
        return build.build_in_unit(args.ref, args.backend, args.patch)
    print(build.build(args.ref, args.backend, args.patch))
    return 0


def cmd_watch(args) -> int:
    from . import watch
    return watch.run()


COMMANDS = {"preflight": cmd_preflight, "run": cmd_run, "plan": cmd_plan, "resume": cmd_resume,
            "grade": cmd_grade, "show": cmd_show, "compare": cmd_compare, "ls": cmd_ls,
            "incumbent": cmd_incumbent, "fetch": cmd_fetch, "build": cmd_build,
            "canary": lambda args: build.canary(), "watch": cmd_watch,
            "promote": lambda args: build.promote(args.label, args.runs),
            "rollback": lambda args: build.rollback()}
