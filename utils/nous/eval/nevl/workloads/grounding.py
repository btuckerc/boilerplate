"""Computer-use grounding: click the described element on a real screenshot.

100 ScreenSpot-v2 records, stratified over platform (desktop, mobile, web) and
element type (text, icon). The model is told the image size and asked for a
click point. Qwen-family vision models often answer in 0-1000 normalised
coordinates instead of pixels, so both readings are scored and reported;
neither is gated.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import random
import re
import urllib.request
import zipfile
from pathlib import Path

NAME = "grounding"
VERSION = "3"
METRICS = {"hit_pixel": "rate", "hit_norm1000": "rate"}
MUST_PASS = ()
REPORTED = ("hit_pixel", "hit_norm1000")
NEEDS_GRADE = False
INPUTS = ("grounding",)  # the screenshots the items point at

SOURCE = "https://huggingface.co/datasets/OS-Copilot/ScreenSpot-v2/resolve/main/"
FILES = {"desktop": "screenspot_desktop_v2.json", "mobile": "screenspot_mobile_v2.json", "web": "screenspot_web_v2.json"}
SAMPLE = 100
SEED = 20261002


def fetch(data_dir: Path) -> None:
    out = Path(data_dir) / "grounding"
    out.mkdir(parents=True, exist_ok=True)
    strata = {}
    for platform, name in FILES.items():
        for row in _download_json(SOURCE + name):
            row["platform"] = platform
            strata.setdefault((platform, str(row.get("data_type", "unknown")).lower()), []).append(row)
    rng = random.Random(SEED)
    keys = sorted(strata)
    per_stratum, extra = divmod(SAMPLE, len(keys))
    selected = []
    for n, key in enumerate(keys):
        rng.shuffle(strata[key])
        selected.extend(strata[key][:per_stratum + (n < extra)])
    if len(selected) < SAMPLE:
        raise RuntimeError(f"ScreenSpot-v2 has only {len(selected)} stratified records")
    archive = out / "screenspotv2_image.zip"  # 1.3 GB; deleted once the sample is extracted
    if not archive.exists():
        _download_file(SOURCE + "screenspotv2_image.zip?download=true", archive)
    with zipfile.ZipFile(archive) as zf:
        members = {Path(n).name: n for n in zf.namelist()}
        for n, row in enumerate(selected):
            member = members.get(Path(row["img_filename"]).name)
            if member is None:
                raise RuntimeError(f"image missing from the ScreenSpot-v2 archive: {row['img_filename']}")
            row["_image_file"] = f"{n:03d}{Path(member).suffix.lower()}"
            (out / row["_image_file"]).write_bytes(zf.read(member))
    archive.unlink()
    (out / "items.json").write_text(json.dumps(selected, ensure_ascii=False), encoding="utf-8")


def items(tier: str, opts: dict, data_dir: Path) -> list[dict]:
    folder = Path(data_dir) / "grounding"
    rows = json.loads((folder / "items.json").read_text(encoding="utf-8"))
    return [{"id": f"{n:03d}", "row": row, "image_path": str(folder / row["_image_file"])} for n, row in enumerate(rows)]


def run_item(ctx, item: dict) -> dict:
    from PIL import Image  # lazy: only vision-capable hosts need Pillow

    path = Path(item["image_path"])
    with Image.open(path) as image:
        width, height = image.size
    url = f"data:{mimetypes.guess_type(path.name)[0] or 'image/png'};base64,{base64.b64encode(path.read_bytes()).decode()}"
    row = item["row"]
    question = (f"{row['instruction']}\nThe image is {width}x{height} pixels. "
                'Return the click point in pixel coordinates as JSON {"x": int, "y": int}.')
    reply = ctx.chat({"messages": [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": url}}, {"type": "text", "text": question}]}],
        "max_tokens": 8192, "seed": ctx.seed})  # production's n-predict: a long think is not a miss
    point = _click_point(reply.content)
    left, top, w, h = map(float, row["bbox"])  # ScreenSpot-v2 bbox is x, y, width, height in pixels
    hit_pixel = point is not None and left <= point[0] <= left + w and top <= point[1] <= top + h
    hit_norm = (point is not None and left * 1000 / width <= point[0] <= (left + w) * 1000 / width
                and top * 1000 / height <= point[1] <= (top + h) * 1000 / height)
    return {"hit_pixel": float(hit_pixel), "hit_norm1000": float(hit_norm), "point": point,
            "platform": row["platform"], "type": row.get("data_type"), "wall": reply.wall,
            "finish_reason": reply.finish_reason}


def summarize(rows: list[dict]) -> dict:
    good = [r for r in rows if "error" not in r]
    groups = {"all": good}
    for row in good:
        groups.setdefault(f"{row['platform']}/{row['type']}", []).append(row)
    return {
        "n": len(good),
        "errors": len(rows) - len(good),
        "hit_rates": {name: {"n": len(group),
                             "hit_pixel": sum(r["hit_pixel"] for r in group) / len(group) if group else 0,
                             "hit_norm1000": sum(r["hit_norm1000"] for r in group) / len(group) if group else 0}
                      for name, group in groups.items()},
    }


def _click_point(text: str | None) -> tuple[int, int] | None:
    match = re.search(r'\{[^{}]*"x"\s*:\s*(-?\d+)[^{}]*"y"\s*:\s*(-?\d+)[^{}]*\}', text or "")
    return (int(match.group(1)), int(match.group(2))) if match else None


def _download_json(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "nous-eval/1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def _download_file(url: str, path: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "nous-eval/1"})
    with urllib.request.urlopen(request, timeout=1800) as response, path.open("wb") as out:
        while chunk := response.read(1 << 20):
            out.write(chunk)
