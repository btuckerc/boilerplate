"""Several agents at once: makespan of four multi-turn sessions over a shared GPU.

Four sessions, each a ~20K-token document followed by three short questions,
run with 1, 2 or 4 clients in flight. One client is the serial baseline; more
clients show what the engine gains (parallel slots, batching) or loses (cache
eviction, re-prefill) under contention.
"""
from __future__ import annotations

import math
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

NAME = "concurrency"
VERSION = "4"
METRICS = {"makespan_s": "lower"}
MUST_PASS = ()  # three client counts cannot certify a pass; a significant loss still fails
REPORTED = ()
NEEDS_GRADE = False

QUESTIONS = [
    "Summarize three important facts in the document above.",
    "Write a Python function that extracts all four-digit years from the document.",
    "Which person appears most often? Explain briefly.",
]
SENTENCE = "The archive records historical events, named people, dates, places, and explanations. "


def items(tier: str, opts: dict, data_dir) -> list[dict]:
    clients = opts.get("concurrency", [1, 2, 4] if tier == "t2" else [1])
    return [{"id": f"clients-{c}", "clients": int(c), "sessions": int(opts.get("sessions", 4)),
             "doc_tokens": int(opts.get("doc_tokens", 20000))} for c in clients]


def run_item(ctx, item: dict) -> dict:
    chars = item["doc_tokens"] * 4  # ~4 characters per token of English
    document = (SENTENCE * (chars // len(SENTENCE) + 1))[:chars]

    def session(n: int) -> list[dict]:
        messages = [{"role": "system", "content": f"You are research agent {n}; answer concisely."},
                    {"role": "user", "content": f"Document {n}:\n{document}"}]
        requests = []
        for turn, question in enumerate(QUESTIONS):
            messages.append({"role": "user", "content": question})
            try:
                reply = ctx.chat({"messages": messages, "max_tokens": 128, "seed": ctx.seed + n * 10 + turn})
            except Exception as error:  # one failed request ends this session; the item fails below
                requests.append({"error": str(error)[:300]})
                break
            messages.append({"role": "assistant", "content": reply.content})
            requests.append({"wall": reply.wall, "ttft_s": reply.ttft,
                             "prompt_n": reply.timings.get("prompt_n", 0),
                             "decode_tps": reply.timings.get("predicted_per_second", 0)})
        return requests

    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=item["clients"]) as pool:
        requests = [r for session_requests in pool.map(session, range(item["sessions"])) for r in session_requests]
    makespan = time.monotonic() - start
    failed = [r["error"] for r in requests if "error" in r]
    if failed:
        # A request that fails under load is an engine failure, not a slower score; failed
        # requests also return fast and would shorten the makespan (council A-08).
        raise RuntimeError(f"{len(failed)} of {len(requests)} requests failed with {item['clients']} clients: {failed[0]}")
    return {
        "makespan_s": makespan,
        "prompt_tokens_processed": sum(r["prompt_n"] for r in requests),
        "requests": requests,
    }


def summarize(rows: list[dict]) -> dict:
    good = [r for r in rows if "error" not in r]
    by_clients = {}
    for row in good:
        by_clients.setdefault(row["item"], []).append(row)
    return {
        "n": len(good),
        "errors": len(rows) - len(good),
        "by_clients": {item: {"makespan_s": statistics.mean(r["makespan_s"] for r in group),
                              "p95_ttft_s": _p95([q["ttft_s"] for r in group for q in r["requests"]
                                                  if q.get("ttft_s") is not None]),
                              "prompt_tokens_processed": statistics.mean(r["prompt_tokens_processed"] for r in group)}
                       for item, group in sorted(by_clients.items())},
    }


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    return values[math.ceil(0.95 * len(values)) - 1]
