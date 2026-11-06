"""Paired statistics over items. Items are the resampling unit (cluster bootstrap):
reps and blocks of one item are averaged first, so repeated runs of one prompt
never count as independent evidence (ledger M11)."""
from __future__ import annotations

import math
import random
import statistics

BOOTSTRAP = 4000


def bootstrap_mean_ci(values: list[float], seed: int = 0, alpha: float = 0.05) -> tuple[float, float]:
    if len(values) < 2:
        return (-math.inf, math.inf)
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(rng.choices(values, k=n)) / n for _ in range(BOOTSTRAP))
    return means[int(alpha / 2 * BOOTSTRAP)], means[int((1 - alpha / 2) * BOOTSTRAP) - 1]


def ratio(pairs: list[tuple[float, float]], higher_is_better: bool, tolerance: float, seed: int = 0) -> dict:
    """Geometric-mean ratio B/A, oriented so > 1 means B is better.

    pass: the CI lower bound is above 1 - tolerance; fail: the CI upper bound is below it.
    """
    usable = [(a, b) for a, b in pairs if a > 0 and b > 0]
    logs = [math.log(b / a) if higher_is_better else math.log(a / b) for a, b in usable]
    out = {"n": len(logs), "dropped": len(pairs) - len(logs)}
    if not logs:
        return {**out, "effect": None, "lo": None, "hi": None, "verdict": "inconclusive"}
    lo, hi = bootstrap_mean_ci(logs, seed)
    effect, lo, hi = math.exp(statistics.fmean(logs)), _exp(lo), _exp(hi)
    floor = 1 - tolerance
    verdict = "pass" if lo >= floor else "fail" if hi < floor else "inconclusive"
    return {**out, "effect": effect, "lo": lo, "hi": hi, "verdict": verdict}


def rate_difference(pairs: list[tuple[float, float]], margin: float, seed: int = 0) -> dict:
    """Mean difference B - A of per-item rates, with a non-inferiority verdict.

    margin is negative (e.g. -0.04). pass: CI lower bound > margin; fail: CI upper
    bound < margin; otherwise inconclusive (too few items to tell).

    The bootstrap interval collapses to [0, 0] when every item agrees, which would
    certify three matching items as non-inferior. So the lower bound is never above
    the rule of three: with no disagreement in n items, a disagreement rate up to
    3/n is still plausible at 95%. Non-inferiority within 4 points therefore needs
    more than 75 items. The upper bound stays the bootstrap's, so a clear loss on a
    small item set still fails (council O-15).

    A rate "pass" is approximate, not certified non-inferiority: the percentile
    bootstrap under-covers near the margin (about 5% one-sided error instead of 2.5%
    for a true 4-point loss at n=258). No promotion depends on it: promote treats a
    t3 pass like inconclusive, and t2/canary gate only on ratios. If a rate ever
    must pass for promotion, switch to a coverage-valid paired method (Newcombe or
    Tango) first (council S-03 tiebreak).
    """
    diffs = [b - a for a, b in pairs]
    out = {"n": len(diffs), "dropped": 0}
    if not diffs:
        return {**out, "effect": None, "lo": None, "hi": None, "verdict": "inconclusive"}
    effect = statistics.fmean(diffs)
    lo, hi = bootstrap_mean_ci(diffs, seed)
    lo = min(lo, effect - 3 / len(diffs))
    verdict = "pass" if lo > margin else "fail" if hi < margin else "inconclusive"
    return {**out, "effect": effect, "lo": lo, "hi": hi, "verdict": verdict}


def _exp(x: float) -> float:
    return 0.0 if x == -math.inf else math.inf if x == math.inf else math.exp(x)
