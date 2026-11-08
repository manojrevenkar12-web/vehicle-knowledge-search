PY ?= python3
export PYTHONPATH := src

.PHONY: world test eval gate heldout report web

world:      ## regenerate the world (changes the held-out fingerprint: only before the pin)
	$(PY) scripts/build_world.py
test:
	$(PY) -m pytest -q
eval:       ## the development evaluation -> reports/dev.json, about 4 minutes
	$(PY) scripts/evaluate.py
gate:       ## CI gate: a proposed system against the graph agent (A/A by default); exits 1 when blocked
	$(PY) scripts/gate.py
heldout:    ## once: the held-out queries -> reports/heldout.json, reports/heldout-runs.log
	$(PY) scripts/heldout.py
report:     ## results.json, RESULTS.md, the README block and the dashboard's data
	$(PY) scripts/report.py
web:
	cd web && npm ci && npm test && npm run build
