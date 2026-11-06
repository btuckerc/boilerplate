#!/usr/bin/env python3
"""Image-input check against a bench server on :18737 (run via bench.py --run).

Usage: vision.py LABEL [--long TOKENS]
Renders three synthetic screenshots with random facts, asks one question each and
checks the answer by substring. --long puts a wikitext prefix before the image to
test image recall deep in context. Appends one row to vision.jsonl.
"""
import argparse, base64, io, json, random, time, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
URL = "http://127.0.0.1:18737/v1/chat/completions"
MONO = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 18)
SANS = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)


def png(img):
    buf = io.BytesIO(); img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def terminal(r):
    line, fn, mod = r.randint(100, 999), r.choice(["parse_header", "load_index", "flush_queue"]), r.choice(["codec", "store", "relay"])
    img = Image.new("RGB", (900, 260), (30, 30, 30)); d = ImageDraw.Draw(img)
    text = ["$ python3 -m app.run --config prod.toml", "Traceback (most recent call last):",
            f'  File "app/{mod}.py", line {line}, in {fn}', "    raise ValueError(\"bad magic\")",
            "ValueError: bad magic", "$ "]
    for i, t in enumerate(text): d.text((16, 16 + i * 36), t, font=MONO, fill=(220, 220, 220))
    return img, f"In the terminal screenshot, which file, line number and function raised the error? Answer as file:line:function.", [f"{mod}.py", str(line), fn]


def chart(r):
    names = ["north", "south", "east", "west"]; vals = r.sample(range(12, 95), 4)
    img = Image.new("RGB", (700, 420), "white"); d = ImageDraw.Draw(img)
    for i, (n, v) in enumerate(zip(names, vals)):
        x = 80 + i * 150; d.rectangle([x, 380 - v * 3.5, x + 90, 380], fill=(60, 110, 200))
        d.text((x + 20, 385), n, font=SANS, fill="black"); d.text((x + 28, 352 - v * 3.5), str(v), font=SANS, fill="black")
    top = names[vals.index(max(vals))]
    return img, "Which region has the tallest bar in the chart, and what value is printed on it? Answer as region=value.", [top, str(max(vals))]


def table(r):
    rows = [(f"SKU-{r.randint(1000, 9999)}", r.randint(1, 40), f"{r.randint(1, 99)}.{r.randint(10, 99)}") for _ in range(5)]
    img = Image.new("RGB", (620, 260), "white"); d = ImageDraw.Draw(img)
    for j, h in enumerate(["item", "qty", "price"]): d.text((30 + j * 200, 15), h, font=SANS, fill="black")
    for i, row in enumerate(rows):
        for j, c in enumerate(row): d.text((30 + j * 200, 55 + i * 38), str(c), font=MONO, fill="black")
    k = r.randrange(5)
    return img, f"In the table, what are the qty and price of {rows[k][0]}? Answer as qty,price.", [str(rows[k][1]), rows[k][2]]


def ask(content, max_tokens=2048):
    body = {"messages": [{"role": "user", "content": content}], "max_tokens": max_tokens, "temperature": 0}
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json", "Authorization": "Bearer gsq-bench-private"})
    t = time.time(); out = json.load(urllib.request.urlopen(req, timeout=1800))
    return out["choices"][0]["message"].get("content") or "", out.get("usage", {}), time.time() - t


ap = argparse.ArgumentParser(); ap.add_argument("label"); ap.add_argument("--long", type=int, default=0); a = ap.parse_args()
r = random.Random(20261002)
prefix = ""
if a.long:
    wiki = (HERE / "wikitext-2-raw/wiki.test.raw").read_text() + (HERE / "wikitext-2-raw/wiki.valid.raw").read_text()
    prefix = wiki[: a.long * 4] + "\n\n(End of background text. Ignore it.)\n\n"
results = []
for make in (terminal, chart, table):
    img, q, need = make(r)
    content = ([{"type": "text", "text": prefix}] if prefix else []) + [{"type": "image_url", "image_url": {"url": png(img)}}, {"type": "text", "text": q}]
    try:
        ans, usage, wall = ask(content)
        ok = all(n.lower() in ans.lower() for n in need)
        results.append({"case": make.__name__, "ok": ok, "need": need, "answer": ans.strip()[-200:], "prompt_tokens": usage.get("prompt_tokens"), "wall": round(wall, 1)})
    except Exception as e:
        results.append({"case": make.__name__, "ok": False, "error": str(e)[:300]})
row = {"label": a.label, "long": a.long, "passed": sum(x["ok"] for x in results), "of": len(results), "results": results}
with open(HERE / "vision.jsonl", "a") as f: f.write(json.dumps(row) + "\n")
print(json.dumps(row))
