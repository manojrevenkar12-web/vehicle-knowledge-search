"""Builds reports/results.json, reports/RESULTS.md, the README results block and the dashboard's data from
reports/dev.json and reports/heldout.json, plus four example queries answered by every system. Every number in the
README comes from here."""

from __future__ import annotations

import json
import re

from vks.agents.systems import SYSTEMS
from vks.evals.runner import run_one, searcher
from vks.evals.truth import labelled
from vks.settings import ROOT, load

NAMES = {
    "llm_only": "Model alone",
    "vector_rag": "Vector RAG",
    "graph": "Knowledge graph",
    "graph_agent": "Graph + validator",
}


def examples(s) -> list[dict]:
    q, t = labelled("dev")
    S = {n: searcher(s, n) for n in SYSTEMS}
    out = []
    for kind in ("generation", "concept", "new_model", "alias"):
        for x in q:
            if t[x["id"]]["kind"] != kind:
                continue
            res = {n: run_one(s, S[n], x, t[x["id"]], 0) for n in SYSTEMS}
            gold_n = len(S["graph"].listings.search(t[x["id"]]["filters"]))
            if (
                not res["llm_only"]["exact"]
                and res["graph_agent"]["exact"]
                and gold_n
                and res["llm_only"]["results"] != gold_n
            ):
                out.append(
                    {
                        "id": x["id"],
                        "kind": kind,
                        "text": x["text"],
                        "gold": t[x["id"]]["filters"],
                        "gold_results": gold_n,
                        "systems": {
                            n: {
                                "filters": r["filters"],
                                "exact": r["exact"],
                                "results": r["results"],
                                "wrong": r["wrong_keys"],
                                "extra": r["extra_keys"],
                            }
                            for n, r in res.items()
                        },
                    }
                )
                break
    return out


def pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}%"


def main() -> None:
    s = load()
    dev = json.loads((ROOT / "reports" / "dev.json").read_text())
    ho = json.loads((ROOT / "reports" / "heldout.json").read_text())
    log = (ROOT / "reports" / "heldout-runs.log").read_text().strip().splitlines()
    res = {
        "dev": dev,
        "heldout": ho,
        "heldout_runs": log,
        "targets": s.targets.model_dump(),
        "names": NAMES,
        "examples": examples(s),
        "config": {
            "repeats": s.run.repeats,
            "production": s.production.model_dump(),
            "gate_max_drop": s.eval.gate_max_drop,
            "monitor": s.monitor.model_dump(),
        },
    }
    (ROOT / "reports" / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    web = ROOT / "web" / "public" / "data"
    web.mkdir(parents=True, exist_ok=True)
    (web / "results.json").write_text(json.dumps(res, ensure_ascii=False))
    t = s.targets
    H = ho["systems"]
    lines = [
        f"Held-out run: {ho['queries']} queries × {ho['repeats']} repeats, run once at commit `{ho['commit']}`.",
        "",
        "| | Exact filters | Result sets (Jaccard) | Zero results | p95 latency | Cost per query |",
        "|---|---|---|---|---|---|",
    ]
    for k in SYSTEMS:
        v = H[k]
        lines.append(
            f"| {NAMES[k]} | {pct(v['exact'][0])} ({pct(v['exact'][1], 0)}–{pct(v['exact'][2], 0)}) | "
            f"{v['result_jaccard']:.3f} | {pct(v['zero_results'])} | {v['p95_ms'] / 1000:.2f} s | "
            f"€{v['cost_eur']:.4f} |"
        )
    lines += [
        "",
        f"Budgets: p95 {t.p95_latency_ms / 1000:.1f} s, €{t.cost_per_query_eur} per query.",
        "",
        "By kind of query (held out, exact filters):",
        "",
        "| Kind | " + " | ".join(NAMES[k] for k in SYSTEMS) + " |",
        "|---|---|---|---|---|",
    ]
    for kind in sorted(H["graph"]["by_kind"]):
        lines.append(
            f"| {kind.replace('_', ' ')} | " + " | ".join(pct(H[k]["by_kind"][kind], 0) for k in SYSTEMS) + " |"
        )
    P = dev["production"]
    lines += [
        "",
        "Twelve production weeks (exact filters per week; alerts from the label-free monitors):",
        "",
        "| Week | What happened | Graph, no validator | Graph + validator | Alerts (graph + validator) |",
        "|---|---|---|---|---|",
    ]
    pc = s.production
    events = {
        pc.season_week: "winter: all-wheel drive and SUVs",
        pc.launch_week: "Kia EV2 goes on sale",
        pc.launch_week + pc.kg_update_lag_weeks: "EV2 reaches the knowledge graph",
        pc.llm_update_week: "the LLM is upgraded",
    }
    for a, b in zip(P["graph"], P["graph_agent"]):
        lines.append(
            f"| {a['week']} | {events.get(a['week'], '')} | {pct(a['exact_true'])} | {pct(b['exact_true'])} | "
            f"{', '.join(b['alerts']) or '–'} |"
        )
    se = dev["sessions"]
    c = dev["cases"]
    lines += [
        "",
        f"Ground truth from behaviour: contacts are right {pct(se['label_precision'])} of the time but cover "
        f"{pct(se['gold_share_labelled'])} of the relevant listings, and {se['queries_with_contacts']} of "
        f"{se['queries']} queries get any. Judged by contacts, the model alone scores "
        f"{pct(se['systems']['llm_only']['contact_recall'])}; its exact-filter rate is "
        f"{pct(se['systems']['llm_only']['exact_true'])}.",
        "",
        f"Production cases: {c['count']} queries the linker or validator flagged, labelled; the graph + validator "
        f"passes {c['pass']['graph_agent']}, the graph without it {c['pass']['graph']}.",
        "",
        "Gate (development queries and production cases):",
        "",
        "| Change | Decision | Why |",
        "|---|---|---|",
    ]
    for change, g in dev["gate"].items():
        why = (
            "; ".join(g["reasons"])
            if g["reasons"]
            else f"exact {100 * g['exact'][0]:+.1f} pts (lower bound {100 * g['exact'][1]:+.1f})"
        )
        lines.append(f"| {change} | {'blocked' if g['blocked'] else 'passes'} | {why} |")
    block = "\n".join(lines)
    (ROOT / "reports" / "RESULTS.md").write_text("# Results\n\nGenerated by `make report`.\n\n" + block + "\n")
    readme = ROOT / "README.md"
    if readme.exists():
        txt = readme.read_text()
        txt = re.sub(
            r"<!-- results:start -->.*<!-- results:end -->",
            "<!-- results:start -->\n" + block + "\n<!-- results:end -->",
            txt,
            flags=re.S,
        )
        readme.write_text(txt)
    print(block)


if __name__ == "__main__":
    main()
