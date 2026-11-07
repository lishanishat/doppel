PY := .venv/bin/python

.PHONY: orchestrator twin-builder coder
orchestrator:
	$(PY) -m agents.orchestrator

twin-builder:
	$(PY) -m agents.twin_builder

coder:
	$(PY) -m agents.coder_agent
