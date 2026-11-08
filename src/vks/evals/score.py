"""Scores an answer against the filters the query meant: filter by filter, as a result set, and for values the
catalogue doesn't have."""

from __future__ import annotations

from vks.search.catalog import FILTER_KEYS


def _eq(a, b) -> bool:
    if isinstance(a, list) or isinstance(b, list):
        return sorted(a or []) == sorted(b or [])
    return a == b


def score(pred: dict, gold: dict, pred_ids: set[str], gold_ids: set[str]) -> dict:
    keys = [k for k in FILTER_KEYS if k in pred or k in gold]
    right = sum(1 for k in keys if k in pred and k in gold and _eq(pred[k], gold[k]))
    p = right / max(1, sum(1 for k in keys if k in pred))
    r = right / max(1, sum(1 for k in keys if k in gold))
    union = pred_ids | gold_ids
    jac = len(pred_ids & gold_ids) / len(union) if union else 1.0
    wrong = sorted(k for k in keys if k in gold and (k not in pred or not _eq(pred[k], gold[k])))
    extra = sorted(k for k in keys if k in pred and k not in gold)
    return {
        "exact": not wrong and not extra,
        "filter_precision": round(p, 4),
        "filter_recall": round(r, 4),
        "filter_f1": round(2 * p * r / (p + r), 4) if p + r else 0.0,
        "result_jaccard": round(jac, 4),
        "zero_results": not pred_ids,
        "gold_zero": not gold_ids,
        "wrong_keys": wrong,
        "extra_keys": extra,
    }
