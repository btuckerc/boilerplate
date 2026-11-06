"""Prompt-cache reuse across an agent session, with another client cutting in.

An eight-turn session grows on a ~90K-character system prompt, one tool output
per turn. Before turn 4 an unrelated client sends its own long request, which
an engine with one slot or a small cache evicts the session for. The metric is
how many prompt tokens the engine had to prefill over the whole session (what
it could not serve from cache) and the session's wall time. Each item is a
session over a different stretch of the filler, so items are distinct prompts.
"""
from __future__ import annotations

import statistics

NAME = "replay"
VERSION = "3"
METRICS = {"wall": "lower", "reprefill_tokens": "lower"}
MUST_PASS = ()  # three sessions cannot certify a pass; a significant loss still fails
# Re-prefilled tokens are the mechanism, wall time the outcome: vLLM re-prefilled 22% more
# (block-granular cache) and still finished sessions 2.5x sooner, so tokens only inform.
REPORTED = ("reprefill_tokens",)
NEEDS_GRADE = False
INPUTS = ("longctx/filler.txt",)

TURNS = 8
INTERRUPT_BEFORE = 4
CHUNK = 12000  # characters of tool output per turn
SYSTEM_CHARS = 90000
SESSIONS = {"t1": 1, "t2": 3}


def items(tier: str, opts: dict, data_dir) -> list[dict]:
    if not (data_dir / "longctx" / "filler.txt").exists():
        raise FileNotFoundError(data_dir / "longctx" / "filler.txt")
    return [{"id": f"session-{n}", "offset": n * (SYSTEM_CHARS + TURNS * CHUNK)}
            for n in range(SESSIONS.get(tier, 1))]


def run_item(ctx, item: dict) -> dict:
    text = (ctx.data_dir / "longctx" / "filler.txt").read_text()
    text = text[item["offset"]:] + text[:item["offset"]]
    system = "You are a coding agent. Use this reference material carefully.\n" + text[:SYSTEM_CHARS]
    messages = [{"role": "system", "content": system}]
    turns = []
    for turn in range(TURNS):
        if turn == INTERRUPT_BEFORE:
            other = ctx.chat({"messages": [
                {"role": "system", "content": "Unrelated archival assistant; do not use the coding reference."},
                {"role": "user", "content": text[-CHUNK:] + " Summarize in one sentence."}],
                "max_tokens": 128, "seed": ctx.seed + 99})
            turns.append({"turn": "other", **_measure(other)})
        start = SYSTEM_CHARS + turn * CHUNK
        messages.append({"role": "user", "content": f"Tool output {turn}:\n{text[start:start + CHUNK]}\nSummarize this output briefly."})
        reply = ctx.chat({"messages": messages, "max_tokens": 256, "seed": ctx.seed + 11 + turn})
        messages.append({"role": "assistant", "content": reply.content})
        turns.append({"turn": turn, **_measure(reply)})
    session = [t for t in turns if t["turn"] != "other"]
    return {
        "turns": turns,
        "reprefill_tokens": sum(t["prompt_n"] for t in session),
        "wall": sum(t["wall"] for t in turns),
    }


def summarize(rows: list[dict]) -> dict:
    good = [r for r in rows if "error" not in r]
    return {
        "n": len(good),
        "errors": len(rows) - len(good),
        "reprefill_tokens": statistics.mean(r["reprefill_tokens"] for r in good) if good else 0,
        "wall": statistics.mean(r["wall"] for r in good) if good else 0,
    }


def _measure(reply) -> dict:
    timings = reply.timings
    return {
        "prompt_n": timings.get("prompt_n", 0),
        "prefill_s": timings.get("prompt_ms", 0) / 1000,
        "decode_tps": timings.get("predicted_per_second", 0),
        "wall": reply.wall,
    }
