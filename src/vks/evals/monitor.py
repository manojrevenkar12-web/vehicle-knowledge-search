"""Monitoring without labels, from the production log alone: zero-result rate, the share of queries naming something
the catalogue cannot link, the share of answers with a value the catalogue doesn't have, and how far the mix of
queries has moved from the first weeks (population stability index). A small labelled sample each week checks what
the monitors cannot see."""

from __future__ import annotations

import math
import re
from collections import Counter

from vks.search.catalog import Graph, norm, validate


def unlinked_name(text: str, g: Graph) -> bool:
    """A make followed by a word the catalogue cannot link: a model it doesn't know yet."""
    t = norm(text)
    linked = {kind for kind, _, _ in g.link(text)}
    for mk in g.make_names():
        m = re.search(rf"(?<![a-z]){re.escape(norm(mk.split('-')[0]))}\s+([a-z0-9.]+)", t)
        if (
            m
            and "model" not in linked
            and "generation" not in linked
            and not re.match(r"(unter|bis|max|ab|from|under|below|up)$", m.group(1))
        ):
            return True
    return False


def topic(filters: dict) -> str:
    for key in ("model", "drive", "body", "fuel", "equipment", "consumption_to", "power_from_kw", "seats_from"):
        if key in filters:
            return key
    return "other"


def psi(base: Counter, now: Counter) -> float:
    keys = set(base) | set(now)
    nb, nn = sum(base.values()) or 1, sum(now.values()) or 1
    out = 0.0
    for k in keys:
        b, n = max(base[k] / nb, 1e-4), max(now[k] / nn, 1e-4)
        out += (n - b) * math.log(n / b)
    return out


def weekly(log: list[dict], g_by_week, baseline_weeks: int) -> list[dict]:
    weeks = sorted({e["week"] for e in log})
    base = Counter(topic(e["filters"]) for e in log if e["week"] <= baseline_weeks)
    out = []
    for w in weeks:
        es = [e for e in log if e["week"] == w]
        g = g_by_week(w)
        n = len(es)
        out.append(
            {
                "week": w,
                "zero_results": round(sum(e["results"] == 0 for e in es) / n, 4),
                "unknown_entities": round(sum(unlinked_name(e["text"], g) for e in es) / n, 4),
                "hallucinations": round(sum(bool(e["problems"]) or bool(validate(e["filters"], g)) for e in es) / n, 4),
                "psi": round(psi(base, Counter(topic(e["filters"]) for e in es)), 4),
            }
        )
    return out
