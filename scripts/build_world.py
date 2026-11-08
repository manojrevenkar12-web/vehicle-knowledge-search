"""The world: a vehicle knowledge graph (make, model, generation, variant, and the concepts people search with), the
model's own, older and partly wrong knowledge of the same cars, a marketplace of listings, natural-language search
queries with the filters they mean, and twelve weeks of production queries with a season change, a model launch and
an LLM upgrade in them. Deterministic from config/vks.toml [run].seed.

Make and model names are real; generations, years and specifications are synthetic and only plausible. In
data/truth/: the filters each query means, and the production timeline.
"""

from __future__ import annotations

import json
import random
import shutil

from vks.settings import ROOT, load

S = load()
DATA = ROOT / "data"

# make, model, segment, body, launched, aliases, generations (name, from, to), fuels, special variants
CATALOGUE = [
    ("Volkswagen", "Golf", "compact", "limousine", 1974, ["golf"], [("Golf 6", 2008, 2012), ("Golf 7", 2012, 2019), ("Golf 8", 2019, 2026)],
     ["petrol", "diesel", "hybrid"], [("GTI", "petrol", 180), ("GTD", "diesel", 147), ("R", "petrol", 235)]),
    ("Volkswagen", "Passat", "midsize", "kombi", 1973, ["passat variant"], [("Passat B7", 2010, 2014), ("Passat B8", 2014, 2023), ("Passat B9", 2023, 2026)],
     ["petrol", "diesel", "hybrid"], [("GTE", "hybrid", 160)]),
    ("Volkswagen", "Tiguan", "suv_compact", "suv", 2007, [], [("Tiguan 1", 2007, 2015), ("Tiguan 2", 2016, 2023), ("Tiguan 3", 2024, 2026)],
     ["petrol", "diesel", "hybrid"], [("R-Line", "petrol", 140)]),
    ("Volkswagen", "ID.4", "suv_compact", "suv", 2021, ["id4"], [("ID.4", 2021, 2026)], ["electric"], [("GTX", "electric", 220)]),
    ("BMW", "3er", "midsize", "limousine", 1975, ["dreier", "3 series", "3er reihe"], [("E90", 2005, 2011), ("F30", 2012, 2018), ("G20", 2019, 2026)],
     ["petrol", "diesel", "hybrid"], [("320d", "diesel", 140), ("330i", "petrol", 190), ("M340i", "petrol", 275)]),
    ("BMW", "X3", "suv_mid", "suv", 2003, [], [("F25", 2010, 2017), ("G01", 2017, 2024), ("G45", 2024, 2026)],
     ["petrol", "diesel", "hybrid"], [("xDrive20d", "diesel", 140)]),
    ("BMW", "i4", "midsize", "limousine", 2021, [], [("G26", 2021, 2026)], ["electric"], [("eDrive40", "electric", 250)]),
    ("Audi", "A4", "midsize", "kombi", 1994, ["a4 avant"], [("B8", 2008, 2015), ("B9", 2015, 2024)], ["petrol", "diesel"],
     [("S4", "petrol", 260), ("RS4", "petrol", 331)]),
    ("Audi", "Q5", "suv_mid", "suv", 2008, [], [("Q5 I", 2008, 2016), ("Q5 II", 2017, 2024), ("Q5 III", 2024, 2026)],
     ["petrol", "diesel", "hybrid"], [("SQ5", "petrol", 260)]),
    ("Mercedes-Benz", "C-Klasse", "midsize", "limousine", 1993, ["c klasse", "c-class", "benz c"],
     [("W204", 2007, 2014), ("W205", 2014, 2021), ("W206", 2021, 2026)], ["petrol", "diesel", "hybrid"], [("C 63 AMG", "petrol", 350)]),
    ("Mercedes-Benz", "GLC", "suv_mid", "suv", 2015, [], [("X253", 2015, 2022), ("X254", 2022, 2026)], ["petrol", "diesel", "hybrid"], []),
    ("Skoda", "Octavia", "compact", "kombi", 1996, ["octavia combi"], [("Octavia 2", 2004, 2012), ("Octavia 3", 2013, 2019), ("Octavia 4", 2020, 2026)],
     ["petrol", "diesel"], [("RS", "petrol", 180)]),
    ("Skoda", "Kodiaq", "suv_mid", "suv", 2016, [], [("Kodiaq 1", 2016, 2023), ("Kodiaq 2", 2024, 2026)], ["petrol", "diesel"], []),
    ("Skoda", "Elroq", "suv_compact", "suv", 2025, [], [("Elroq", 2025, 2026)], ["electric"], []),
    ("Toyota", "Corolla", "compact", "limousine", 1966, [], [("E210", 2019, 2026)], ["hybrid"], []),
    ("Toyota", "RAV4", "suv_mid", "suv", 1994, ["rav 4"], [("XA40", 2013, 2018), ("XA50", 2019, 2026)], ["hybrid", "petrol"], []),
    ("Hyundai", "Tucson", "suv_compact", "suv", 2004, [], [("Tucson 3", 2015, 2020), ("Tucson 4", 2021, 2026)], ["petrol", "diesel", "hybrid"], []),
    ("Hyundai", "Ioniq 5", "suv_compact", "suv", 2021, ["ioniq5"], [("Ioniq 5", 2021, 2026)], ["electric"], [("N", "electric", 448)]),
    ("Kia", "Sportage", "suv_compact", "suv", 1993, [], [("Sportage 4", 2016, 2021), ("Sportage 5", 2022, 2026)], ["petrol", "diesel", "hybrid"], []),
    ("Kia", "EV6", "midsize", "suv", 2021, [], [("EV6", 2021, 2026)], ["electric"], [("GT", "electric", 430)]),
    ("Kia", "EV3", "compact", "suv", 2025, [], [("EV3", 2025, 2026)], ["electric"], []),
    ("Tesla", "Model 3", "midsize", "limousine", 2017, ["model3"], [("Model 3", 2019, 2023), ("Model 3 Highland", 2024, 2026)], ["electric"],
     [("Long Range", "electric", 366), ("Performance", "electric", 393)]),
    ("Tesla", "Model Y", "suv_mid", "suv", 2020, ["modely"], [("Model Y", 2021, 2026)], ["electric"], [("Long Range", "electric", 378)]),
    ("Renault", "Clio", "small", "kleinwagen", 1990, [], [("Clio 4", 2012, 2019), ("Clio 5", 2019, 2026)], ["petrol", "diesel", "hybrid"], []),
    ("Renault", "5 E-Tech", "small", "kleinwagen", 2025, ["r5", "renault 5"], [("R5 E-Tech", 2025, 2026)], ["electric"], []),
    ("Opel", "Corsa", "small", "kleinwagen", 1982, [], [("Corsa E", 2014, 2019), ("Corsa F", 2019, 2026)], ["petrol", "diesel", "electric"], []),
    ("Ford", "Focus", "compact", "limousine", 1998, [], [("Focus 3", 2011, 2018), ("Focus 4", 2018, 2025)], ["petrol", "diesel"], [("ST", "petrol", 206)]),
    ("Ford", "Kuga", "suv_compact", "suv", 2008, [], [("Kuga 2", 2013, 2019), ("Kuga 3", 2020, 2026)], ["petrol", "diesel", "hybrid"], []),
    ("Dacia", "Duster", "suv_compact", "suv", 2010, [], [("Duster 2", 2018, 2023), ("Duster 3", 2024, 2026)], ["petrol", "diesel"], []),
    ("Fiat", "500", "small", "kleinwagen", 2007, ["cinquecento"], [("500 (312)", 2007, 2024), ("500e", 2020, 2026)], ["petrol", "electric"], []),
    ("Seat", "Leon", "compact", "limousine", 1999, [], [("Leon 3", 2012, 2020), ("Leon 4", 2020, 2026)], ["petrol", "diesel", "hybrid"], []),
    ("Cupra", "Born", "compact", "limousine", 2021, [], [("Born", 2021, 2026)], ["electric"], []),
]
# launched after the production weeks begin: not in the knowledge graph until it is updated
LAUNCH = ("Kia", "EV2", "small", "suv", 2026, [], [("EV2", 2026, 2026)], ["electric"], [])

