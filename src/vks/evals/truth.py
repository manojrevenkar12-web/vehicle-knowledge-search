"""The evaluation's view of the world: the filters each query means. Only vks.evals reads data/truth/
(tests/test_isolation.py).

One labelling rule is applied to the generated labels, the same on every split: a query that names a generation
called exactly like its model ("Kia EV6", "Cupra Born") is a model reference, so the generation's years are not part
of what it means. The generator put them in; that was found on development queries and fixed here, before the
held-out run."""

from __future__ import annotations

import json

from vks.search.catalog import read_jsonl
from vks.settings import ROOT


def _generation_named_like_model(t: dict, q: dict, kg: dict) -> bool:
    f = t["filters"]
    if t["kind"] != "generation" or "year_from" not in f:
        return False
    model = next(m for m in kg["models"] if m["make"] == f["make"] and m["name"] == f["model"])
    gens = [
        g
        for g in kg["generations"]
        if g["model_id"] == model["id"] and (g["year_from"], g["year_to"]) == (f["year_from"], f.get("year_to"))
    ]
    return bool(gens) and gens[0]["name"] == model["name"]


def labelled(split: str) -> tuple[list[dict], dict[str, dict]]:
    q = read_jsonl(ROOT / "data" / f"{'production_queries' if split == 'production' else f'queries_{split}'}.jsonl")
    tpath = (
        ROOT / "data" / "truth" / ("production_queries.jsonl" if split == "production" else f"queries_{split}.jsonl")
    )
    t = {x["id"]: x for x in read_jsonl(tpath)}
    kg = json.loads((ROOT / "data" / "kg.json").read_text())
    for x in q:
        if _generation_named_like_model(t[x["id"]], x, kg):
            t[x["id"]]["filters"].pop("year_from", None)
            t[x["id"]]["filters"].pop("year_to", None)
            t[x["id"]]["relabelled"] = True
    return q, t
