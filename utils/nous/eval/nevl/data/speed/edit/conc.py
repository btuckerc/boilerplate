#!/usr/bin/env python3
"""Concurrent agent-like load against a bench.py server on :18737.

Usage (inside bench.py --run): python3 conc.py LABEL --conc C [--sessions 4] [--turns 3] [--prefix 20000]
Fixed work, varying client concurrency C:
  agents: SESSIONS conversations, each with a distinct ~PREFIX-token document and TURNS sequential turns
          (turn k re-sends the whole conversation plus a new question; prefix reuse is exercised).
  code:   8 HumanEval+ prompts.
Both phases run with C client threads. Appends one JSON row to conc.jsonl.
"""
import argparse, gzip, json, statistics as st, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
URL = "http://127.0.0.1:18737/v1/chat/completions"
SAMPLING = {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "min_p": 0.0, "reasoning_effort": "medium"}
QUESTIONS = ["Summarize the three most important events in the document above in five bullet points.",
             "Write a Python function that extracts every four-digit year mentioned in the document and returns a sorted unique list. Include tests.",
             "Which person is mentioned most often in the document? Explain how you counted."]

def post(body):
    req = urllib.request.Request(URL, json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": "Bearer gsq-bench-private"})
    t = time.monotonic()
    with urllib.request.urlopen(req, timeout=3600) as r:
        d = json.load(r)
    return d, time.monotonic() - t

def rec(d, wall, kind):
    t = d["timings"]
    return {"kind": kind, "wall": wall, "prompt_n": t["prompt_n"], "prompt_s": t["prompt_ms"] / 1000,
            "pred_n": t["predicted_n"], "pred_s": t["predicted_ms"] / 1000, "tps": t["predicted_per_second"],
            "cache_n": t.get("cache_n", 0), "acc": t.get("draft_n_accepted", 0) / max(1, t.get("draft_n", 0)),
            "queue_s": max(0.0, wall - t["prompt_ms"] / 1000 - t["predicted_ms"] / 1000)}

def session(i, a):
    text = (HERE / "wikitext-2-raw/wiki.test.raw").read_text() + (HERE / "wikitext-2-raw/wiki.valid.raw").read_text()
    n = int(a.prefix * 3.6); off = ((i + a.doc_shift) * n) % max(1, len(text) - n)
    msgs = [{"role": "system", "content": f"You are coding agent #{i}. Answer concisely."},
            {"role": "user", "content": text[off:off + n]}]
    out = []
    for k in range(a.turns):
        msgs.append({"role": "user", "content": QUESTIONS[k % len(QUESTIONS)]})
        try:
            d, w = post({"messages": msgs, "max_tokens": a.max_tokens, "seed": 10 * i + k, **SAMPLING})
        except Exception as e:  # e.g. unified KV pool exhausted; record and end this session
            body = e.read().decode()[:300] if hasattr(e, "read") else ""
            out.append({"kind": f"agent-t{k}", "error": f"{e!r} {body}"})
            break
        out.append(rec(d, w, f"agent-t{k}"))
        msgs.append({"role": "assistant", "content": d["choices"][0]["message"].get("content") or ""})
    return out

def code(p, a):
    d, w = post({"messages": [{"role": "user", "content": "Complete the following Python function. Return the complete function in a single ```python code block.\n\n```python\n" + p + "```"}],
                 "max_tokens": 3072, "seed": 5, **SAMPLING})
    return [rec(d, w, "code")]

def phase(fn, items, a):
    t = time.monotonic()
    with ThreadPoolExecutor(a.conc) as ex:
        rows = [r for rs in ex.map(lambda x: fn(x, a), items) for r in rs]
    span = time.monotonic() - t
    errors = [r["error"] for r in rows if "error" in r]
    rows = [r for r in rows if "error" not in r]
    toks = sum(r["pred_n"] for r in rows)
    if not rows: return {"makespan": round(span, 1), "errors": errors}
    return {"makespan": round(span, 1), "agg_decode_tps": round(toks / span, 1), "tokens": toks,
            "median_stream_tps": round(st.median(r["tps"] for r in rows), 1),
            "p50_wall": round(st.median(r["wall"] for r in rows), 1),
            "max_wall": round(max(r["wall"] for r in rows), 1),
            "mean_queue_s": round(st.mean(r["queue_s"] for r in rows), 1),
            "prefill_tok": sum(r["prompt_n"] for r in rows), "cached_tok": sum(r["cache_n"] for r in rows),
            "mean_acc": round(st.mean(r["acc"] for r in rows), 3), "errors": errors, "rows": rows}

ap = argparse.ArgumentParser()
ap.add_argument("label"); ap.add_argument("--conc", type=int, default=1)
ap.add_argument("--sessions", type=int, default=4); ap.add_argument("--turns", type=int, default=3)
ap.add_argument("--prefix", type=int, default=20000); ap.add_argument("--max-tokens", type=int, default=1024)
ap.add_argument("--no-code", action="store_true")
ap.add_argument("--doc-shift", type=int, default=0, help="use documents shifted by this many sessions (avoid cache hits from an earlier run)")
a = ap.parse_args()
post({"messages": [{"role": "user", "content": "Say OK."}], "max_tokens": 16, **SAMPLING})
row = {"label": a.label, "conc": a.conc, "sessions": a.sessions, "turns": a.turns, "prefix": a.prefix}
row["agents"] = phase(session, range(a.sessions), a)
if not a.no_code:
    he = [json.loads(l)["prompt"] for l in gzip.open(HERE / "HumanEvalPlus.jsonl.gz")][100:108]
    row["code"] = phase(code, he, a)
summary = {k: ({kk: vv for kk, vv in v.items() if kk != "rows"} if isinstance(v, dict) else v) for k, v in row.items()}
print(json.dumps(summary), flush=True)
with open(HERE / "conc.jsonl", "a") as f: f.write(json.dumps(row) + "\n")
