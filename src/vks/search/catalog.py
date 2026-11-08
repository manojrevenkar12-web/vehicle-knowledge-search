"""The search side: the listings with the filters a result page offers, the knowledge graph with entity linking and
traversal, a TF-IDF retriever over documents written from the graph, and a validator that checks a filter set
against the graph. None of this reads what the queries were meant to find."""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

from vks.settings import ROOT

FOLD = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})
FILTER_KEYS = (
    "make",
    "model",
    "year_from",
    "year_to",
    "price_to",
    "fuel",
    "body",
    "power_from_kw",
    "power_to_kw",
    "consumption_to",
    "seats_from",
    "equipment",
    "drive",
    "gearbox",
    "mileage_to",
)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower().translate(FOLD)
    return re.sub(r"[^a-z0-9.]+", " ", s).strip()


def tokens(s: str) -> list[str]:
    return [t for t in re.split(r"[ .]+", norm(s)) if t]


def read_jsonl(path) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


# ---- listings ----
def matches(listing: dict, f: dict) -> bool:
    for k, v in f.items():
        if v is None:
            continue
        x = listing
        if (k == "make" and x["make"] != v) or (k == "model" and x["model"] != v):
            return False
        if (k == "year_from" and x["year"] < v) or (k == "year_to" and x["year"] > v):
            return False
        if (k == "price_to" and x["price"] > v) or (k == "mileage_to" and x["mileage"] > v):
            return False
        if k in ("fuel", "body") and x[k] not in v:
            return False
        if (k == "power_from_kw" and x["power_kw"] < v) or (k == "power_to_kw" and x["power_kw"] > v):
            return False
        if k == "consumption_to" and x["consumption"] is not None and x["consumption"] > v:
            return False  # electric cars pass a fuel-consumption filter
        if k == "seats_from" and x["seats"] < v:
            return False
        if k == "equipment" and not set(v) <= set(x["equipment"]):
            return False
        if k in ("drive", "gearbox") and x[k] != v:
            return False
    return True


class Listings:
    def __init__(self, extra: bool = False):
        self.items = read_jsonl(ROOT / "data" / "listings.jsonl")
        if extra:
            self.items += read_jsonl(ROOT / "data" / "listings_launch.jsonl")

    def search(self, f: dict) -> list[dict]:
        return [x for x in self.items if matches(x, f)]


# ---- the knowledge graph ----
@dataclass
class Graph:
    models: list[dict]
    generations: list[dict]
    variants: list[dict]
    concepts: dict
    bodies: dict
    surface: dict = field(default_factory=dict)  # normalised name -> ("model"|"generation"|"variant"|..., id)

    @staticmethod
    def load(with_update: bool = False) -> Graph:
        kg = json.loads((ROOT / "data" / "kg.json").read_text())
        if with_update:
            up = json.loads((ROOT / "data" / "kg_update.json").read_text())
            for k in ("models", "generations", "variants"):
                kg[k] = kg[k] + up[k]
        g = Graph(kg["models"], kg["generations"], kg["variants"], kg["concepts"], kg["bodies"])
        g._index()
        return g

    def _index(self) -> None:
        s = {}
        for m in self.models:
            s[norm(m["name"])] = ("model", m["id"])
            for a in m.get("aliases", []):
                s[norm(a)] = ("model", m["id"])
        for gen in self.generations:
            s.setdefault(norm(gen["name"]), ("generation", gen["id"]))
        for c, spec in self.concepts.items():
            for w in spec["words"]:
                s[norm(w)] = ("concept", c)
        for b, words in self.bodies.items():
            for w in words:
                s[norm(w)] = ("body", b)
        self.surface = s
        self.by_id = {x["id"]: x for x in self.models + self.generations + self.variants}

    def model_of(self, gid: str) -> dict:
        return self.by_id[self.by_id[gid]["model_id"]]

    def link(self, text: str) -> list[tuple[str, str, str]]:
        """Entity linking: the longest surface forms in the text, then German inflections by stem."""
        t = norm(text)
        found, used = [], []
        for surf in sorted(self.surface, key=len, reverse=True):
            for m in re.finditer(rf"(?<![a-z0-9]){re.escape(surf)}(?:e[rsmn]?)?(?![a-z0-9])", t):
                span = (m.start(), m.end())
                if any(a < span[1] and span[0] < b for a, b in used):
                    continue
                used.append(span)
                kind, ident = self.surface[surf]
                found.append((kind, ident, surf))
        return found

    def variants_of(self, gen_id: str) -> list[dict]:
        return [v for v in self.variants if v["generation_id"] == gen_id]

    def generations_of(self, model_id: str) -> list[dict]:
        return [g for g in self.generations if g["model_id"] == model_id]

    def make_names(self) -> set[str]:
        return {m["make"] for m in self.models}


