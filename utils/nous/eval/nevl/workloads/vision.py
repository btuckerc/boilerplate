"""Reading images: synthetic screenshots with one checkable answer each.

A terminal traceback, a bar chart, a table, a dense text page, rotated text and
a two-image comparison, all drawn from a seeded RNG so every candidate sees the
same pixels. T2 adds the traceback again behind ~120K tokens of text, which
checks that images still read correctly deep in the context.
"""
from __future__ import annotations

import base64
import io
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

NAME = "vision"
VERSION = "3"
METRICS = {"pass": "rate"}
MUST_PASS = ()  # seven items cannot certify non-inferiority; a significant loss still fails
REPORTED = ()
NEEDS_GRADE = False

SEED = 20261002
DEEP_CHARS = 120000 * 4  # ~120K tokens of filler before the deep item


def items(tier: str, opts: dict, data_dir: Path) -> list[dict]:
    rng = random.Random(opts.get("seed", SEED))
    result = [_terminal(rng), _chart(rng), _table(rng), _dense(rng), _rotated(rng), _comparison()]
    if tier == "t1":
        return result[:3]
    filler = (Path(data_dir) / "longctx" / "filler.txt").read_text(encoding="utf-8")
    prefix = filler[:DEEP_CHARS] + "\n\n(End of background text. Ignore it.)\n\n"
    return result + [{**result[0], "id": "deep-terminal", "prefix": prefix}]


def run_item(ctx, item: dict) -> dict:
    parts = [{"type": "text", "text": item["prefix"]}] if item.get("prefix") else []
    parts += [{"type": "image_url", "image_url": {"url": url}} for url in item["images"]]
    parts.append({"type": "text", "text": item["question"]})
    reply = ctx.chat({"messages": [{"role": "user", "content": parts}], "max_tokens": 8192,  # production's n-predict
                      "seed": ctx.seed})
    answer = (reply.content or "").lower()
    return {"pass": float(all(need.lower() in answer for need in item["need"])),
            "answer": (reply.content or "").strip()[-500:],
            "prompt_tokens": reply.usage.get("prompt_tokens"), "wall": reply.wall}


def summarize(rows: list[dict]) -> dict:
    good = [r for r in rows if "error" not in r]
    return {"n": len(good), "errors": len(rows) - len(good),
            "pass_rate": sum(r["pass"] for r in good) / len(good) if good else 0,
            "failed": sorted({r["item"] for r in good if not r["pass"]})}


def _item(name: str, images: list[Image.Image], question: str, need: list[str]) -> dict:
    return {"id": name, "images": [_data_url(image) for image in images], "question": question, "need": need}


def _terminal(rng: random.Random) -> dict:
    line = rng.randint(100, 999)
    module = rng.choice(["codec", "store", "relay"])
    function = rng.choice(["parse_header", "load_index", "flush_queue"])
    image = Image.new("RGB", (900, 260), (30, 30, 30))
    draw = ImageDraw.Draw(image)
    lines = ["$ python3 -m app.run --config prod.toml", "Traceback (most recent call last):",
             f'  File "app/{module}.py", line {line}, in {function}', '    raise ValueError("bad magic")',
             "ValueError: bad magic"]
    for n, text in enumerate(lines):
        draw.text((16, 16 + n * 36), text, font=_font(18, mono=True), fill=(220, 220, 220))
    return _item("terminal", [image], "Which file, line number and function raised the error? Answer file:line:function.",
                 [f"{module}.py", str(line), function])


def _chart(rng: random.Random) -> dict:
    regions = ["north", "south", "east", "west"]
    values = rng.sample(range(12, 95), 4)
    image = Image.new("RGB", (700, 420), "white")
    draw = ImageDraw.Draw(image)
    for n, (region, value) in enumerate(zip(regions, values)):
        x = 80 + n * 150
        draw.rectangle([x, 380 - value * 3.5, x + 90, 380], fill=(60, 110, 200))
        draw.text((x + 20, 385), region, font=_font(), fill="black")
        draw.text((x + 28, 352 - value * 3.5), str(value), font=_font(), fill="black")
    tallest = regions[values.index(max(values))]
    return _item("chart", [image], "Which region has the tallest bar and what value is printed? Answer region=value.",
                 [tallest, str(max(values))])


def _table(rng: random.Random) -> dict:
    rows = [(f"SKU-{rng.randint(1000, 9999)}", rng.randint(1, 40), f"{rng.randint(1, 99)}.{rng.randint(10, 99)}")
            for _ in range(5)]
    image = Image.new("RGB", (620, 260), "white")
    draw = ImageDraw.Draw(image)
    for column, header in enumerate(("item", "qty", "price")):
        draw.text((30 + column * 200, 15), header, font=_font(), fill="black")
    for n, row in enumerate(rows):
        for column, value in enumerate(row):
            draw.text((30 + column * 200, 55 + n * 38), str(value), font=_font(18, mono=True), fill="black")
    sku, qty, price = rows[rng.randrange(len(rows))]
    return _item("table", [image], f"What are qty and price for {sku}? Answer qty,price.", [str(qty), price])


def _dense(rng: random.Random) -> dict:
    codes = [rng.randint(10000, 99999) for _ in range(35)]
    image = Image.new("RGB", (1200, 800), "white")
    draw = ImageDraw.Draw(image)
    for n, code in enumerate(codes):
        draw.text((12, 8 + n * 21), f"Record {n:02}: code {code}", font=_font(12, mono=True), fill="black")
    chosen = rng.randrange(len(codes))
    return _item("dense", [image], f"What code appears in Record {chosen:02}?", [str(codes[chosen])])


def _rotated(rng: random.Random) -> dict:
    key = str(rng.randint(1000, 9999))
    layer = Image.new("RGBA", (500, 70), (255, 255, 255, 0))
    ImageDraw.Draw(layer).text((4, 4), f"ROTATED KEY {key}", font=_font(), fill="black")
    layer = layer.rotate(90, expand=True)
    image = Image.new("RGB", (700, 400), "white")
    image.paste(layer, (300, 20), layer)
    return _item("rotated", [image], "Read the rotated key.", [key])


def _comparison() -> dict:
    before = Image.new("RGB", (360, 220), "white")
    after = Image.new("RGB", (360, 220), "white")
    ImageDraw.Draw(before).rectangle((40, 60, 120, 180), fill="blue")
    ImageDraw.Draw(before).rectangle((190, 90, 270, 180), fill="red")
    ImageDraw.Draw(after).rectangle((40, 100, 120, 180), fill="blue")
    ImageDraw.Draw(after).rectangle((190, 45, 270, 180), fill="red")
    return _item("compare", [before, after], "Which color's bar became taller in the second image?", ["red"])


def _data_url(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _font(size: int = 18, mono: bool = False):
    names = (["DejaVuSansMono.ttf"] if mono else []) + ["DejaVuSans.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{name}", size)
        except OSError:
            pass
    return ImageFont.load_default()
