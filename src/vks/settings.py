"""Settings from config/vks.toml, loaded strictly: a misspelt key fails at start-up."""

from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Run(Strict):
    seed: int
    repeats: int


class World(Strict):
    listings: int
    queries_dev: int
    queries_heldout: int
    english_share: float
    today: str
    llm_cutoff_year: int


class Prior(Strict):
    generation_year_shift: float
    variant_power_error: float
    concept_drift: float


class Model(Strict):
    extraction_error: float
    unknown_model_guess: float
    alias_miss: float
    ttft_ms: float
    tokens_per_s: float
    price_in: float
    price_out: float


class Retrieval(Strict):
    vector_k: int
    graph_hops: int


class Agent(Strict):
    max_relax: int
    tool_ms: float
    tool_spread: float


class Tokens(Strict):
    system: int
    per_doc: int
    per_query: int
    per_tool_result: int
    output: int


class Sessions(Strict):
    page_size: int
    click_relevant: float
    click_irrelevant: float
    contact_given_click: float
    position_decay: float


class Production(Strict):
    weeks: int
    queries_per_week: int
    season_week: int
    launch_week: int
    kg_update_lag_weeks: int
    llm_update_week: int
    llm_update_extra_guess: float
    labelled_per_week: int


class Monitor(Strict):
    hallucination_alert: float
    zero_result_alert: float
    unknown_entity_alert: float
    psi_alert: float
    baseline_weeks: int


class Targets(Strict):
    p95_latency_ms: float
    cost_per_query_eur: float


class Eval(Strict):
    bootstrap: int
    alpha: float
    gate_max_drop: float
    budget_slack: float


class Settings(Strict):
    run: Run
    world: World
    prior: Prior
    model: Model
    retrieval: Retrieval
    agent: Agent
    tokens: Tokens
    sessions: Sessions
    production: Production
    monitor: Monitor
    targets: Targets
    eval: Eval


@lru_cache
def load(path: Path | None = None) -> Settings:
    with open(path or ROOT / "config" / "vks.toml", "rb") as f:
        return Settings.model_validate(tomllib.load(f))
