"""Statistics for telling a real gain from noise: per-call means over repeats, a bootstrap that resamples calls (the
repeats of one call stay together), paired differences, and the number of calls a comparison needs."""

from __future__ import annotations

from statistics import NormalDist

import numpy as np


def by_call(runs: list[dict], key) -> dict[str, float]:
    acc: dict[str, list[float]] = {}
    for r in runs:
        acc.setdefault(r["id"], []).append(float(key(r)))
    return {k: sum(v) / len(v) for k, v in acc.items()}


def interval(values: list[float], n: int, alpha: float, seed: int) -> tuple[float, float, float]:
    x = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    means = x[rng.integers(0, len(x), size=(n, len(x)))].mean(axis=1)
    return float(x.mean()), float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))


def paired(a: list[dict], b: list[dict], key, n: int, alpha: float, seed: int) -> tuple[float, float, float]:
    """b minus a in the per-call mean of `key`, paired by call."""
    ta, tb = by_call(a, key), by_call(b, key)
    ids = sorted(set(ta) & set(tb))
    return interval([tb[i] - ta[i] for i in ids], n, alpha, seed)


def diffs(a: list[dict], b: list[dict], key) -> list[float]:
    ta, tb = by_call(a, key), by_call(b, key)
    return [tb[i] - ta[i] for i in sorted(set(ta) & set(tb))]


def calls_needed(d: list[float], effect: float, alpha: float, power: float) -> int:
    """Calls a paired comparison needs to detect `effect` with `power`, from observed per-call differences."""
    sd = float(np.std(d, ddof=1)) if len(d) > 1 else 0.0
    z = NormalDist().inv_cdf(1 - alpha / 2) + NormalDist().inv_cdf(power)
    return int(np.ceil((z * sd / effect) ** 2)) if effect > 0 else 0


def pct(values: list[float], q: float) -> float:
    return float(np.percentile(values, q)) if values else 0.0
