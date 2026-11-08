# Working on vehicle-knowledge-search

This file is for people and coding agents alike: what to run, what must stay true, and how to know you broke it.

## Fast feedback

| What | Command | Time |
|---|---|---|
| Lint and format | `ruff check src tests scripts && ruff format --check src tests scripts` | ~1 s |
| All tests | `make test` | ~20 s |
| Gate a change | `python scripts/gate.py <system>` (`llm_only`, `vector_rag`, `graph`, `graph_agent`) | ~1 min |
| Development evaluation | `make eval` | ~4 min |
| Dashboard | `cd web && npm test && npm run dev` | ~3 s |

## Invariants

1. **Nothing that answers queries reads the truth.** `src/vks/search` and `src/vks/agents` never read `data/truth/`
   or `evalcases/` and never import `vks.evals`; `tests/test_isolation.py` checks it.
2. **Monitors and mining read the log only.** Labels enter through the weekly sample and the labelled production
   cases, never through a monitor.
3. **Filters come from the catalogue.** A model filter must be one the graph linked in the query, or the user's own
   word. A substitution from the model's memory is dropped and the name is logged.
4. **The gate decides.** A change to retrieval, prompts, the model or the agent passes `scripts/gate.py`. Production
   cases are not deleted to make a change pass. An A/A rerun must pass.
5. **Settings in config.** Rates, thresholds and budgets live in `config/vks.toml`; the dashboard's visual constants in
   `web/src/theme/tokens.ts`.
6. **Generated reports.** `reports/results.json`, `reports/RESULTS.md`, the README block and `web/public/data` come from
   `make report`.

## The held-out rule

The world, including the held-out queries, is pinned in `config/heldout.sha256`, recorded before any search or agent
code existed. `scripts/heldout.py` refuses to run if the data changed, if the code is not committed, or if it has run
before. When the held-out run shows a problem, publish it, fix it with a test on development data, and do not rerun
the held-out set to improve the number.