SEG = {  # seats, base price (new, EUR), power range kW, consumption l/100km (combustion), towing kg
    "small": (5, 19000, (55, 96), 4.6, 900), "compact": (5, 29000, (81, 150), 5.2, 1400),
    "midsize": (5, 42000, (110, 190), 5.6, 1800), "suv_compact": (5, 34000, (96, 170), 6.1, 1800),
    "suv_mid": (7, 52000, (120, 220), 6.8, 2400),
}
FUEL_FACTOR = {"petrol": 1.0, "diesel": 0.85, "hybrid": 0.75, "electric": 0.0}

CONCEPTS = {  # what the catalogue means by the words people search with
    "sparsam": {"words": ["sparsam", "sparsamer", "sparsames", "economical", "fuel-efficient"], "filters": {"consumption_to": 5.5}},
    "familie": {"words": ["familientauglich", "familienauto", "family car", "für die familie"],
                "filters": {"seats_from": 5, "body": ["kombi", "suv"]}},
    "sportlich": {"words": ["sportlich", "sportlicher", "sporty"], "filters": {"power_from_kw": 140}},
    "anhaenger": {"words": ["mit anhängerkupplung", "with a tow bar", "mit ahk"], "filters": {"equipment": ["tow_bar"]}},
    "allrad": {"words": ["allrad", "mit allrad", "all-wheel drive", "4x4"], "filters": {"drive": "awd"}},
    "automatik": {"words": ["automatik", "mit automatik", "automatic"], "filters": {"gearbox": "automatic"}},
    "wenig_km": {"words": ["wenig gelaufen", "low mileage", "wenig kilometer"], "filters": {"mileage_to": 50000}},
    "elektro": {"words": ["elektroauto", "e-auto", "electric car"], "filters": {"fuel": ["electric"]}},
}
BODY_WORDS = {"suv": ["SUV", "SUV"], "kombi": ["Kombi", "estate"], "kleinwagen": ["Kleinwagen", "small car"]}


