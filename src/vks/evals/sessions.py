"""Ground truth from behaviour. The system in production shows a result page; users click and contact listings that
fit what they wanted, and now and then ones that don't, with attention falling down the page. Contacted listings look
like free relevance labels. This measures how good those labels are and what they can and cannot judge: they only
exist for listings the logging system showed."""

from __future__ import annotations

import random
import zlib

from vks.evals.stats import by_call
from vks.settings import Settings


def rank(listing_ids: list[str]) -> list[str]:
    """The marketplace's own ordering of a result set, the same for every system."""
    return sorted(listing_ids, key=lambda i: zlib.crc32(i.encode()))


def simulate(s: Settings, logged: list[dict], gold: dict[str, set[str]], listings_of) -> dict[str, set[str]]:
    S = s.sessions
    rng = random.Random(s.run.seed + 21)
    contacts = {}
    for r in logged:
        shown = rank([x["id"] for x in listings_of(r["filters"])])[: S.page_size]
        got = set()
        for pos, lid in enumerate(shown):
            p = (S.click_relevant if lid in gold[r["id"]] else S.click_irrelevant) * (1 - S.position_decay) ** pos
            if rng.random() < p and rng.random() < S.contact_given_click:
                got.add(lid)
        contacts[r["id"]] = got
    return contacts


def analyse(
    contacts: dict[str, set[str]], gold: dict[str, set[str]], systems: dict[str, list[dict]], listings_of
) -> dict:
    labelled = {q: c for q, c in contacts.items() if c}
    right = sum(len(c & gold[q]) for q, c in labelled.items())
    total = sum(len(c) for c in labelled.values())
    coverage = [min(1.0, len(c) / len(gold[q])) for q, c in labelled.items() if gold[q]]
    out = {
        "queries": len(contacts),
        "queries_with_contacts": len(labelled),
        "label_precision": round(right / max(1, total), 4),
        "gold_share_labelled": round(sum(coverage) / max(1, len(coverage)), 4),
        "systems": {},
    }
    for name, runs in systems.items():
        first = [r for r in runs if r["repeat"] == 0]
        recall = []
        for r in first:
            c = labelled.get(r["id"])
            if c:
                ids = {x["id"] for x in listings_of(r["filters"])}
                recall.append(len(c & ids) / len(c))
        out["systems"][name] = {
            "contact_recall": round(sum(recall) / max(1, len(recall)), 4),
            "exact_true": round(sum(by_call(runs, lambda r: r["exact"]).values()) / len({r["id"] for r in runs}), 4),
        }
    return out
