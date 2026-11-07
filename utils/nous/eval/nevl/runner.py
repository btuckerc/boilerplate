"""Plan, execute, resume and grade runs.

A run is one session: every candidate it compares is measured in it, in blocks
(ABBA by default, so drift hits both sides). `run` plans and creates the run,
then re-executes `nous-eval resume <id>` inside a GPU lease in llama.slice. A
run killed by the lease runtime resumes from its durable rows, keeping only rows
whose block attempt passed its end check. Grading (sandboxed CPU work) happens
after the lease returns the GPU to production.
"""
from __future__ import annotations

import fcntl
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
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import guards
from .candidate import manifest
from .ctx import DATA_DIR, DEFAULT_SAMPLING, Context
from .server import Server, vram_mib
from .store import Run, fsync_dir, row_key
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


def lease_argv(plan: dict, token: str) -> list[str]:
    """argv for llama-yield; never a shell string (ledger M14). token: the lease's claim (start())."""
    argv = [sys.executable, str(NOUS_EVAL), "resume", plan["run_id"], "--lease-token", token]
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


STOP_SIGNALS = (signal.SIGTERM, signal.SIGINT)
LEASE_CLAIM = "lease.claim"


def start(run: Run, max_leases: int = 3, *, automatic: bool = False, lease_token: str | None = None) -> int:
    """Run (or continue) a planned run: under a lease if the plan wants the GPU.

    A lease whose runtime ran out before the run finished is followed by another, after
    production has been checked, up to max_leases. A lease stopped any other way (by hand,
    a shutdown, a crash) ends the run here; it is resumed on purpose (council S-06).

    The client (this process, outside a lease) owns the run's state (release audits, M61). It
    takes the run's `lock`; a second process is refused. It alone writes stopped.json, which keeps
    boot recovery and the canary from resuming the run (council F-05): durably and at once when
    it is stopped, and after a lease that started and ended without running out. It clears the
    mark only when resumed by hand. automatic (boot recovery, the canary timer) leaves alone a run
    found stopped or finished once the lock is held, as it may have been stopped after the caller
    chose it.

    Inside a lease, only the command the client launched for it runs the run (_start_leased)."""
    if in_lease():
        return _start_leased(run, max_leases, automatic, lease_token)
    owner: dict = {}

    def owns() -> bool:
        # The run is this process's while it holds the lock: a flock on its own descriptor
        # succeeds then (or takes the free lock), and fails once another process holds it or
        # ours is closed. A flag set beside the flock would leave a signal a window either way.
        try:
            fcntl.flock(owner.get("lock"), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except (OSError, TypeError, ValueError):
            return False

    def stop(signum, frame):
        if owns():
            _mark_stopped(run)
            _say(f"stopped: run {run.run_id} stays stopped; continue with: nous-eval resume {run.run_id}")
        raise SystemExit(128 + signum)
    previous = {s: signal.signal(s, stop) for s in STOP_SIGNALS}
    try:
        owner["lock"] = open(run.path / "lock", "a")
        try:
            fcntl.flock(owner["lock"], fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(f"run {run.run_id} is being run by another nous-eval process", file=sys.stderr)
            return 1
        (run.path / LEASE_CLAIM).unlink(missing_ok=True)  # a client killed mid-lease left it
        stopped = run.path / "stopped.json"
        if automatic and stopped.exists():
            print(f"run {run.run_id} was stopped; continue with: nous-eval resume {run.run_id}", file=sys.stderr)
            return 1
        if automatic and run.done():
            return grade(run)
        if stopped.exists():  # resumed by hand: the one place a stop is undone
            stopped.unlink()
            fsync_dir(run.path)
        return _start(run, max_leases)
    finally:
        if owner.get("lock") is not None:
            owner["lock"].close()  # from here the run is not this process's, for the handler too
        for s, handler in previous.items():
            signal.signal(s, handler)


def _start_leased(run: Run, max_leases: int, automatic: bool, token: str | None) -> int:
    """Inside a lease, only the command a client launched for this lease runs the run: it
    presents the token the client wrote to `lease.claim` and removes the claim (the first one
    wins), finds that client still holding the run's lock, and holds `exec.lock` while it runs.
    It never writes or clears stopped.json (the client decides, from systemd's result), and does
    not start a run marked stopped: its client was stopped while the lease started."""
    def refuse(why: str) -> int:
        print(f"run {run.run_id} {why}; not run in this lease", file=sys.stderr)
        return 1
    if automatic:
        return refuse("is recovered and canaried only outside a lease")
    claim = run.path / LEASE_CLAIM
    try:
        if token is None or claim.read_text().strip() != token:
            return refuse("was not leased for this process")
        claim.unlink()
    except FileNotFoundError:
        return refuse("was not leased for this process")
    with open(run.path / "lock", "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pass  # held by the client that leased the run: expected
        else:
            return refuse("has no client (its lock is free)")
    with open(run.path / "exec.lock", "a") as running:
        try:
            fcntl.flock(running, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return refuse("is already running")
        if (run.path / "stopped.json").exists():
            return refuse("was stopped")
        return _start(run, max_leases)


def _mark_stopped(run: Run) -> None:
    run.write_json("stopped.json", {"run_id": run.run_id, "ts": time.time()})


def _say(text: str) -> None:
    """Best-effort: a closed log cannot keep a stop from being recorded or carried out. A write
    can still block on a stalled reader, so the stop path writes only once the stop is done
    (release audits, M61)."""
    try:
        os.write(2, (text + "\n").encode())
    except OSError:
        pass


def _start(run: Run, max_leases: int) -> int:
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
        token = uuid.uuid4().hex
        (run.path / LEASE_CLAIM).write_text(token + "\n")
        try:
            status, ran_out, started = _lease(plan, run, token)
        finally:
            (run.path / LEASE_CLAIM).unlink(missing_ok=True)
        if started and not ran_out and not run.done():
            # Stopped by hand, a crash or a shutdown: resumed on purpose, never by boot recovery.
            _mark_stopped(run)
        healthy, detail = guards.production_health()
        print(("production ok: " if healthy else "PRODUCTION NOT HEALTHY: ") + detail, flush=True)
        if not healthy:
            return 1
        if run.done():
            return grade(run) or status
        if not ran_out:
            print(f"run {run.run_id}'s lease ended before its runtime (exit {status}); continue with: "
                  f"nous-eval resume {run.run_id}", file=sys.stderr)
            return 1
    print(f"run {run.run_id} is incomplete after {max_leases} leases; continue with: nous-eval resume {run.run_id}",
          file=sys.stderr)
    return 1


def build_items(plan: dict) -> dict[str, list[dict]]:
    return {spec["name"]: REGISTRY[spec["name"]].items(spec["items_tier"], spec["opts"], DATA_DIR)
            for spec in plan["workloads"]}


TIMESPAN_S = {"us": 1e-6, "ms": 1e-3, "s": 1, "min": 60, "h": 3600, "d": 86400, "w": 604800}


def _timespan_s(text: str) -> float:
    """systemd's format_timespan ("1h 3min 21.878s") in seconds; 0 for anything else."""
    text = text.strip()
    parts = re.findall(r"([0-9]+(?:\.[0-9]+)?)(us|ms|min|s|h|d|w)", text)
    if not parts or "".join(number + unit for number, unit in parts) != text.replace(" ", ""):
        return 0.0
    return sum(float(number) * TIMESPAN_S[unit] for number, unit in parts)


def _lease(plan: dict, run: Run, token: str) -> tuple[int, bool, bool]:
    """One lease: its exit status, whether it ran out, and whether systemd-run said it started our
    unit (`Running as unit: llama-yield-gpu.service`). It ran out only if llama-yield's
    `systemd-run --wait` reports "Finished with result: timeout" after a "Service runtime" of at
    least the lease's: a stop by hand ends "success", or "timeout" too when the stop itself times
    out (TimeoutStopSec), well before the runtime. The child cannot tell these apart: its clock
    guesses misread a stop near the deadline (release audits; council S-06, F-14). Every line is
    passed through, best-effort, after it was read.

    A stop of this process (`systemctl --user stop`, Ctrl-C) marks the run stopped at once and
    durably (a power cut while the lease winds down must not leave it recoverable), then ends the
    lease through llama-yield: SIGTERM to the lease command, which sudo relays to llama-yield. It
    stops its own lease under its lock, never while the start job still waits for production to
    stop (that cancelled the job's restore of production), and restores production. The signal is
    repeated until the command ends, in case it came before sudo could relay it. Once the lease
    has ended, the signal goes to the handler that was in place (release audits, M61)."""
    seen = {"started": False, "timeout": False, "runtime_s": 0.0}
    stopped: dict = {}
    launched: dict = {}

    def relay():
        for line in launched["proc"].stderr:
            text = line.strip()
            seen["started"] = seen["started"] or text.startswith(f"Running as unit: {guards.LEASE_UNIT}")
            seen["timeout"] = seen["timeout"] or text == "Finished with result: timeout"
            if text.startswith("Service runtime:"):
                seen["runtime_s"] = _timespan_s(text.removeprefix("Service runtime:"))
            try:
                sys.stderr.write(line)
                sys.stderr.flush()
            except (OSError, ValueError):
                pass  # a log that went away must not cost the lease its bookkeeping

    def end_lease():
        proc = launched.get("proc")
        if proc is not None and proc.returncode is None:
            try:
                os.kill(proc.pid, signal.SIGTERM)  # not reaped yet, so still this pid
            except ProcessLookupError:
                pass

    def exit_on(signum):
        handler = previous[signum]
        if callable(handler):
            handler(signum, None)
        raise SystemExit(128 + signum)

    def stop(signum, frame):
        # Acts only, and never exits while the lease command may run (or be launching): the
        # wait below returns once it ends. No output here: a write can block on a stalled log.
        proc = launched.get("proc")
        if proc is not None and proc.returncode is not None:
            exit_on(signum)
        if "signum" not in stopped:
            stopped["signum"] = signum
            _mark_stopped(run)
        end_lease()
    previous = {s: signal.signal(s, stop) for s in STOP_SIGNALS}
    try:
        if "signum" in stopped:  # stopped before anything was launched
            exit_on(stopped["signum"])
        proc = launched["proc"] = subprocess.Popen(lease_argv(plan, token), stderr=subprocess.PIPE, text=True,
                                                   errors="replace")
        reader = threading.Thread(target=relay, daemon=True)
        reader.start()
        while True:
            try:
                status = proc.wait(timeout=1)
                break
            except subprocess.TimeoutExpired:
                if "signum" in stopped:
                    end_lease()
        reader.join()
        if "signum" in stopped:
            exit_on(stopped["signum"])
        return status, seen["timeout"] and seen["runtime_s"] >= lease_runtime(plan), seen["started"]
    finally:
        for s, handler in previous.items():
            signal.signal(s, handler)


def execute(run: Run) -> int:
    """One lease of a run (or a --no-lease run, in its client). SIGTERM anywhere in it stops it (_killed)."""
    active: dict = {}
    previous = signal.signal(signal.SIGTERM, lambda signum, frame: _killed(active.get("server"), run))
    try:
        return _execute(run, active)
    finally:
        signal.signal(signal.SIGTERM, previous)


def _execute(run: Run, active: dict) -> int:
    plan = run.plan
    (run.path / "done.json").unlink(missing_ok=True)  # a resumed run is open until it finishes again
    fsync_dir(run.path)  # else a power cut can bring the mark back and keep a cut run from recovery
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
    changed = _check_inputs(run, items) or _check_host(run)
    if changed:
        run.finish("failed", reason=changed)
        print(changed, file=sys.stderr)
        return 1
    rows = run.rows()
    block_failures: list[tuple[str, str]] = []  # (label, what failed)
    for block, label in enumerate(plan["blocks"]):
        if (run.path / "stopped.json").exists():  # its client was stopped; the lease is being ended
            print(f"run {run.run_id} was stopped; not starting block {block}", file=sys.stderr, flush=True)
            return 1
        # A row counts only if the attempt that wrote it passed its end check; any other row (an
        # engine found dead, a lease cut mid-block) is measured again (release audits, M59/M61).
        vouched = _vouched(run, label, block)
        finished = {row_key(r) for r in rows if "error" not in r and r.get("attempt") in vouched}
        todo = [(spec, rep, item) for spec in plan["workloads"] for rep in range(spec["reps"])
                for item in items[spec["name"]]
                if (block, label, spec["name"], item["id"], rep) not in finished]
        if not todo:
            continue
        candidate = plan["candidates"][label]
        changed = _check_manifest(run, label, manifest(candidate))
        if changed:
            block_failures.append((label, f"block {block} ({label}): {changed}"))
            print(block_failures[-1][1], file=sys.stderr, flush=True)
            continue
        if plan["lease"]:
            status, detail = guards.vram_free(guards.Host(plan=plan))  # ledger M29, between blocks too
            if status == "fail":
                block_failures.append((label, f"block {block} ({label}): {detail}"))
                print(block_failures[-1][1], file=sys.stderr, flush=True)
                continue
        server = Server(candidate, run.path, plan["port"])
        print(f"block {block}: {label}, {len(todo)} items", flush=True)
        active["server"] = server
        attempt = uuid.uuid4().hex[:12]
        try:
            _record_attempt(run, label, block, attempt, {"started": time.time()})
            vram_before = _vram()
            load_s = server.start()
            _record_attempt(run, label, block, attempt, {"load_s": load_s, "vram_mib_before": vram_before,
                                                         "vram_mib_loaded": _vram()})
            _run_items(run, plan, block, label, attempt, server.base_url, todo)
            server.check_alive()  # an engine that crashed mid-block fails the block by name
            _record_attempt(run, label, block, attempt, {"vram_mib_end": _vram(), "ended": time.time()})
        except Exception as error:
            block_failures.append((label, f"block {block} ({label}): {error}"))
            print(block_failures[-1][1], file=sys.stderr, flush=True)
        finally:
            server.stop()
            active.pop("server")
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


def _check_host(run: Run) -> str | None:
    """Every block of a run runs on one kernel (ledger M54). A power loss booted a pending
    kernel mid-sweep; per-candidate manifests refused only the arms that spanned it, and the
    rest compared arms from two kernels. Runs from before host.json fall back to the kernel
    their manifests recorded."""
    current = os.uname().release
    recorded = (run.read_json("host.json") or {}).get("kernel")
    if recorded is None:
        manifests = [json.loads(p.read_text()) for p in sorted(run.path.glob("manifest.*.json"))]
        recorded = next((m["kernel"] for m in manifests if "kernel" in m), None)
    if recorded is None:
        run.write_json("host.json", {"kernel": current})
        return None
    return (None if recorded == current else
            f"kernel changed since the run started ({recorded} -> {current}): arms measured on different "
            "kernels cannot be compared; start a new run")


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


def _killed(server: Server | None, run: Run) -> None:
    """SIGTERM (the lease ran out, was stopped, or the host shuts down cleanly): free the GPU, exit.

    Rows are already durable; resume continues the run. Inside a lease nothing is marked: the
    client decides from systemd's result whether the lease ran out (the next lease, or boot
    recovery, continues) or was stopped (it writes stopped.json; council F-05, release audits
    M61). A --no-lease run is its own client and marks itself stopped."""
    if not in_lease():
        _mark_stopped(run)
    if server is not None:
        server.kill()
    _say("terminated: stopped the candidate")
    os._exit(143)


def _run_items(run: Run, plan: dict, block: int, label: str, attempt: str, base_url: str, todo: list) -> None:
    candidate = plan["candidates"][label]
    lock = threading.Lock()

    def one(task):
        spec, rep, item = task
        module = REGISTRY[spec["name"]]
        ctx = Context(base_url, candidate["model"], sampling=plan["sampling"], request=candidate["request"],
                      seed=1000 * rep, data_dir=DATA_DIR, run_dir=run.path)
        row = {"block": block, "candidate": label, "workload": spec["name"], "version": spec["version"],
               "item": item["id"], "rep": rep, "seed": ctx.seed, "attempt": attempt}
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


def _record_attempt(run: Run, label: str, block: int, attempt: str, values: dict) -> None:
    name = f"manifest.{label}.json"
    data = run.read_json(name)
    entry = data["blocks"].get(str(block), {})
    if not all(isinstance(v, dict) for v in entry.values()):
        entry = {}  # the layout before attempts (one record per block); its rows are measured again
    entry.setdefault(attempt, {}).update(values)
    data["blocks"][str(block)] = entry
    run.write_json(name, data)


def _vouched(run: Run, label: str, block: int) -> set[str]:
    """Attempts at this block whose end check passed (`ended` is their last write). A manifest from
    before attempts vouches for nothing: its rows name no attempt."""
    attempts = (run.read_json(f"manifest.{label}.json") or {}).get("blocks", {}).get(str(block), {})
    return {attempt for attempt, values in attempts.items() if isinstance(values, dict) and "ended" in values}


def _vram() -> int | None:
    try:
        return vram_mib()
    except (OSError, RuntimeError):
        return None


def _finish(run: Run, plan: dict, items: dict, block_failures: list[tuple[str, str]]) -> int:
    """done.json; failed_labels names every candidate with a failed block, a missing row, an
    error or a leak, so one arm's crash in a many-arm run leaves the others comparable."""
    rows = run.rows()
    present = {row_key(r) for r in rows}
    expected = {(block, label, spec["name"], item["id"], rep)
                for block, label in enumerate(plan["blocks"]) for spec in plan["workloads"]
                for rep in range(spec["reps"]) for item in items[spec["name"]]}
    errors = [f"{r['workload']}/{r['item']}#{r['rep']} {r['candidate']}: {r['error']}" for r in rows if "error" in r]
    leaks = [f"{r['workload']}/{r['item']}#{r['rep']} {r['candidate']}" for r in rows if r.get("reasoning_leak")]
    gaps = expected - present
    # A row counts only if its attempt passed the end check; a block left with any other row
    # (its check failed, or it was skipped this lease) fails, whatever rows exist (M59/M61).
    for block, label in enumerate(plan["blocks"]):
        vouched = _vouched(run, label, block)
        unvouched = sum(1 for r in rows if r["block"] == block and r["candidate"] == label
                        and r.get("attempt") not in vouched)
        if unvouched and not any(text.startswith(f"block {block} (") for _, text in block_failures):
            block_failures.append((label, f"block {block} ({label}): {unvouched} rows from an attempt "
                                          "whose end check did not pass"))
    failed_labels = sorted({label for label, _ in block_failures} | {key[1] for key in gaps}
                           | {r["candidate"] for r in rows if "error" in r or r.get("reasoning_leak")})
    ok = not failed_labels
    run.finish("ok" if ok else "failed", errors=errors[:50], error_count=len(errors), leaks=leaks[:50],
               missing=len(gaps), block_failures=[text for _, text in block_failures], failed_labels=failed_labels)
    print(f"run {run.run_id}: {'ok' if ok else 'FAILED'}; {len(errors)} errors, {len(leaks)} reasoning leaks, "
          f"{len(gaps)} missing, {len(block_failures)} failed blocks", flush=True)
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
