"""The gate a change to prompts, retrieval, the model or the agent goes through. Blocked when, against the current
system on the development queries (paired by query), the lower bound of the difference in exact answers is below
-[eval].gate_max_drop; when it fails a production case the current system passes; or when it is over the latency or
cost budget and worse than the current system there."""

from __future__ import annotations

from vks.evals.stats import paired, pct
from vks.settings import Settings


def budget(runs: list[dict]) -> dict:
    return {
        "p95_ms": round(pct([r["latency_ms"] for r in runs], 95)),
        "cost_eur": round(sum(r["cost_eur"] for r in runs) / len(runs), 5),
    }


def decide(base: list[dict], cand: list[dict], base_reg: dict, cand_reg: dict, s: Settings) -> dict:
    e = s.eval
    d = paired(base, cand, lambda r: r["exact"], e.bootstrap, e.alpha, s.run.seed)
    a, b = budget(base), budget(cand)
    broken = sorted(k for k, ok in base_reg.items() if ok and not cand_reg.get(k, False))
    reasons = []
    if d[1] < -e.gate_max_drop:
        reasons.append(f"exact answers may drop: {100 * d[0]:+.1f} pts, lower bound {100 * d[1]:+.1f}")
    if broken:
        reasons.append(f"fails {len(broken)} production case(s) the current system passes")
    slack = 1 + e.budget_slack
    if b["p95_ms"] > s.targets.p95_latency_ms and b["p95_ms"] > a["p95_ms"] * slack:
        reasons.append(f"p95 {b['p95_ms']} ms, over the {s.targets.p95_latency_ms:.0f} ms budget")
    if b["cost_eur"] > s.targets.cost_per_query_eur and b["cost_eur"] > a["cost_eur"] * slack:
        reasons.append(f"€{b['cost_eur']:.4f} per query, over the €{s.targets.cost_per_query_eur} budget")
    return {
        "exact": [round(x, 4) for x in d],
        "budget": b,
        "baseline_budget": a,
        "broken": broken,
        "blocked": bool(reasons),
        "reasons": reasons,
    }
