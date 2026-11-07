PY := .venv/bin/python

.PHONY: orchestrator twin-builder coder test bench demo
orchestrator:
	$(PY) -m agents.orchestrator

twin-builder:
	$(PY) -m agents.twin_builder

coder:
	$(PY) -m agents.coder_agent

test:
	$(PY) -m pytest -q

bench:
	$(PY) -m bench.run_bench

demo:
	bash scripts/demo_run.sh
