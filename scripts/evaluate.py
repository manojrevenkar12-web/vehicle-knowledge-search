"""The development evaluation: four systems on the development queries, ground truth from behaviour, twelve
production weeks with their monitors, cases mined from production, and the gate on four changes. Writes
reports/dev.json. Never reads the held-out queries."""

from __future__ import annotations

import json
import sys
import time
from collections import Counter

from vks.agents.systems import SYSTEMS
from vks.evals import gate, production, sessions
from vks.evals.runner import _listings, run, searcher
from vks.evals.stats import by_call, interval, paired, pct
from vks.evals.truth import labelled
from vks.settings import ROOT, load

EXACT = lambda r: r["exact"]
CHANGES = {
    "answer from the model's own knowledge (no retrieval)": "llm_only",
    "switch the graph for vector retrieval": "vector_rag",
    "drop the validator to save a tool call": "graph",
    "same system, run again (A/A)": "graph_agent",
}


def summary(runs: list[dict], s) -> dict:
    e = s.eval
    ex = interval(list(by_call(runs, EXACT).values()), e.bootstrap, e.alpha, s.run.seed)
    kinds = sorted({r["kind"] for r in runs})
    n = len(runs)
    return {
        "exact": [round(x, 4) for x in ex],
        "result_jaccard": round(sum(r["result_jaccard"] for r in runs) / n, 4),
        "filter_f1": round(sum(r["filter_f1"] for r in runs) / n, 4),
        "zero_results": round(sum(r["zero_results"] for r in runs) / n, 4),
        "by_kind": {
            k: round(sum(r["exact"] for r in runs if r["kind"] == k) / sum(r["kind"] == k for r in runs), 4)
            for k in kinds
        },
        "by_lang": {
            g: round(sum(r["exact"] for r in runs if r["lang"] == g) / max(1, sum(r["lang"] == g for r in runs)), 4)
            for g in ("de", "en")
        },
        "wrong_keys": dict(Counter(k for r in runs for k in r["wrong_keys"]).most_common(8)),
        "p50_ms": round(pct([r["latency_ms"] for r in runs], 50)),
        "p95_ms": round(pct([r["latency_ms"] for r in runs], 95)),
        "cost_eur": round(sum(r["cost_eur"] for r in runs) / n, 5),
        "docs": round(sum(r["docs"] for r in runs) / n, 2),
        "runs": n,
    }


def main() -> None:
    s = load()
    t0 = time.time()
    q, t = labelled("dev")
    rep = s.run.repeats
    out: dict = {"queries": len(q), "repeats": rep, "relabelled": sum(bool(x.get("relabelled")) for x in t.values())}
    runs = {name: run(s, searcher(s, name), q, t, rep) for name in SYSTEMS}
    out["systems"] = {name: summary(r, s) for name, r in runs.items()}
    out["paired"] = {
        f"{b} vs {a}": [
            round(x, 4) for x in paired(runs[a], runs[b], EXACT, s.eval.bootstrap, s.eval.alpha, s.run.seed)
        ]
        for a, b in (
            ("llm_only", "vector_rag"),
            ("llm_only", "graph"),
            ("vector_rag", "graph"),
            ("graph", "graph_agent"),
        )
    }
    print("systems", round(time.time() - t0, 1), file=sys.stderr)

    # ground truth from behaviour, with vector retrieval as the system that served and logged the sessions
    L = _listings(False)
    gold = {x["id"]: {y["id"] for y in L.search(t[x["id"]]["filters"])} for x in q}
    logged = [r for r in runs["vector_rag"] if r["repeat"] == 0]
    contacts = sessions.simulate(s, logged, gold, L.search)
    out["sessions"] = sessions.analyse(contacts, gold, runs, L.search)

    # production: the graph without and with the validator, and vector retrieval
    pq, pt = labelled("production")
    out["production"] = {}
    logs = {}
    for name in ("vector_rag", "graph", "graph_agent"):
        log, scored = production.serve(s, name, pq, pt)
        logs[name] = log
        out["production"][name] = production.report(s, log, scored)
        print("production", name, round(time.time() - t0, 1), file=sys.stderr)
    cases = production.mine(logs["graph_agent"])
    production.save(cases, logs["graph_agent"])
    by_id = {x["id"]: x for x in pq}
    reg = {name: production.replay(s, name, cases, by_id, pt) for name in set(CHANGES.values())}
    out["cases"] = {
        "count": len(cases),
        "why": dict(Counter(c["why"] for c in cases)),
        "pass": {name: sum(v.values()) for name, v in reg.items()},
    }

    out["gate"] = {}
    for change, name in CHANGES.items():
        cand = run(s, searcher(s, name), q, t, rep, offset=rep if name == "graph_agent" else 0)
        out["gate"][change] = {
            "system": name,
            **gate.decide(runs["graph_agent"], cand, reg["graph_agent"], reg[name], s),
        }
    out["seconds"] = round(time.time() - t0, 1)
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "dev.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    for k, v in out["systems"].items():
        print(f"{k:12s} exact {v['exact']} jac {v['result_jaccard']} p95 {v['p95_ms']} €{v['cost_eur']} {v['by_kind']}")
    print("paired", out["paired"])
    print("sessions", out["sessions"])
    print("cases", out["cases"])
    for k, d in out["gate"].items():
        print("BLOCKED" if d["blocked"] else "passes ", k, d["exact"], d["reasons"])
    print("seconds", out["seconds"])


if __name__ == "__main__":
    main()
