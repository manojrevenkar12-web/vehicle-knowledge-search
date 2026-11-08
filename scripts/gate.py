"""The CI gate: a proposed system against the current one (the graph agent), on the development queries and the
production cases. Exits 1 when the change is blocked. Default: the A/A rerun, which must pass."""

from __future__ import annotations

import json
import sys

from vks.evals import gate, production
from vks.evals.runner import run, searcher
from vks.evals.truth import labelled
from vks.settings import load


def main() -> None:
    s = load()
    name = sys.argv[1] if len(sys.argv) > 1 else "graph_agent"
    q, t = labelled("dev")
    pq, pt = labelled("production")
    by_id = {x["id"]: x for x in pq}
    cases = production.load_cases()
    rep = s.run.repeats
    base = run(s, searcher(s, "graph_agent"), q, t, rep)
    cand = run(s, searcher(s, name), q, t, rep, offset=rep if name == "graph_agent" else 0)
    d = gate.decide(
        base,
        cand,
        production.replay(s, "graph_agent", cases, by_id, pt),
        production.replay(s, name, cases, by_id, pt),
        s,
    )
    print(json.dumps({"candidate": name, **d}, indent=1))
    sys.exit(1 if d["blocked"] else 0)


if __name__ == "__main__":
    main()
