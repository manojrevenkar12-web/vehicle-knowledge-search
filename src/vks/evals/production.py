"""Twelve production weeks. Winter starts in week 6, a new model goes on sale in week 7 and reaches the knowledge graph
two weeks later, and the LLM behind the search is upgraded in week 10. Each week is served under its own conditions;
the log keeps what the system saw and did, the evaluation keeps the truth."""

from __future__ import annotations

import json
import random

from vks.evals.monitor import weekly
from vks.evals.runner import run_one, searcher
from vks.evals.stats import interval
from vks.search.catalog import Graph
from vks.settings import ROOT, Settings

CASES = ROOT / "evalcases" / "production.jsonl"


def conditions(s: Settings, week: int) -> dict:
    P = s.production
    return {
        "kg_update": week >= P.launch_week + P.kg_update_lag_weeks,
        "launch_listings": week >= P.launch_week,
        "llm_version": 2 if week >= P.llm_update_week else 1,
    }


def serve(s: Settings, system: str, queries: list[dict], truth: dict) -> tuple[list[dict], list[dict]]:
    log, scored = [], []
    for week in sorted({q["week"] for q in queries}):
        S = searcher(s, system, **conditions(s, week))
        for q in (x for x in queries if x["week"] == week):
            r = run_one(s, S, q, truth[q["id"]], week)
            log.append(
                {
                    "id": q["id"],
                    "week": week,
                    "text": q["text"],
                    "filters": r["filters"],
                    "results": r["results"],
                    "problems": r["problems"],
                    "unknown": r["unknown"],
                    "latency_ms": r["latency_ms"],
                }
            )
            scored.append(r | {"week": week})
    return log, scored


def report(s: Settings, log: list[dict], scored: list[dict]) -> list[dict]:
    graphs = {False: Graph.load(False), True: Graph.load(True)}
    mon = weekly(log, lambda w: graphs[conditions(s, w)["kg_update"]], s.monitor.baseline_weeks)
    rng = random.Random(s.run.seed + 3)
    M = s.monitor
    import numpy as np

    base = [r for r in mon if r["week"] <= M.baseline_weeks]

    def limit(key: str, floor: float) -> float:
        # an alert is a value the first weeks would not produce: three standard deviations above their mean
        vals = [r[key] for r in base]
        return max(floor, float(np.mean(vals) + 3 * np.std(vals)))

    lims = {
        "zero_results": limit("zero_results", M.zero_result_alert),
        "unknown_entities": limit("unknown_entities", M.unknown_entity_alert),
        "hallucinations": limit("hallucinations", M.hallucination_alert),
        "psi": M.psi_alert,
    }
    for row in mon:
        w = row["week"]
        ws = [r for r in scored if r["week"] == w]
        row["exact_true"] = round(sum(r["exact"] for r in ws) / len(ws), 4)
        sample = rng.sample(ws, min(s.production.labelled_per_week, len(ws)))
        est = interval([float(r["exact"]) for r in sample], s.eval.bootstrap, s.eval.alpha, s.run.seed + w)
        row["exact_labelled"] = [round(x, 4) for x in est]
        row["alerts"] = [
            name
            for name, key in (
                ("zero results", "zero_results"),
                ("unknown entities", "unknown_entities"),
                ("hallucinations", "hallucinations"),
                ("query drift", "psi"),
            )
            if row[key] > lims[key]
        ]
        row["limits"] = {k: round(v, 4) for k, v in lims.items()}
    return mon


def mine(log: list[dict]) -> list[dict]:
    """Queries the validator or the linker flagged become cases for a person to label: a name the catalogue could
    not link, or a value it does not have. Zero results alone are not mined: most are people asking for a car that
    isn't on sale at that price. Reads the log only."""
    return [
        {
            "case": f"PROD-{i + 1:03d}",
            "id": e["id"],
            "week": e["week"],
            "why": "unknown entity" if e["unknown"] else "invalid value",
        }
        for i, e in enumerate(e for e in log if e["unknown"] or e["problems"])
    ]


def replay(s: Settings, system: str, cases: list[dict], queries: dict, truth: dict) -> dict[str, bool]:
    out = {}
    for c in cases:
        S = searcher(s, system, **conditions(s, c["week"]))
        r = run_one(s, S, queries[c["id"]], truth[c["id"]], c["week"])
        out[c["case"]] = bool(r["exact"])
    return out


def save(cases: list[dict], log: list[dict]) -> None:
    CASES.parent.mkdir(exist_ok=True)
    CASES.write_text("".join(json.dumps(c) + "\n" for c in cases))
    (ROOT / "logs").mkdir(exist_ok=True)
    (ROOT / "logs" / "production.jsonl").write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in log))


def load_cases() -> list[dict]:
    return [json.loads(x) for x in CASES.read_text().splitlines()] if CASES.exists() else []
