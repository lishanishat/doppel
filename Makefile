PY := .venv/bin/python

.PHONY: orchestrator twin-builder
orchestrator:
	$(PY) -m agents.orchestrator

twin-builder:
	$(PY) -m agents.twin_builder
