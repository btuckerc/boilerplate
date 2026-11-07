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

    The interval is the union of a Student-t and a studentized bootstrap (bootstrap-t)
    interval on the paired per-item differences (items are the cluster; reps of one
    item are averaged first), so each decision uses the more cautious bound. Student-t
    alone ignores skew: when the loss is a few items that fail every rep, it passed a
    true 4-point loss about 5% of the time (5.25% analytically for 5 of 258 items lost;
    release audit 2026-11-06). Bootstrap-t alone is erratic on a few items (it called 3
    losses in 7 a fail). Simulated at n=258, 3 reps and a true loss of exactly 4 points
    (2000 trials each), the union passed 2.65% with deterministic losses, 2.1% with
    noisy losses and 2.55% with mixed wins and losses (nominal 2.5%, Monte Carlo error
    ±0.35%); a true tie passed 59% (t alone: 60%). So a t3 pass is a non-inferiority
    claim promote can rely on (council A-02).

    An interval of [0, 0] when every item agrees would certify three matching items
    as non-inferior, and [1, 1] three unanimous wins (11% likely when B is a true 4
    points worse with most items discordant; release audit). So the lower bound is
    never above min(effect, 0) - 3/n, the rule of three: with no loss seen in n items,
    a loss rate up to 3/n is still plausible at 95%. Non-inferiority within 4 points
    therefore needs more than 75 items whatever their direction (council O-15).
    """
    diffs = [b - a for a, b in pairs]
    out = {"n": len(diffs), "dropped": 0}
    if not diffs:
        return {**out, "effect": None, "lo": None, "hi": None, "verdict": "inconclusive"}
    effect = statistics.fmean(diffs)
    lo, hi = bootstrap_t_ci(diffs, seed)
    if len(diffs) >= 2:
        half = _t975(len(diffs) - 1) * statistics.stdev(diffs) / math.sqrt(len(diffs))
        lo, hi = min(lo, effect - half), max(hi, effect + half)
    lo = min(lo, min(effect, 0.0) - 3 / len(diffs))
    verdict = "pass" if lo > margin else "fail" if hi < margin else "inconclusive"
    return {**out, "effect": effect, "lo": lo, "hi": hi, "verdict": verdict}


def bootstrap_t_ci(values: list[float], seed: int = 0, alpha: float = 0.05) -> tuple[float, float]:
    """Studentized bootstrap interval for the mean: resamples whose spread is zero are
    skipped (their t is undefined); a sample with no spread has the point interval."""
    n = len(values)
    if n < 2:
        return (-math.inf, math.inf)
    mean, sd = statistics.fmean(values), statistics.stdev(values)
    if sd == 0:
        return (mean, mean)
    rng = random.Random(seed)
    ts = []
    for _ in range(BOOTSTRAP):
        sample = rng.choices(values, k=n)
        m = sum(sample) / n
        var = (sum(x * x for x in sample) - n * m * m) / (n - 1)
        if var > 1e-15:
            ts.append((m - mean) / math.sqrt(var / n))
    if not ts:
        return (-math.inf, math.inf)
    ts.sort()
    se = sd / math.sqrt(n)
    upper_t = ts[min(len(ts) - 1, int((1 - alpha / 2) * len(ts)))]
    lower_t = ts[int(alpha / 2 * len(ts))]
    return mean - upper_t * se, mean - lower_t * se


def _t975(df: int) -> float:
    """97.5% quantile of Student's t: tabulated for df 1-5, Cornish-Fisher beyond (error < 0.002)."""
    if df <= 5:
        return (12.7062, 4.3027, 3.1824, 2.7764, 2.5706)[df - 1]
    z = 1.959964
    return (z + (z**3 + z) / (4 * df) + (5 * z**5 + 16 * z**3 + 3 * z) / (96 * df**2)
            + (3 * z**7 + 19 * z**5 + 17 * z**3 - 15 * z) / (384 * df**3))


def _exp(x: float) -> float:
    return 0.0 if x == -math.inf else math.inf if x == math.inf else math.exp(x)
