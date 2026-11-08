"""The held-out run: 160 queries nobody looked at, through all four systems, once. Checks the pin, refuses a second
run and uncommitted code, and appends to reports/heldout-runs.log. Published as it comes out."""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys

from vks import heldout
from vks.agents.systems import SYSTEMS
from vks.evals.runner import run, searcher
from vks.evals.stats import paired
from vks.evals.truth import labelled
from vks.settings import ROOT, load

sys.path.insert(0, str(ROOT / "scripts"))
from evaluate import EXACT, summary

LOG = ROOT / "reports" / "heldout-runs.log"


def main() -> None:
    heldout.check()
    if LOG.exists() and LOG.read_text().strip():
        sys.exit("the held-out run has already happened; see reports/heldout-runs.log")
    if subprocess.run(
        ["git", "status", "--porcelain", "src", "config", "scripts"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip():
        sys.exit("commit the code first: the log records the commit the run used")
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    s = load()
    q, t = labelled("heldout")
    runs = {name: run(s, searcher(s, name), q, t, s.run.repeats) for name in SYSTEMS}
    e = s.eval
    out = {
        "queries": len(q),
        "repeats": s.run.repeats,
        "commit": commit,
        "fingerprint": heldout.fingerprint(),
        "systems": {k: summary(v, s) for k, v in runs.items()},
        "paired": {
            f"{b} vs {a}": [round(x, 4) for x in paired(runs[a], runs[b], EXACT, e.bootstrap, e.alpha, s.run.seed)]
            for a, b in (("llm_only", "graph_agent"), ("vector_rag", "graph_agent"))
        },
    }
    (ROOT / "reports" / "heldout.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    stamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with LOG.open("a") as f:
        f.write(
            f"{stamp} commit={commit} fingerprint={out['fingerprint'][:16]} queries={len(q)} repeats={s.run.repeats} "
            + " ".join(f"{k}={v['exact'][0]:.3f}" for k, v in out["systems"].items())
            + "\n"
        )
    for k, v in out["systems"].items():
        print(k, v["exact"], v["p95_ms"], v["cost_eur"], v["by_kind"])
    print(out["paired"])


if __name__ == "__main__":
    main()