def build_kg(rng: random.Random, catalogue: list) -> dict:
    makes, models, gens, variants = {}, [], [], []
    for make, model, seg, body, launched, aliases, generations, fuels, specials in catalogue:
        makes.setdefault(make, {"id": make.lower().replace(" ", "-"), "name": make})
        mid = f"{makes[make]['id']}/{model.lower().replace(' ', '-').replace('.', '')}"
        seats, base, (plo, phi), cons, tow = SEG[seg]
        models.append({"id": mid, "make": make, "name": model, "segment": seg, "body": body, "launched": launched,
                       "aliases": aliases, "base_price": base})
        for g, y0, y1 in generations:
            gid = f"{mid}/{g.lower().replace(' ', '-')}"
            gens.append({"id": gid, "model_id": mid, "name": g, "year_from": y0, "year_to": y1})
            for fuel in fuels:
                for _ in range(2):
                    p = rng.randint(plo, phi) // 5 * 5
                    label = {"petrol": "TSI" if make in ("Volkswagen", "Skoda", "Seat", "Cupra") else "Benzin",
                             "diesel": "TDI" if make in ("Volkswagen", "Skoda", "Seat") else "Diesel",
                             "hybrid": "Hybrid", "electric": "Elektro"}[fuel]
                    variants.append(_variant(gid, f"{label} {p} kW", fuel, p, seg, seats, cons, tow, rng))
            for name, fuel, p in specials:
                if fuel in fuels:
                    variants.append(_variant(gid, name, fuel, p, seg, seats, cons, tow, rng, special=True))
    return {"makes": list(makes.values()), "models": models, "generations": gens, "variants": variants,
            "concepts": {k: {"words": v["words"], "filters": v["filters"]} for k, v in CONCEPTS.items()},
            "bodies": {k: v for k, v in BODY_WORDS.items()}}


