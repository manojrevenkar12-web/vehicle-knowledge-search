"""Runs a system over queries, with repeats, and scores each answer against the filters the query meant."""

from __future__ import annotations

import zlib
from functools import lru_cache

from vks.agents.systems import Searcher, prior_graph
from vks.evals.score import score
from vks.search.catalog import Graph, Listings, VectorIndex
from vks.settings import Settings


@lru_cache
def _graph(update: bool) -> Graph:
    return Graph.load(with_update=update)


@lru_cache
def _listings(extra: bool) -> Listings:
    return Listings(extra=extra)


@lru_cache
def _prior() -> Graph:
    return prior_graph()


@lru_cache
def _index(update: bool) -> VectorIndex:
    return VectorIndex(_graph(update))


def seed_of(s: Settings, qid: str, repeat: int) -> int:
    return zlib.crc32(f"{s.run.seed}:{qid}:{repeat}".encode())


def searcher(
    s: Settings, system: str, kg_update: bool = False, launch_listings: bool = False, llm_version: int = 1
) -> Searcher:
    return Searcher(s, system, _graph(kg_update), _prior(), _index(kg_update), _listings(launch_listings), llm_version)


def run_one(s: Settings, S: Searcher, q: dict, truth: dict, repeat: int) -> dict:
    a = S.answer(q["text"], seed_of(s, q["id"], repeat))
    L = S.listings
    pred_ids = {x["id"] for x in L.search(a.filters)}
    gold_ids = {x["id"] for x in L.search(truth["filters"])}
    sc = score(a.filters, truth["filters"], pred_ids, gold_ids)
    return {
        "id": q["id"],
        "kind": truth["kind"],
        "lang": q["lang"],
        "repeat": repeat,
        **sc,
        "filters": a.filters,
        "unknown": a.unknown,
        "problems": a.problems,
        "suggestion": a.suggestion,
        "latency_ms": a.latency_ms,
        "cost_eur": a.cost_eur,
        "docs": a.docs,
        "tool_calls": a.tool_calls,
        "results": len(pred_ids),
    }


def run(s: Settings, S: Searcher, queries: list[dict], truth: dict, repeats: int, offset: int = 0) -> list[dict]:
    return [run_one(s, S, q, truth[q["id"]], r) for r in range(offset, offset + repeats) for q in queries]
