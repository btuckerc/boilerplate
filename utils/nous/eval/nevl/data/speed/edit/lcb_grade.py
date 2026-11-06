#!/usr/bin/env python3
"""Grade lcb_gen.py output against all public+private tests. Usage: lcb_grade.py OUT.jsonl"""
import json, re, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

probs = {p["question_id"]: p for p in map(json.loads, open(Path(__file__).with_name("lcb") / "subset60.jsonl"))}
gens = {g["question_id"]: g for g in map(json.loads, open(sys.argv[1]))}

HARNESS = '''
import sys, json
from typing import *
from collections import *
from functools import *
from itertools import *
from heapq import *
from bisect import *
import math, string, re
sys.setrecursionlimit(1 << 20)
{code}
args = [json.loads(l) for l in sys.stdin.read().splitlines() if l.strip()]
print(json.dumps(getattr(Solution(), {fn!r})(*args)))
'''

def extract(text):
    blocks = re.findall(r"```(?:python|py)?\n(.*?)```", text or "", re.S)
    return blocks[-1] if blocks else None

def same_stdout(got, want):
    g, w = got.split(), want.split()
    if len(g) != len(w): return False
    for a, b in zip(g, w):
        if a == b: continue
        try:
            if abs(float(a) - float(b)) > 1e-6 * max(1, abs(float(b))): return False
        except ValueError: return False
    return True

def grade(qid):
    p, g = probs[qid], gens.get(qid)
    code = extract(g.get("content")) if g else None
    if not code: return qid, False, "no code"
    fn = json.loads(p["metadata"] or "{}").get("func_name")
    src = HARNESS.format(code=code, fn=fn) if p["starter_code"] else code
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f: f.write(src)
    for i, t in enumerate(p["tests"]):
        try:
            r = subprocess.run([sys.executable, f.name], input=t["input"], capture_output=True, text=True, timeout=10)
        except subprocess.TimeoutExpired:
            return qid, False, f"timeout test {i}"
        if r.returncode: return qid, False, f"error test {i}: {r.stderr[-200:]}"
        if p["starter_code"]:
            try: ok = json.loads(r.stdout.strip().splitlines()[-1]) == json.loads(t["output"])
            except Exception: ok = False
        else:
            ok = same_stdout(r.stdout, t["output"])
        if not ok: return qid, False, f"wrong test {i}"
    return qid, True, ""

with ThreadPoolExecutor(12) as ex:
    res = list(ex.map(grade, probs))
by = {}
for qid, ok, why in res:
    d = probs[qid]["difficulty"]; by.setdefault(d, [0, 0]); by[d][0] += ok; by[d][1] += 1
fin = sum(1 for g in gens.values() if g.get("finish") == "length")
tok = sum(g.get("usage", {}).get("completion_tokens", 0) for g in gens.values())
summary = {"file": sys.argv[1], "pass": sum(ok for _, ok, _ in res), "n": len(res), "by_difficulty": by,
           "truncated": fin, "errors": sum(1 for g in gens.values() if "error" in g), "completion_tokens": tok,
           "seconds": round(sum(g.get("seconds", 0) for g in gens.values()))}
Path(sys.argv[1]).with_suffix(".graded.json").write_text(json.dumps({"summary": summary, "results": res}, indent=1))
print(json.dumps(summary))
