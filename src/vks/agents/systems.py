"""Four ways to turn a search query into result-page filters, around the same simulated model.

- `llm_only`: the model answers from its own knowledge (data/llm_prior.json): no models launched after its cutoff,
  some generation years and variant powers off, its own idea of "sparsam" or "familientauglich".
- `vector_rag`: the top documents a TF-IDF retriever finds in text written from the knowledge graph go into the
  prompt; the model uses them for the entities they cover and its own knowledge for the rest.
- `graph`: an entity linker finds models, generations, variants and concepts in the graph; the model reads the query
  and the graph supplies the facts.
- `graph_agent`: the graph, plus a validator tool after the model has answered. Values the catalogue does not have are
  repaired or dropped; a model name must come from the catalogue's own link in the query, and names it cannot link
  are flagged as unknown entities. A search with no results gets a
  relaxed suggestion, while the filters stay as asked.

The model's reading of the query (numbers, fuel, words) is a parser with configured mistakes; its knowledge is
whichever source the system gives it. Latency and cost come from config."""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass

from vks.search.catalog import Graph, Listings, VectorIndex, norm, validate
from vks.settings import ROOT, Settings

FUEL = {
    "benziner": "petrol",
    "petrol": "petrol",
    "diesel": "diesel",
    "hybrid": "hybrid",
    "elektro": "electric",
    "electric": "electric",
}
SYSTEMS = ("llm_only", "vector_rag", "graph", "graph_agent")


def prior_graph() -> Graph:
    p = json.loads((ROOT / "data" / "llm_prior.json").read_text())
    kg = json.loads((ROOT / "data" / "kg.json").read_text())
    g = Graph(p["models"], p["generations"], p["variants"], p["concepts"], kg["bodies"])
    g._index()
    return g


def parse_price(text: str, misread_tsd: bool) -> int | None:
    t = text.lower()
    m = re.search(r"(?:unter|bis|max\.|under|below|up to)\s+([\d.,]+)\s*(k|tsd|\.000|,000|euro|eur|€)?", t)
    if not m:
        return None
    num, unit = m.group(1), (m.group(2) or "")
    digits = re.sub(r"[.,]", "", num)
    if not digits.isdigit():
        return None
    v = int(digits)
    if (unit in ("k", "tsd") and not (unit == "tsd" and misread_tsd)) or unit in (".000", ",000"):
        v *= 1000
    return v


@dataclass
class Answer:
    filters: dict
    unknown: list
    problems: list
    suggestion: dict | None
    latency_ms: float
    cost_eur: float
    docs: int
    tool_calls: int


