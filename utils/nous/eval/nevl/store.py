"""Run directories: an immutable plan, durable rows, and an explicit completion record.

<root>/runs/<run_id>/
    plan.json            written once at creation (ledger M10)
    manifest.<label>.json  identity of each candidate, plus per-block load times
    rows.jsonl           one fsynced line per finished item (ledger M5)
    replies.jsonl        every reply behind each row, keyed like it (ledger M31)
    graded.jsonl         rows after grading (NEEDS_GRADE workloads), rewritten atomically
    done.json            {"run_id", "status", ...}: the only completion signal (ledger M4)
    compare.<a>.<b>.{json,md}
<root>/index.sqlite      one row per run, for `nous-eval ls`
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path

DEFAULT_ROOT = Path("/srv/models/.eval")


def root() -> Path:
    return Path(os.environ.get("NOUS_EVAL_ROOT", DEFAULT_ROOT))


def row_key(row: dict) -> tuple:
    return (row["block"], row["candidate"], row["workload"], row["item"], row["rep"])


def write_durable(path: Path, text: str) -> None:
    """Replace path with text so that after a power loss it holds the old or the new text,
    and the new text once this returns: file and directory are fsynced (release audit)."""
    tmp = path.with_name(f".{path.name}.tmp")
    with tmp.open("w") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    fsync_dir(path.parent)


def fsync_dir(path: Path) -> None:
    directory = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


class Run:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.run_id = self.path.name

    @classmethod
    def create(cls, plan: dict, base: Path | None = None) -> "Run":
        run = cls((base or root()) / "runs" / plan["run_id"])
        run.path.mkdir(parents=True, exist_ok=False)
        run.write_json("plan.json", plan)
        # the run's own entry in runs/ (and runs/ in the root when new): a canary record names
        # this run next and must find it after a power loss (release audit)
        fsync_dir(run.path.parent)
        fsync_dir(run.path.parent.parent)
        run.index()
        return run

    @classmethod
    def open(cls, run_id: str, base: Path | None = None) -> "Run":
        path = (base or root()) / "runs" / run_id
        if not (path / "plan.json").is_file():
            raise FileNotFoundError(f"no run {run_id} under {path.parent}")
        return cls(path)

    @property
    def plan(self) -> dict:
        return self.read_json("plan.json")

    def read_json(self, name: str) -> dict | None:
        path = self.path / name
        return json.loads(path.read_text()) if path.exists() else None

    def write_json(self, name: str, data: dict) -> None:
        write_durable(self.path / name, json.dumps(data, indent=2, sort_keys=True) + "\n")

    def append(self, row: dict, name: str = "rows.jsonl") -> None:
        path = self.path / name
        created = not path.exists()
        with path.open("a+b") as f:
            if f.seek(0, os.SEEK_END):
                f.seek(-1, os.SEEK_END)
                if f.read(1) != b"\n":  # isolate a torn line left by a killed lease
                    f.write(b"\n")
            f.write(json.dumps(row, sort_keys=True).encode() + b"\n")
            f.flush()
            os.fsync(f.fileno())
        if created:  # the file's entry too: recovery selects a run by its rows.jsonl (release audit, M61)
            fsync_dir(self.path)

    def rows(self) -> list[dict]:
        """Latest row per key; a later row (a retry after an error) replaces an earlier one."""
        return _latest(_read_jsonl(self.path / "rows.jsonl"))

    def graded_rows(self) -> list[dict]:
        """rows() with graded versions substituted where they grade that very row (same ts): a row
        measured again after its attempt failed its end check keeps the same key (ledger M61)."""
        graded = {row_key(r): r for r in _read_jsonl(self.path / "graded.jsonl")}
        return [g if (g := graded.get(row_key(r))) and g.get("ts") == r.get("ts") else r for r in self.rows()]

    def evidence(self) -> str:
        """sha256 of everything a compare reads that a resume can change: rows, grades and
        done.json. A saved compare report counts only while this still matches (release audit:
        a resume that measured rows again left the old report standing)."""
        digest = hashlib.sha256()
        for name in ("rows.jsonl", "graded.jsonl", "done.json"):
            path = self.path / name
            data = path.read_bytes() if path.exists() else b""
            digest.update(f"{name}:{len(data)}\n".encode())
            digest.update(data)
        return digest.hexdigest()

    def write_graded(self, rows: list[dict]) -> None:
        tmp = self.path / ".graded.jsonl.tmp"
        with tmp.open("w") as f:
            for row in rows:
                f.write(json.dumps(row, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path / "graded.jsonl")

    def finish(self, status: str, **details) -> None:
        self.write_json("done.json", {"run_id": self.run_id, "status": status, "ts": time.time(), **details})
        self.index()

    def done(self) -> dict | None:
        """done.json, only if it belongs to this run."""
        done = self.read_json("done.json")
        return done if done and done.get("run_id") == self.run_id else None

    def index(self) -> None:
        plan = self.plan
        done = self.done() or {}
        with sqlite3.connect(self.path.parent.parent / "index.sqlite") as db:
            db.execute("CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, tier TEXT, created REAL,"
                       " candidates TEXT, status TEXT, path TEXT)")
            db.execute("INSERT OR REPLACE INTO runs VALUES (?, ?, ?, ?, ?, ?)",
                       (self.run_id, plan["tier"], plan["created"], ",".join(plan["candidates"]),
                        done.get("status", "open"), str(self.path)))


def list_runs(base: Path | None = None) -> list[dict]:
    path = (base or root()) / "index.sqlite"
    if not path.exists():
        return []
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        return [dict(r) for r in db.execute("SELECT * FROM runs ORDER BY created")]


INTERRUPT_WINDOW_S = 24 * 3600


def boot_time(stat: Path = Path("/proc/stat")) -> float:
    return float(next(line.split()[1] for line in stat.read_text().splitlines() if line.startswith("btime ")))


def interrupted(boot: float, base: Path | None = None) -> list[str]:
    """Runs a reboot cut short: started (rows.jsonl), never finished (no done.json), last row
    written in the day before boot. No process survives a reboot, so none of them is live, and
    runs started since boot are left alone (ledger M51). A run that got SIGTERM (stopped by
    hand, or a clean shutdown) has stopped.json and stays stopped (council F-05). Oldest
    first: run ids sort by start time."""
    found = []
    for rows in sorted(((base or root()) / "runs").glob("*/rows.jsonl")):
        ended = (rows.parent / "done.json").exists() or (rows.parent / "stopped.json").exists()
        if not ended and boot - INTERRUPT_WINDOW_S < rows.stat().st_mtime < boot:
            found.append(rows.parent.name)
    return found


def _read_jsonl(path: Path) -> list[dict]:
    """Parse rows; a torn line from a killed lease is skipped (its item reruns on resume)."""
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _latest(rows: list[dict]) -> list[dict]:
    latest = {}
    for row in rows:
        latest[row_key(row)] = row
    return list(latest.values())
