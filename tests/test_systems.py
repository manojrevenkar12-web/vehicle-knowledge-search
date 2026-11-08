from vks.agents.systems import Searcher, prior_graph
from vks.search.catalog import Graph, Listings, VectorIndex
from vks.settings import load

S = load()
G, P = Graph.load(), prior_graph()
IDX, L = VectorIndex(G), Listings()


def ask(system, text, seed=1, version=1, graph=G):
    return Searcher(S, system, graph, P, IDX, L, llm_version=version).answer(text, seed)


def test_the_graph_knows_a_model_the_llm_does_not():
    a = ask("graph", "Skoda Elroq bis 40.000 €")
    assert a.filters["model"] == "Elroq"
    guesses = {ask("llm_only", "Skoda Elroq bis 40.000 €", seed).filters.get("model") for seed in range(30)}
    assert guesses - {"Elroq"}, "the model alone sometimes substitutes a model it knows"


def test_the_graph_takes_years_and_power_from_the_catalogue():
    a = ask("graph", "BMW 3er F30 330i unter 20.000 €")
    gen = G.by_id["bmw/3er/f30"]
    assert (a.filters["year_from"], a.filters["year_to"]) == (gen["year_from"], gen["year_to"])
    v = next(v for v in G.variants_of("bmw/3er/f30") if v["name"] == "330i")
    assert a.filters["power_from_kw"] <= v["power_kw"] <= a.filters["power_to_kw"]


def test_the_validator_repairs_a_price_the_upgraded_model_misreads():
    plain = [ask("graph", "Golf unter 20 Tsd", seed, version=2).filters.get("price_to") for seed in range(20)]
    agent = [ask("graph_agent", "Golf unter 20 Tsd", seed, version=2).filters.get("price_to") for seed in range(20)]
    assert 20 in plain and set(agent) - {None} == {20000}


def test_the_agent_keeps_the_users_word_but_drops_a_substitution():
    for seed in range(20):
        a = ask("graph_agent", "Kia EV2 unter 30.000 €", seed)
        assert a.filters.get("model") in (None, "EV2") and "ev2" in a.unknown


def test_no_results_get_a_suggestion_and_keep_the_filters():
    a = ask("graph_agent", "Volkswagen Golf Diesel unter 1.000 €")
    assert a.filters["price_to"] == 1000 and a.suggestion and a.suggestion["drop"] == "price_to"