def _variant(gid, name, fuel, p, seg, seats, cons, tow, rng, special=False) -> dict:
    c = None if fuel == "electric" else round(cons * FUEL_FACTOR[fuel] * (1 + (p - 110) / 400) + rng.uniform(-0.3, 0.3), 1)
    return {"id": f"{gid}/{name.lower().replace(' ', '-')}", "generation_id": gid, "name": name, "fuel": fuel,
            "power_kw": p, "gearbox": "automatic" if fuel in ("electric", "hybrid") or p > 150 or rng.random() < 0.45
            else "manual", "drive": "awd" if (seg.startswith("suv") and rng.random() < 0.45) or p > 250 else "fwd",
            "seats": seats, "consumption": c, "special": special}


def build_prior(rng: random.Random, kg: dict) -> dict:
    """The model's own knowledge: no models launched after its cutoff, some years and powers off, concepts its own."""
    P = S.prior
    known = [m for m in kg["models"] if m["launched"] <= S.world.llm_cutoff_year]
    ids = {m["id"] for m in known}
    gens = []
    for g in kg["generations"]:
        if g["model_id"] not in ids:
            continue
        g = dict(g)
        if rng.random() < P.generation_year_shift:
            g["year_from"] += rng.choice([-2, -1, 1])
            g["year_to"] += rng.choice([-1, 1, 2])
        gens.append(g)
    gids = {g["id"] for g in gens}
    variants = []
    for v in kg["variants"]:
        if v["generation_id"] not in gids:
            continue
        v = dict(v)
        if rng.random() < P.variant_power_error:
            v["power_kw"] = int(v["power_kw"] * rng.choice([0.85, 0.9, 1.1, 1.15]))
        variants.append(v)
    concepts = {}
    for k, c in kg["concepts"].items():
        f = dict(c["filters"])
        if rng.random() < P.concept_drift * 2:
            for key, val in list(f.items()):
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    f[key] = type(val)(val * rng.choice([0.8, 1.2, 1.4]))
                elif key == "body":
                    f[key] = [*val, "limousine"]
        concepts[k] = {"words": c["words"], "filters": f}
    return {"note": "the model's knowledge, as of its training cutoff", "models": [
        {k: m[k] for k in ("id", "make", "name", "segment", "body", "aliases")} for m in known],
        "generations": gens, "variants": variants, "concepts": concepts}