# ---- vector retrieval over documents written from the graph ----
class VectorIndex:
    def __init__(self, g: Graph):
        self.docs: list[dict] = []
        for m in g.models:
            alias = f" Auch genannt: {', '.join(m['aliases'])}." if m.get("aliases") else ""
            self.docs.append(
                {
                    "kind": "model",
                    "id": m["id"],
                    "text": f"{m['make']} {m['name']}: {m['segment']}, Karosserie {m['body']}.{alias}",
                }
            )
        for gen in g.generations:
            m = g.by_id[gen["model_id"]]
            vs = ", ".join(f"{v['name']} ({v['fuel']}, {v['power_kw']} kW)" for v in g.variants_of(gen["id"]))
            self.docs.append(
                {
                    "kind": "generation",
                    "id": gen["id"],
                    "text": f"{m['make']} {m['name']} {gen['name']}, gebaut {gen['year_from']} bis "
                    f"{gen['year_to']}. Varianten: {vs}.",
                }
            )
        for c, spec in g.concepts.items():
            self.docs.append(
                {
                    "kind": "concept",
                    "id": c,
                    "text": f"Suchbegriff {', '.join(spec['words'])}: bedeutet {json.dumps(spec['filters'])}.",
                }
            )
        self.tf = [Counter(tokens(d["text"])) for d in self.docs]
        df = Counter(t for tf in self.tf for t in tf)
        n = len(self.docs)
        self.idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}
        self.norms = [math.sqrt(sum((c * self.idf[t]) ** 2 for t, c in tf.items())) for tf in self.tf]

    def search(self, query: str, k: int) -> list[dict]:
        q = Counter(tokens(query))
        scores = []
        for i, tf in enumerate(self.tf):
            dot = sum(q[t] * self.idf.get(t, 0) * tf.get(t, 0) * self.idf.get(t, 0) for t in q)
            scores.append((dot / (self.norms[i] or 1), i))
        scores.sort(reverse=True)
        return [self.docs[i] for s, i in scores[:k] if s > 0]


# ---- validation ----
def validate(f: dict, g: Graph) -> list[str]:
    """Problems with a filter set that the catalogue can see without knowing what the user meant."""
    problems = []
    models = {(m["make"], m["name"]): m for m in g.models}
    if f.get("model") and (f.get("make"), f["model"]) not in models:
        problems.append(f"no model '{f['model']}' for make '{f.get('make')}'")
    if f.get("make") and f["make"] not in g.make_names():
        problems.append(f"no make '{f['make']}'")
    m = models.get((f.get("make"), f.get("model")))
    if m and (f.get("year_from") or f.get("year_to")):
        gens = g.generations_of(m["id"])
        lo, hi = min(x["year_from"] for x in gens), max(x["year_to"] for x in gens)
        if (f.get("year_to") and f["year_to"] < lo) or (f.get("year_from") and f["year_from"] > hi):
            problems.append("years outside every generation of the model")
    if m and f.get("power_from_kw"):
        ps = [
            v["power_kw"]
            for gen in g.generations_of(m["id"])
            for v in g.variants_of(gen["id"])
            if (not f.get("year_from") or gen["year_to"] >= f["year_from"])
            and (not f.get("year_to") or gen["year_from"] <= f["year_to"])
        ]
        if ps and not any(f["power_from_kw"] <= p <= f.get("power_to_kw", 10_000) for p in ps):
            problems.append("no variant with that power in those years")
    if f.get("price_to") is not None and f["price_to"] < 500:
        problems.append("price below 500 EUR")
    return problems
