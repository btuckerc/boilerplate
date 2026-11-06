"""Long-context recall and prefill/decode speed at fixed prompt depths.

Eight key/value needles are spread evenly through wikitext filler sized to the
target depth in real tokens (bisected against the server's /tokenize), and the
model must return all eight as JSON. Each prompt starts with a line unique to
the item, rep and seed, so no engine can serve any of it from a prefix cache:
prefill is measured cold everywhere.
"""
from __future__ import annotations

import json
import random
import re
import statistics
import urllib.error
import urllib.request
from pathlib import Path

NAME = "longctx"
VERSION = "5"
METRICS = {"recall": "rate", "answered": "rate", "prefill_tps": "higher", "decode_tps": "higher"}
MUST_PASS = ("prefill_tps", "decode_tps")  # recall and answered may only fail: four depths cannot certify a pass
REPORTED = ()
NEEDS_GRADE = False
INPUTS = ("longctx/filler.txt",)

DEPTHS = {"t1": [32768], "t2": [32768, 65536, 131072, 160000]}
NEEDLES = 8
QUESTION_ROOM = 400  # tokens left for the needles and the question
CONTEXT = 163840  # production's ctx-size: prompt plus answer must fit
MAX_TOKENS = 8192  # answer budget, less at depths that leave less room
WIKITEXT = Path("/home/tux/.local/state/gsq-eval/wikitext-2-raw")


def fetch(data_dir: Path) -> None:
    target = Path(data_dir) / "longctx"
    target.mkdir(parents=True, exist_ok=True)
    parts = [(WIKITEXT / name).read_text() for name in ("wiki.train.raw", "wiki.valid.raw", "wiki.test.raw")]
    (target / "filler.txt").write_text("\n".join(parts))


def items(tier: str, opts: dict, data_dir: Path) -> list[dict]:
    if not (Path(data_dir) / "longctx" / "filler.txt").exists():
        raise FileNotFoundError(Path(data_dir) / "longctx" / "filler.txt")
    depths = opts.get("depths", DEPTHS.get(tier, DEPTHS["t1"]))
    return [{"id": f"depth-{depth}", "depth": int(depth)} for depth in depths]


def run_item(ctx, item: dict) -> dict:
    filler = (ctx.data_dir / "longctx" / "filler.txt").read_text()
    header = f"Archive session {item['id']}-{ctx.seed}. Read the archive; a question follows it.\n"
    body = _fit(ctx, filler, item["depth"] - QUESTION_ROOM)
    needles = _needles(random.Random(f"{item['id']}-{ctx.seed}"))
    prompt = (header + _plant(body, needles)
              + "\nReturn a JSON object containing exactly these keys and their values: " + ", ".join(needles) + ".")
    budget = min(MAX_TOKENS, CONTEXT - item["depth"] - 256)  # 256: chat template and slack
    reply = ctx.chat({"messages": [{"role": "user", "content": prompt}], "max_tokens": budget,
                      "seed": ctx.seed, "cache_prompt": False})
    answered = reply.finish_reason != "length"
    answer = _last_json_object(reply.content)
    timings = reply.timings
    return {
        # Out of budget is not a recall failure; it counts against `answered` instead and
        # keeps the depth's speed (council O-09, F-12).
        "recall": sum(str(answer.get(key)) == value for key, value in needles.items()) / NEEDLES if answered else None,
        "answered": float(answered),
        "max_tokens": budget,
        "prompt_n": timings.get("prompt_n", 0),
        "prefill_tps": timings.get("prompt_per_second", 0),
        "decode_tps": timings.get("predicted_per_second", 0),
        "wall": reply.wall,
        "finish_reason": reply.finish_reason,
    }


def summarize(rows: list[dict]) -> dict:
    good = [r for r in rows if "error" not in r]
    by_depth = {}
    for row in good:
        by_depth.setdefault(row["item"], []).append(row)
    return {
        "n": len(good),
        "errors": len(rows) - len(good),
        "by_depth": {depth: {key: _mean(r.get(key) for r in group)
                             for key in ("recall", "answered", "prompt_n", "prefill_tps", "decode_tps")}
                     for depth, group in sorted(by_depth.items())},
    }


def _mean(values) -> float | None:
    """Mean of the values that exist; recall is None where the model ran out of budget."""
    present = [v for v in values if v is not None]
    return statistics.mean(present) if present else None


def _fit(ctx, text: str, tokens: int) -> str:
    """The longest prefix of `text` (to 2000 characters) that fits in `tokens`."""
    lo, hi = 0, min(len(text), tokens * 8)
    if _count_tokens(ctx, text[:hi]) <= tokens:
        raise ValueError(f"filler is shorter than {tokens} tokens")
    while hi - lo > 2000:
        mid = (lo + hi) // 2
        if _count_tokens(ctx, text[:mid]) <= tokens:
            lo = mid
        else:
            hi = mid
    return text[:lo]


def _count_tokens(ctx, text: str) -> int:
    """Tokens in `text` from the server: llama.cpp takes `content`, vLLM `prompt`.

    A body the server does not understand can come back as an empty token list
    (the llama.cpp router answers `prompt` with []), never a valid count for
    real text, so an empty count moves on to the next form."""
    for body in ({"model": ctx.model, "content": text},
                 {"model": ctx.model, "prompt": text, "add_special_tokens": False}):
        request = urllib.request.Request(ctx.base_url + "/tokenize", json.dumps(body).encode(),
                                         {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                reply = json.load(response)
        except urllib.error.HTTPError:
            continue
        count = reply["count"] if "count" in reply else len(reply.get("tokens") or [])
        if count:
            return int(count)
    raise RuntimeError(f"{ctx.base_url}/tokenize gave no token count in llama.cpp or vLLM form")


def _needles(rng: random.Random) -> dict[str, str]:
    return {f"key_{i}": f"value_{rng.randrange(100000, 999999)}" for i in range(NEEDLES)}


def _plant(text: str, needles: dict[str, str]) -> str:
    """Insert one record per needle at evenly spaced line boundaries."""
    lines = [line for line in text.splitlines() if line.strip()]
    records = [f"Record {n}: lookup {key} has value {value}." for n, (key, value) in enumerate(needles.items())]
    out = []
    for n, record in enumerate(records):
        start = len(lines) * n // len(records)
        end = len(lines) * (n + 1) // len(records)
        out.extend(lines[start:(start + end) // 2])
        out.append(record)
        out.extend(lines[(start + end) // 2:end])
    return "\n".join(out)


def _last_json_object(text: str | None) -> dict:
    """The last flat JSON object in the reply, fenced or bare; {} if none parses."""
    for match in reversed(list(re.finditer(r"\{[^{}]*\}", text or ""))):
        try:
            return json.loads(match.group(0))
        except ValueError:
            continue
    return {}
