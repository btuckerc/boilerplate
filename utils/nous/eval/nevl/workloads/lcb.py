from __future__ import annotations

import base64
import hashlib
import json
import math
import pickle
import re
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from nevl.sandbox import run_python

NAME = "lcb"
VERSION = "2"
METRICS = {"pass": "rate"}
MUST_PASS = ("pass",)
REPORTED = ()
NEEDS_GRADE = True
INPUTS = ("lcb/tests.jsonl",)  # grading only; the questions are in the items
SYS = "You are an expert Python programmer. Solve the problem and return only the final program in a single ```python code block."
HARNESS = '''\nimport sys, json\nfrom typing import *\nfrom collections import *\nfrom functools import *\nfrom itertools import *\nfrom heapq import *\nfrom bisect import *\nimport math, string, re\nsys.setrecursionlimit(1 << 20)\n{code}\nargs = [json.loads(l) for l in sys.stdin.read().splitlines() if l.strip()]\nprint(json.dumps(getattr(Solution(), {fn!r})(*args)))\n'''


def _decode(value):
    if not value:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            raw = zlib.decompress(base64.b64decode(value))
            return json.loads(pickle.loads(raw))
    return []


def _load(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# fetch() splits the pool: questions.jsonl is small and is what a lease loads;
# tests.jsonl (~1 GB of hidden tests) is read only by grade(), outside the lease.
QUESTION_FIELDS = ("question_id", "question_content", "starter_code", "difficulty")


def fetch(data_dir: Path) -> None:
    out = Path(data_dir) / "lcb"
    out.mkdir(parents=True, exist_ok=True)
    source = Path("/home/tux/.local/state/gsq-eval/lcb")
    questions, tests = [], []
    for name in ("test5.jsonl", "test6.jsonl"):
        for row in _load(source / name):
            cases = _decode(row.get("public_test_cases")) + _decode(row.get("private_test_cases"))
            if not cases and row.get("tests_blob"):
                cases = _decode(row["tests_blob"])
            questions.append({k: row.get(k) for k in QUESTION_FIELDS})
            tests.append({"question_id": row["question_id"], "starter_code": row.get("starter_code"),
                          "metadata": row.get("metadata"), "tests": cases})
    _write_jsonl(out / "questions.jsonl", questions)
    _write_jsonl(out / "tests.jsonl", tests)
    (out / "pool.jsonl").unlink(missing_ok=True)  # pre-split layout


def _write_jsonl(path: Path, rows) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(path)


def items(tier: str, opts: dict, data_dir: Path) -> list[dict]:
    """t1: the first 10 easy problems, a smoke test that coding output works at all.
    Other tiers: every medium and hard problem (258), the accuracy test."""
    rows = sorted(_load(Path(data_dir) / "lcb" / "questions.jsonl"), key=lambda r: str(r["question_id"]))
    if tier == "t1":
        chosen = [r for r in rows if (r.get("difficulty") or "").lower() == "easy"][:10]
    else:
        chosen = [r for r in rows if (r.get("difficulty") or "").lower() in ("medium", "hard")]
    max_tokens = opts.get("max_tokens", 8192 if tier == "t1" else 16384)
    return [{"id": r["question_id"], "problem": r, "max_tokens": max_tokens} for r in chosen]


def run_item(ctx, item: dict) -> dict:
    p = item["problem"]
    if p.get("starter_code"):
        user = (f"### Question:\n{p['question_content']}\n\n### Format: Use the following starter code, completing the method.\n"
                f"```python\n{p['starter_code']}\n```\n\n### Answer: (use the provided format with backticks)")
    else:
        user = (f"### Question:\n{p['question_content']}\n\n### Format: Read the inputs from stdin, solve the problem and write the "
                "answer to stdout (do not directly test on the sample inputs).\n```python\n# YOUR CODE HERE\n```\n\n### Answer: (use the provided format with backticks)")
    seed = int.from_bytes(hashlib.sha256(str(p["question_id"]).encode()).digest()[:4], "big")
    rep = ctx.chat({"messages": [{"role": "system", "content": SYS}, {"role": "user", "content": user}],
                    "max_tokens": item["max_tokens"], "seed": (ctx.seed + seed) % (2**31)})
    return {"content": rep.content, "reasoning_length": len(rep.reasoning or ""), "finish_reason": rep.finish_reason,
            "completion_tokens": rep.usage.get("completion_tokens"), "predicted_per_second": rep.timings.get("predicted_per_second"),
            "wall": rep.wall, "truncated": rep.finish_reason == "length", "difficulty": p.get("difficulty")}


def _extract(text):
    blocks = re.findall(r"```(?:python|py)?\n(.*?)```", text or "", re.S)
    return blocks[-1] if blocks else None


def _same_stdout(got, want):
    g, w = got.split(), want.split()
    if len(g) != len(w):
        return False
    for a, b in zip(g, w):
        if a == b:
            continue
        try:
            if abs(float(a) - float(b)) > 1e-6 * max(1, abs(float(b))):
                return False
        except ValueError:
            return False
    return True


def _grade_one(pair):
    p, gen = pair
    code = _extract(gen.get("content"))
    if not code:
        return {"pass": False, "why": "no code", "no_code": True}
    fn = json.loads(p.get("metadata") or "{}").get("func_name")
    src = HARNESS.format(code=code, fn=fn) if p.get("starter_code") else code
    for i, test in enumerate(p.get("tests", [])):
        rc, stdout, stderr, timed_out = run_python(src, test["input"], 10, mem_mb=4096)
        if timed_out:
            return {"pass": False, "why": f"timeout test {i}", "no_code": False}
        if rc:
            return {"pass": False, "why": f"error test {i}: {stderr[-200:]}", "no_code": False}
        if p.get("starter_code"):
            try:
                ok = json.loads(stdout.strip().splitlines()[-1]) == json.loads(test["output"])
            except Exception:
                ok = False
        else:
            ok = _same_stdout(stdout, test["output"])
        if not ok:
            return {"pass": False, "why": f"wrong test {i}", "no_code": False}
    return {"pass": True, "why": "", "no_code": False}


def grade(rows, data_dir):
    wanted = {row["item"] for row in rows}
    problems = {}
    with (Path(data_dir) / "lcb" / "tests.jsonl").open(encoding="utf-8") as f:
        for line in f:
            problem = json.loads(line)
            if problem["question_id"] in wanted:
                problems[problem["question_id"]] = problem
    def do(row):
        result = _grade_one((problems[row["item"]], row))
        return {**row, **result}
    with ThreadPoolExecutor(max_workers=12) as pool:
        return list(pool.map(do, rows))


def summarize(rows: list[dict]) -> dict:
    good = [r for r in rows if "error" not in r]
    by = {}
    # Difficulty is copied onto graded rows when available; tolerate core rows that omit it.
    for r in good:
        d = r.get("difficulty", "unknown")
        bucket = by.setdefault(d, {"n": 0, "pass_rate": 0.0})
        bucket["n"] += 1
        bucket["pass_rate"] += bool(r.get("pass"))
    for bucket in by.values():
        bucket["pass_rate"] /= bucket["n"]
    n = len(good)
    return {"n": n, "errors": len(rows) - n, "pass_rate": sum(bool(r.get("pass")) for r in good) / n if n else 0,
            "truncated_rate": sum(bool(r.get("truncated")) for r in good) / n if n else 0,
            "no_code_rate": sum(bool(r.get("no_code")) for r in good) / n if n else 0,
            "mean_completion_tokens": sum(r.get("completion_tokens") or 0 for r in good) / n if n else 0,
            # an arm whose server capped replies below the request shows it here (council O-12)
            "max_completion_tokens": max((r.get("completion_tokens") or 0 for r in good), default=0),
            "by_difficulty": by}