def build_listings(rng: random.Random, kg: dict, n: int, models_extra: list | None = None) -> list[dict]:
    gens = {g["id"]: g for g in kg["generations"]}
    models = {m["id"]: m for m in kg["models"] + (models_extra or [])}
    by_gen: dict[str, list] = {}
    for v in kg["variants"]:
        by_gen.setdefault(v["generation_id"], []).append(v)
    year_now = int(S.world.today[:4])
    out = []
    pool = [v for v in kg["variants"]]
    for i in range(n):
        v = rng.choice(pool)
        g = gens[v["generation_id"]]
        m = models[g["model_id"]]
        year = rng.randint(g["year_from"], min(g["year_to"], year_now))
        age = max(0, year_now - year)
        mileage = int(max(0, rng.gauss(14000 * age + 3000, 6000 + 4000 * age)) // 500 * 500)
        price = m["base_price"] * (1 + (v["power_kw"] - 110) / 300) * (0.86 ** age) * rng.uniform(0.85, 1.15)
        price *= 0.95 if mileage > 150000 else 1.0
        equipment = [e for e, p in (("tow_bar", 0.45 if m["segment"].startswith("suv") or m["body"] == "kombi" else 0.15),
                                    ("navi", 0.6), ("heated_seats", 0.5)) if rng.random() < p]
        out.append({"id": f"L{i + 1:05d}", "make": m["make"], "model": m["name"], "model_id": m["id"],
                    "generation_id": g["id"], "variant": v["name"], "year": year, "mileage": mileage,
                    "price": int(price // 100 * 100), "fuel": v["fuel"], "body": m["body"], "gearbox": v["gearbox"],
                    "power_kw": v["power_kw"], "drive": v["drive"], "seats": v["seats"],
                    "consumption": v["consumption"], "equipment": equipment})
    return out


# ---- queries ----
def _price(rng, lo=8, hi=60) -> int:
    return rng.choice(range(lo, hi + 1, 2)) * 1000


def say_price(p: int, en: bool, rng) -> str:
    k = p // 1000
    if en:
        return rng.choice([f"under {k}k", f"below {p:,} EUR".replace(",", ","), f"up to {k}k euros"])
    return rng.choice([f"unter {k}.000 €", f"bis {k}.000 Euro", f"unter {k} Tsd", f"max. {k}k"])


FUEL_WORDS = {"petrol": ("Benziner", "petrol"), "diesel": ("Diesel", "diesel"), "hybrid": ("Hybrid", "hybrid"),
              "electric": ("Elektro", "electric")}


def make_query(rng: random.Random, kg: dict, kind: str, en: bool, models_pool: list) -> tuple[str, dict]:
    gens = kg["generations"]
    variants = kg["variants"]
    models = {m["id"]: m for m in kg["models"]}
    f: dict = {}
    if kind in ("explicit", "alias"):
        m = rng.choice([x for x in models_pool if (x["aliases"] if kind == "alias" else True)])
        name = rng.choice(m["aliases"]).title() if kind == "alias" else m["name"]
        f.update(make=m["make"], model=m["name"])
        parts = [name if kind == "alias" else f"{m['make'].split('-')[0]} {m['name']}"]
        fuels = sorted({v["fuel"] for v in variants for g in gens if g["model_id"] == m["id"] and v["generation_id"] == g["id"]})
        if len(fuels) > 1 and rng.random() < 0.6:
            fu = rng.choice(fuels)
            f["fuel"] = [fu]
            parts.append(FUEL_WORDS[fu][1 if en else 0])
        if rng.random() < 0.6:
            y = rng.randint(2014, 2023)
            f["year_from"] = y
            parts.append(f"from {y}" if en else f"ab {y}")
        if rng.random() < 0.8:
            p = _price(rng)
            f["price_to"] = p
            parts.append(say_price(p, en, rng))
        return " ".join(parts), f
    if kind == "generation":
        specials = [v for v in variants if v["special"]]
        v = rng.choice(specials) if rng.random() < 0.7 else None
        g = next(x for x in gens if x["id"] == v["generation_id"]) if v else rng.choice(gens)
        m = models[g["model_id"]]
        f.update(make=m["make"], model=m["name"], year_from=g["year_from"], year_to=g["year_to"])
        text = g["name"] if g["name"].startswith(m["name"].split()[0]) else f"{m['make'].split('-')[0]} {m['name']} {g['name']}"
        if v:
            f.update(power_from_kw=v["power_kw"] - 5, power_to_kw=v["power_kw"] + 5, fuel=[v["fuel"]])
            text += f" {v['name']}"
        if rng.random() < 0.8:
            p = _price(rng, 10, 70)
            f["price_to"] = p
            text += " " + say_price(p, en, rng)
        return text, f
    if kind == "concept":
        cs = rng.sample(list(CONCEPTS), rng.randint(1, 3))
        words = []
        for c in cs:
            for key, val in CONCEPTS[c]["filters"].items():
                if key in ("body", "fuel", "equipment") and key in f:
                    f[key] = sorted(set(f[key]) & set(val)) or val
                else:
                    f[key] = val
            w = CONCEPTS[c]["words"]
            words.append(w[2] if en and len(w) > 2 else w[0])
        if rng.random() < 0.5 and "body" not in f:
            b = rng.choice(list(BODY_WORDS))
            f["body"] = [b]
            words.append(BODY_WORDS[b][1 if en else 0])
        p = _price(rng, 10, 50)
        f["price_to"] = p
        return " ".join(words + [say_price(p, en, rng)]), f
    if kind == "new_model":
        m = rng.choice([x for x in kg["models"] if x["launched"] > S.world.llm_cutoff_year])
        f.update(make=m["make"], model=m["name"])
        text = f"{m['make'].split('-')[0]} {m['name']}"
        if rng.random() < 0.8:
            p = _price(rng, 20, 50)
            f["price_to"] = p
            text += " " + say_price(p, en, rng)
        return text, f
    raise ValueError(kind)


KINDS = [("explicit", 0.3), ("generation", 0.25), ("concept", 0.25), ("alias", 0.1), ("new_model", 0.1)]


def queries(rng, kg, n, prefix, weights=KINDS, models_pool=None) -> tuple[list[dict], list[dict]]:
    pool = models_pool or [m for m in kg["models"] if m["launched"] <= int(S.world.today[:4])]
    q, t = [], []
    kinds, w = zip(*weights)
    for i in range(n):
        kind = rng.choices(kinds, weights=w)[0]
        en = rng.random() < S.world.english_share
        text, f = make_query(rng, kg, kind, en, pool)
        qid = f"{prefix}-{i + 1:04d}"
        q.append({"id": qid, "text": text, "lang": "en" if en else "de"})
        t.append({"id": qid, "kind": kind, "filters": f})
    return q, t


def main() -> None:
    rng = random.Random(S.run.seed)
    if DATA.exists():
        shutil.rmtree(DATA)
    (DATA / "truth").mkdir(parents=True)
    kg = build_kg(rng, CATALOGUE)
    kg_launch = build_kg(random.Random(S.run.seed + 1), [LAUNCH])
    prior = build_prior(rng, kg)
    listings = build_listings(rng, kg, S.world.listings)
    launch_listings = build_listings(rng, kg_launch, 200)
    for i, x in enumerate(launch_listings):
        x["id"] = f"N{i + 1:05d}"
    (DATA / "kg.json").write_text(json.dumps(kg, ensure_ascii=False, indent=1))
    (DATA / "kg_update.json").write_text(json.dumps(kg_launch, ensure_ascii=False, indent=1))
    (DATA / "llm_prior.json").write_text(json.dumps(prior, ensure_ascii=False, indent=1))
    (DATA / "listings.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in listings))
    (DATA / "listings_launch.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in launch_listings))
    for split, n in (("dev", S.world.queries_dev), ("heldout", S.world.queries_heldout)):
        q, t = queries(rng, kg, n, split[:3].upper())
        (DATA / f"queries_{split}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in q))
        (DATA / "truth" / f"queries_{split}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in t))
    # production: twelve weeks, with winter, a launch and (outside the world) an LLM upgrade
    P = S.production
    prod_q, prod_t = [], []
    full = {**kg, "models": kg["models"] + kg_launch["models"], "generations": kg["generations"] + kg_launch["generations"],
            "variants": kg["variants"] + kg_launch["variants"]}
    for week in range(1, P.weeks + 1):
        weights = list(KINDS)
        if week >= P.season_week:
            weights = [(k, w * (1.6 if k == "concept" else 1.0)) for k, w in weights]
        q, t = queries(rng, kg, P.queries_per_week, f"W{week:02d}", weights)
        if week >= P.season_week:     # winter: all-wheel drive and SUVs
            for qq, tt in zip(q, t):
                if tt["kind"] == "concept" and rng.random() < 0.5 and "drive" not in tt["filters"]:
                    word = "all-wheel drive" if qq["lang"] == "en" else "Allrad"
                    qq["text"] = f"{word} {qq['text']}"
                    tt["filters"]["drive"] = "awd"
        if week >= P.launch_week:     # people search for the new model
            n_new = int(P.queries_per_week * 0.06)
            lq, lt = queries(rng, full, n_new, f"W{week:02d}N", [("explicit", 1.0)], models_pool=kg_launch["models"])
            for x, y in zip(lq, lt):
                y["kind"] = "launch"
            q, t = q + lq, t + lt
        for x, y in zip(q, t):
            x["week"] = week
            y["week"] = week
        prod_q += q
        prod_t += t
    (DATA / "production_queries.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in prod_q))
    (DATA / "truth" / "production_queries.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in prod_t))
    print("world written:", len(listings), "listings,", len(kg["variants"]), "variants,", len(prod_q), "production queries")


if __name__ == "__main__":
    main()
