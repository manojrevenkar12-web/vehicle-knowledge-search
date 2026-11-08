from collections import Counter

from vks.evals import gate, production
from vks.evals.monitor import psi, unlinked_name
from vks.evals.runner import run, searcher
from vks.evals.truth import labelled
from vks.search.catalog import Graph
from vks.settings import load

S = load()


def test_psi_is_zero_for_the_same_mix_and_grows_with_a_shift():
    a = Counter({"model": 70, "drive": 5, "body": 25})
    assert psi(a, a) == 0
    assert psi(a, Counter({"model": 50, "drive": 25, "body": 25})) > S.monitor.psi_alert


def test_an_unknown_model_is_seen_from_the_query_alone():
    assert unlinked_name("Kia EV2 unter 30.000 €", Graph.load())
    assert not unlinked_name("Kia EV2 unter 30.000 €", Graph.load(with_update=True))
    assert not unlinked_name("Kia Sportage ab 2020", Graph.load())


def test_the_relabelling_rule_only_touches_generations_named_like_their_model():
    _, t = labelled("dev")
    for x in t.values():
        if x.get("relabelled"):
            assert x["kind"] == "generation" and "year_from" not in x["filters"]


def test_the_gate_passes_a_rerun_and_blocks_the_model_alone():
    q, t = labelled("dev")
    base = run(S, searcher(S, "graph_agent"), q, t, 2)
    again = run(S, searcher(S, "graph_agent"), q, t, 2, offset=2)
    assert not gate.decide(base, again, {}, {}, S)["blocked"]
    worse = run(S, searcher(S, "llm_only"), q, t, 2)
    assert gate.decide(base, worse, {}, {}, S)["blocked"]


def test_production_conditions_follow_the_timeline():
    P = S.production
    c = production.conditions
    assert c(S, P.launch_week - 1) == {"kg_update": False, "launch_listings": False, "llm_version": 1}
    assert c(S, P.launch_week)["launch_listings"] and not c(S, P.launch_week)["kg_update"]
    assert c(S, P.launch_week + P.kg_update_lag_weeks)["kg_update"]
    assert c(S, P.llm_update_week)["llm_version"] == 2