class Searcher:
    def __init__(
        self,
        s: Settings,
        system: str,
        graph: Graph,
        prior: Graph,
        index: VectorIndex,
        listings: Listings | None = None,
        llm_version: int = 1,
    ):
        self.s, self.system, self.g, self.prior, self.index = s, system, graph, prior, index
        self.listings = listings or Listings()
        self.version = llm_version

    # ---- the model reading the query with a given knowledge ----
    def _read(self, text: str, know: list[Graph], rng: random.Random) -> tuple[dict, list[str]]:
        md = self.s.model
        f: dict = {}
        unknown: list[str] = []
        linked = []
        for k in know:
            for kind, ident, surf in k.link(text):
                if any(surf == s2 or surf in s2 for _, _, s2, _ in linked):
                    continue
                if (
                    k is self.prior
                    and kind == "model"
                    and norm(k.by_id[ident]["name"]) != surf
                    and rng.random() < md.alias_miss
                ):
                    continue  # a colloquial name the model doesn't place
                linked.append((kind, ident, surf, k))
        model = gen = None
        for kind, ident, surf, k in linked:
            if kind == "model" and model is None:
                model = (k.by_id[ident], k)
            elif kind == "generation" and gen is None:
                gen = (k.by_id[ident], k)
            elif kind == "concept":
                for key, val in k.concepts[ident]["filters"].items():
                    if key in ("body", "fuel", "equipment") and key in f:
                        f[key] = sorted(set(f[key]) & set(val)) or val
                    else:
                        f[key] = val
            elif kind == "body":
                f["body"] = [ident]
        if gen and not model:
            model = (gen[1].model_of(gen[0]["id"]), gen[1])
        makes = {m["make"] for k in know for m in k.models}
        said_make = next(
            (
                mk
                for mk in sorted(makes, key=len, reverse=True)
                if re.search(rf"(?<![a-z]){re.escape(norm(mk.split('-')[0]))}(?![a-z])", norm(text))
            ),
            None,
        )
        if model:
            f["make"], f["model"] = model[0]["make"], model[0]["name"]
        elif said_make:
            f["make"] = said_make
            rest = norm(text).split(norm(said_make.split("-")[0]), 1)[1].split()
            word = rest[0] if rest else None
            if word and not re.match(r"(unter|bis|max|ab|from|under|below|up)$", word):
                guess = self.s.model.unknown_model_guess + (
                    self.s.production.llm_update_extra_guess if self.version > 1 else 0
                )
                known = [m for m in self.prior.models if m["make"] == said_make]
                if known and rng.random() < guess:
                    f["model"] = rng.choice(known)["name"]  # a plausible model it knows
                else:
                    f["model"] = word.upper() if len(word) <= 3 else word.title()
                unknown.append(word)
        if model and not gen:  # "Model 3 Long Range": a named variant, without a generation
            k = model[1]
            hits = [
                (x, v)
                for x in k.generations_of(model[0]["id"])
                for v in k.variants_of(x["id"])
                if v["special"] and re.search(rf"(?<![a-z0-9]){re.escape(norm(v['name']))}(?![a-z0-9])", norm(text))
            ]
            if len({x["id"] for x, _ in hits}) == 1:
                gen = (hits[0][0], k)
            elif hits and len({v["power_kw"] for _, v in hits}) == 1:
                v = hits[0][1]
                f["power_from_kw"], f["power_to_kw"], f["fuel"] = v["power_kw"] - 5, v["power_kw"] + 5, [v["fuel"]]
        if gen:
            f["year_from"], f["year_to"] = gen[0]["year_from"], gen[0]["year_to"]
            vs = gen[1].variants_of(gen[0]["id"])
            for v in sorted(vs, key=lambda x: -len(x["name"])):
                if v["special"] and re.search(rf"(?<![a-z0-9]){re.escape(norm(v['name']))}(?![a-z0-9])", norm(text)):
                    f["power_from_kw"], f["power_to_kw"] = v["power_kw"] - 5, v["power_kw"] + 5
                    f["fuel"] = [v["fuel"]]
                    break
        for w, fu in FUEL.items():
            if re.search(rf"(?<![a-z]){w}(?![a-z])", norm(text)):
                f["fuel"] = [fu]
        m = re.search(r"(?:ab|from)\s+(\d{4})", text)
        if m:
            f["year_from"] = int(m.group(1))
        price = parse_price(text, misread_tsd=self.version > 1 and rng.random() < 0.5)
        if price is not None and rng.random() >= md.extraction_error:
            f["price_to"] = price
        return f, unknown

    def _call_ms(self, rng: random.Random, tin: int) -> tuple[float, float]:
        md, t = self.s.model, self.s.tokens
        ms = md.ttft_ms * rng.lognormvariate(0, 0.25) + t.output / md.tokens_per_s * 1000
        return ms, tin / 1000 * md.price_in + t.output / 1000 * md.price_out

    def _tool_ms(self, rng: random.Random) -> float:
        return self.s.agent.tool_ms * rng.lognormvariate(0, self.s.agent.tool_spread)

    def answer(self, text: str, seed: int) -> Answer:
        s, t = self.s, self.s.tokens
        rng = random.Random(seed)
        docs, tools = 0, 0
        latency = cost = 0.0
        tin = t.system + t.per_query
        if self.system == "llm_only":
            know = [self.prior]
        elif self.system == "vector_rag":
            hits = self.index.search(text, s.retrieval.vector_k)
            docs = len(hits)
            tools += 1
            latency += self._tool_ms(rng)
            know = [self._from_docs(hits), self.prior]
            tin += t.per_doc * docs
        else:
            tools += 1
            latency += self._tool_ms(rng)
            know = [self.g, self.prior]
            tin += t.per_tool_result
        f, unknown = self._read(text, know, rng)
        linked_models = {self.g.by_id[i]["name"] for kind, i, _ in self.g.link(text) if kind == "model"} | {
            self.g.model_of(i)["name"] for kind, i, _ in self.g.link(text) if kind == "generation"
        }
        ms, c = self._call_ms(rng, tin)
        latency += ms
        cost += c
        problems, suggestion = [], None
        if self.system == "graph_agent":
            tools += 1
            latency += self._tool_ms(rng)
            problems = validate(f, self.g)
            if f.get("model") and f["model"] not in linked_models and norm(f["model"]) not in norm(text).split():
                # a model the catalogue did not find in the query and the user did not say: a substitution
                problems.append(f"model '{f['model']}' not found in the query by the catalogue")
            elif f.get("model") and f["model"] not in linked_models:
                unknown.append(norm(f["model"]))  # the user's own word: searched as said, logged for the graph
            if problems:
                f = self._repair(f, problems, unknown, text)
                ms, c = self._call_ms(rng, tin + t.per_tool_result)
                latency += ms
                cost += c
            tools += 1
            latency += self._tool_ms(rng)
            if not self.listings.search(f):
                suggestion = self._relax(f)
        return Answer(f, unknown, problems, suggestion, round(latency, 1), round(cost, 6), docs, tools)

    def _repair(self, f: dict, problems: list[str], unknown: list[str], text: str) -> dict:
        f = dict(f)
        for p in problems:
            if p.startswith("no model") or p.startswith("model '"):
                name = norm(f.get("model") or "")
                if name and name not in unknown:
                    unknown.append(name)  # the name goes to the unknown-entity log for the graph team
                if name not in norm(text).split():
                    f.pop("model", None)  # a substitution: keep the make only
                # the user's own word stays: listings may carry a model the catalogue doesn't have yet
            elif p.startswith("years outside"):
                f.pop("year_from", None)
                f.pop("year_to", None)
            elif p.startswith("no variant"):
                f.pop("power_from_kw", None)
                f.pop("power_to_kw", None)
            elif p.startswith("price below"):
                f["price_to"] = f["price_to"] * 1000
        return f

    def _relax(self, f: dict) -> dict | None:
        """The filter whose removal brings results back first, in order of how much a user would give up."""
        for key in ("price_to", "year_from", "mileage_to", "consumption_to", "power_from_kw", "equipment", "drive"):
            if key in f:
                g = {k: v for k, v in f.items() if k != key}
                if key == "power_from_kw":
                    g.pop("power_to_kw", None)
                if self.listings.search(g):
                    return {"drop": key, "results": len(self.listings.search(g))}
        return None

    def _from_docs(self, hits: list[dict]) -> Graph:
        ids = {h["id"] for h in hits}
        models = [m for m in self.g.models if m["id"] in ids]
        gens = [x for x in self.g.generations if x["id"] in ids]
        models += [self.g.by_id[x["model_id"]] for x in gens if self.g.by_id[x["model_id"]] not in models]
        variants = [v for v in self.g.variants if v["generation_id"] in {x["id"] for x in gens}]
        concepts = {c: self.g.concepts[c] for c in ids if c in self.g.concepts}
        k = Graph(models, gens, variants, concepts, {})
        k._index()
        return k
