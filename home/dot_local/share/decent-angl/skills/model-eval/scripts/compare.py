#!/usr/bin/env python3
"""Compare candidate models against the current director on price and shape.

Usage: compare [SELECTOR ...] [--baseline SELECTOR] [--days N]

Defaults to every model assigned to a role in OMP config. Blended $/M weights each
catalog price by the real token mix of recent OMP sessions (input, cache read,
cache write, output). The "x base" column approximates relative subscription
burn only within one provider pool; Anthropic and Codex pools are separate.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

FALLBACK_MIX = {"input": 0.01, "cacheRead": 0.90, "cacheWrite": 0.05, "output": 0.04}


def omp_json(*args):
    return json.loads(subprocess.run(["omp", *args, "--json"], check=True,
                                     capture_output=True, text=True).stdout)


def walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def token_mix(days):
    totals = dict.fromkeys(FALLBACK_MIX, 0)
    cutoff = time.time() - days * 86400
    root = Path.home() / ".omp/agent/sessions"
    for path in root.rglob("*.jsonl"):
        if path.stat().st_mtime < cutoff:
            continue
        with path.open(errors="ignore") as handle:
            for line in handle:
                if '"usage"' not in line or '"assistant"' not in line:
                    continue
                try:
                    usage = json.loads(line)["message"]["usage"]
                except (ValueError, KeyError, TypeError):
                    continue
                for key in totals:
                    totals[key] += usage.get(key) or 0
    total = sum(totals.values())
    if total == 0:
        return FALLBACK_MIX, "fallback mix"
    return {k: v / total for k, v in totals.items()}, f"{days}-day session mix, {total / 1e6:.1f}M tokens"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("selectors", nargs="*")
    parser.add_argument("--baseline")
    parser.add_argument("--days", type=int, default=14)
    args = parser.parse_args()

    roles = omp_json("config", "get", "modelRoles")["value"]
    strip = lambda s: s.rsplit(":", 1)[0] if s.count(":") else s
    role_models = sorted({strip(v) for v in roles.values() if "/" in v and not v.startswith("web/")})
    selectors = args.selectors or role_models
    baseline = args.baseline or strip(roles["default"])

    catalog = {n["selector"]: n for n in walk(omp_json("models")) if "selector" in n and "provider" in n}
    mix, source = token_mix(args.days)

    def blended(model):
        cost = model.get("cost") or {}
        return sum(mix[k] * (cost.get(k) or 0) for k in mix)

    base = catalog.get(baseline)
    base_cost = blended(base) if base else 0
    print(f"mix ({source}): " + " ".join(f"{k}={v:.1%}" for k, v in mix.items()))
    print(f"baseline: {baseline}")
    header = f"{'selector':42} {'ctx':>6} {'out':>5} {'in':>6} {'out$':>6} {'cRd':>5} {'cWr':>5} {'blend':>6} {'x base':>6}  efforts"
    print(header)
    missing = []
    for selector in selectors:
        model = catalog.get(selector)
        if not model:
            missing.append(selector)
            continue
        cost = model.get("cost") or {}
        b = blended(model)
        ratio = f"{b / base_cost:.2f}" if base_cost else "-"
        print(f"{selector:42} {model.get('contextWindow', 0) // 1000:>5}K {model.get('maxTokens', 0) // 1000:>4}K "
              f"{cost.get('input', 0):>6.2f} {cost.get('output', 0):>6.2f} {cost.get('cacheRead', 0):>5.2f} "
              f"{cost.get('cacheWrite', 0):>5.2f} {b:>6.3f} {ratio:>6}  {','.join(model.get('thinking') or []) or '-'}")
    if missing:
        print("not discovered (check auth, enabledModels, OMP pin): " + ", ".join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
