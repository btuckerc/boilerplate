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


class Run:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.run_id = self.path.name

    @classmethod
    def create(cls, plan: dict, base: Path | None = None) -> "Run":
        run = cls((base or root()) / "runs" / plan["run_id"])
        run.path.mkdir(parents=True, exist_ok=False)
        run.write_json("plan.json", plan)
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
        tmp = self.path / f".{name}.tmp"
        with tmp.open("w") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path / name)

    def append(self, row: dict, name: str = "rows.jsonl") -> None:
        with (self.path / name).open("a+b") as f:
            if f.seek(0, os.SEEK_END):
                f.seek(-1, os.SEEK_END)
                if f.read(1) != b"\n":  # isolate a torn line left by a killed lease
                    f.write(b"\n")
            f.write(json.dumps(row, sort_keys=True).encode() + b"\n")
            f.flush()
            os.fsync(f.fileno())

    def rows(self) -> list[dict]:
        """Latest row per key; a later row (a retry after an error) replaces an earlier one."""
        return _latest(_read_jsonl(self.path / "rows.jsonl"))

    def graded_rows(self) -> list[dict]:
        """rows() with graded versions substituted where they exist."""
        graded = {row_key(r): r for r in _read_jsonl(self.path / "graded.jsonl")}
        return [graded.get(row_key(r), r) for r in self.rows()]

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
