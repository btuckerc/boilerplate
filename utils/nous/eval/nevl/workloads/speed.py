from __future__ import annotations

import statistics
from pathlib import Path

EDIT_SOURCES = Path(__file__).resolve().parents[1] / "data" / "speed" / "edit"

NAME = "speed"
VERSION = "2"
METRICS = {"decode_tps": "higher", "ttft_s": "lower"}
MUST_PASS = ("decode_tps",)
REPORTED = ("ttft_s",)  # short prompts, warm cache on later reps: engine cache policy, not speed
NEEDS_GRADE = False

PROSE = [
    "Write a Python function that parses an ISO-8601 duration like P3DT4H5M6S into seconds. Include edge cases.",
    "Explain, with a worked example, how a B-tree insertion splits nodes.",
    "Implement an LRU cache in TypeScript with O(1) get/put and explain the design briefly.",
    "A train leaves at 09:40 going 84 km/h; another leaves the same station at 10:05 going 104 km/h on the same track. When and where does the second catch the first? Show work.",
    "Refactor this into idiomatic Rust and explain ownership choices: fn f(v: &Vec<String>) -> Vec<String> { let mut o = Vec::new(); for s in v.iter() { if s.len() > 3 { o.push(s.clone().to_uppercase()); } } o }",
    "Write a bash script that rotates log files in a directory, keeping the newest 5 compressed copies. Explain each step.",
]
CODE = [
    "Implement a Python function to merge overlapping intervals.",
    "Implement an LRU cache with O(1) get and put operations.",
    "Write a parser for nested parentheses and return the maximum nesting depth.",
    "Implement a rate limiter using a sliding window.",
    "Write a function that finds the shortest path in a weighted grid using Dijkstra's algorithm.",
    "Implement a thread-safe bounded queue with blocking put/get.",
    "Write a JSON-lines reader that reports malformed line numbers and continues.",
    "Implement a trie with insert, contains, and prefix search operations.",
]
EDIT = [
    ("conc.py", "Rename every occurrence of the variable `sessions` to `n_sessions`."),
    ("vision.py", "Add a one-line docstring to every function that lacks one."),
    ("lcb_grade.py", "Replace every double-quoted string literal with single quotes where that needs no escaping."),
]

def items(tier, opts, data_dir):
    families = [("prose", PROSE), ("code", CODE), ("edit", EDIT)]
    selected = [("prose", PROSE[:2]), ("code", CODE[:2]), ("edit", EDIT[:2])] if tier == "t1" else families
    out = []
    for family, prompts in selected:
        for i, value in enumerate(prompts):
            if family == "edit":
                name, change = value
                source = (EDIT_SOURCES / name).read_text()
                prompt = f"{change}\nReturn the complete modified file in one ```python block and nothing else.\n\n```python\n{source}```"
            else:
                name, prompt = f"{family}-{i}", value
            out.append({"id": f"{family}-{i}", "family": family, "name": name, "prompt": prompt, "seed": 300 + i, "max_tokens": opts.get("max_tokens", 12000 if family == "edit" else 1536)})
    return out

def run_item(ctx, item):
    sampling = dict(ctx.sampling)
    if item["family"] == "edit":
        sampling["reasoning_effort"] = "low"  # edits measure copy-heavy decode (ngram, drafter), not reasoning
    reply = ctx.chat({"messages": [{"role": "user", "content": item["prompt"]}], "max_tokens": item["max_tokens"],
                      "seed": ctx.seed + item["seed"], **sampling})
    timings = reply.timings
    server = timings.get("server", {})  # llama.cpp only
    return {
        "decode_tps": timings.get("predicted_per_second", 0),
        "ttft_s": reply.ttft,
        "predicted_n": timings.get("predicted_n", 0),
        "prompt_tps": timings.get("prompt_per_second", 0),
        # vLLM reports no per-request draft counts; None, not a 0.0 that reads as measured (council F-07)
        "draft_acceptance": server.get("draft_n_accepted", 0) / server["draft_n"] if server.get("draft_n") else None,
        "wall": reply.wall,
        "finish_reason": reply.finish_reason,
    }


def summarize(rows):
    good = [r for r in rows if "error" not in r]
    by_family = {}
    for row in good:
        by_family.setdefault(row["item"].split("-")[0], []).append(row)
    return {"n": len(good), "errors": len(rows) - len(good),
            "by_family": {family: {"decode_tps": statistics.mean(r["decode_tps"] for r in group),
                                   "ttft_s": statistics.mean(r["ttft_s"] or 0 for r in group)}
                          for family, group in sorted(by_family.items())}}
