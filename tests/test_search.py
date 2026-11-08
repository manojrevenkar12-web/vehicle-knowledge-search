from vks.agents.systems import parse_price
from vks.search.catalog import Graph, Listings, matches, validate


def test_linker_finds_aliases_generations_and_inflected_concepts():
    g = Graph.load()
    found = {(k, i) for k, i, _ in g.link("Dreier Touring F30 sparsamer Familien-SUV mit Allrad")}
    assert ("model", "bmw/3er") in found
    assert ("generation", "bmw/3er/f30") in found
    assert ("concept", "sparsam") in found and ("concept", "allrad") in found


def test_a_model_launched_later_is_only_in_the_updated_graph():
    assert not [k for k, _, _ in Graph.load().link("Kia EV2") if k == "model"]
    assert [k for k, _, _ in Graph.load(with_update=True).link("Kia EV2") if k == "model"]


def test_validator_sees_impossible_filters_without_knowing_the_intent():
    g = Graph.load()
    assert validate({"make": "BMW", "model": "3er", "year_from": 2019, "year_to": 2026}, g) == []
    assert validate({"make": "BMW", "model": "Golf"}, g)
    assert validate({"make": "BMW", "model": "3er", "year_from": 1990, "year_to": 1995}, g)
    assert validate({"price_to": 38}, g) == ["price below 500 EUR"]


def test_prices_in_every_way_people_write_them():
    assert parse_price("unter 38 Tsd", False) == 38000
    assert parse_price("max. 56k", False) == 56000
    assert parse_price("bis 54.000 Euro", False) == 54000
    assert parse_price("below 18,000 EUR", False) == 18000
    assert parse_price("unter 38 Tsd", True) == 38  # the upgraded model's misreading


def test_electric_cars_pass_a_consumption_filter():
    car = {"consumption": None}
    assert matches(car, {"consumption_to": 5.5})
    assert not matches({"consumption": 7.1}, {"consumption_to": 5.5})


def test_listings_search_by_filters():
    L = Listings()
    res = L.search({"make": "Volkswagen", "model": "Golf", "fuel": ["diesel"], "price_to": 15000})
    assert res and all(x["model"] == "Golf" and x["price"] <= 15000 for x in res)
