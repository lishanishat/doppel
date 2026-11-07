# Engine-internal interfaces (frozen 12:58; engine side only)

Public boundary is `contract/types.py` (do not change). These are the internal seams so each
module can be built in parallel. Python 3, stdlib + hypothesis (+ matplotlib in bench only).

## Function target module: `demo_target/<fn>/`
- `spec.md` (signature on line 1), `reference.py` (correct), `schema.py` exposing
  `FUNCTION_NAME`, `ARG_NAMES`, `inputs()` -> Hypothesis strategy of kwargs dicts (JSON values).
- Load by name: `engine.target.load(fn) -> Target(spec_text, reference_code, entrypoint, strategy)`.

## engine/protocol.py
- `encode_result(value) -> {"ok": True, "value": normalize(value)}`; errors -> `{"ok": False}`.
- `normalize(v)`: Decimal -> str via `format(v, "f")`; date -> isoformat; str of a decimal number
  -> canonical 2dp-insensitive form is NOT applied (compare strings exactly, after `.strip()`);
  floats -> `repr`; lists/dicts recursively. Keep it simple and documented.
- `same(a, b) -> bool`: both `ok` False -> equal (raised-vs-not only); else ok flags and values equal.
- `key(result) -> str`: stable JSON string used for vote grouping.

## engine/harness.py
- `class Runner(name, code, entrypoint, timeout_s=2.0)`: starts ONE long-lived subprocess
  (`python -I -u engine/_worker.py`), sends code once, then JSON lines `{"kwargs": {...}}` ->
  `{"ok":..., "value":...}` or `{"ok": false}`.
  - `.call(kwargs) -> dict` result; on timeout/crash returns `{"ok": False, "error": "timeout"|"crash"}`
    AND restarts the process. `error` key marks harness faults (not disagreements).
  - `.restart()`, `.close()`; context manager.
  - Load failure (syntax error, missing entrypoint) -> raises `BuildError(name, msg)` at construction.
- `engine/_worker.py`: the subprocess loop. Must stay import-light.

## engine/referee.py
- `run(target, versions: list[contract.Version], seed=0, max_examples=2000, time_budget_s=60) -> RefereeResult`
  - Hypothesis drives the shared strategy; each input goes to all three Runners.
  - Records disagreements; shrinks (Hypothesis `find`/failing-test shrink) to minimal inputs;
    keeps up to K=5 distinct shrunk counterexamples (distinct by vote pattern).
  - Confirm-twice: rerun each shrunk input on freshly restarted Runners, twice; identical -> confirmed,
    else flaky (counted, excluded). Harness faults (`error` key) are never disagreements.
- `RefereeResult` (dict): `n_inputs, disagreements: int, confirmed: list[Counterexample], flaky: int,
  faults: dict[name, int], samples: list[dict]` (up to 200 inputs+outputs, for rules), `timings`.
- `vote(outputs: dict[name, result]) -> (vote_str, majority_names)` — "3-0"|"2-1"|"1-1-1".

## engine/rules.py
- `RULES: dict[fn, list[Rule]]`; `Rule(name, spec_line, check(kwargs, result) -> bool)`.
- prorate_refund invariants: rule 9 (never negative, never > price), rule 10 (exactly 2dp string),
  rule 5 (invalid input raises: price with 3dp / cancel outside period).
- `evaluate(fn, samples, versions_outputs) -> list[contract.RuleResult]`: active only if `spec_line`
  is quoted from spec.md AND the rule passes on >= 1 twin; else advisory.

## engine/verdict.py
- `decide(referee_result, rule_results, build_errors, scope_error) -> (verdict, reason, counterexample|None, question|None)`
  — pure function implementing CLAUDE.md §6 in order. No LLM, no I/O.

## engine/ledger.py
- `write(run_id, payload) -> path` under `ledgers/` (gitignored). Fields per CLAUDE.md §7.

## engine/regression.py
- `regression.json` at repo root: list of `{question_id, input, expected, chosen, question, ts}`.
- `save(question, chosen) -> int`, `check(fn, runner_pr) -> (n_checked, n_failed)`.
- Pending questions persisted to `ledgers/questions.json` so `answer_question` works across processes.

## engine/api.py (real branch) and engine/cli.py
- `python -m engine.cli verify --fn prorate_refund --pr path.py [--twin-a p --twin-b p] [--seed 0 --max-examples 2000]`
  Twins default to `twins_cache/<fn>/twin_a.py|twin_b.py`; if missing, placeholders from `engine/tests/`.

## bench/
- `mutate.py`: `generate(reference_code, seed=0) -> list[Mutant]` via AST operators
  (flip_comparison, swap_arith, off_by_one_const, remove_check, swap_rounding). Deterministic ids.
  Split: `id % 3 == 0` -> dev, else heldout, fixed BEFORE any tuning. Cache to `bench/mutants/<fn>.json`.
- `api.py` real: `get_mutant(n)`, `list_mutants(split)` from that cache.
- `baselines.py`: run pytest-style tests (PR's own tests from `demo_target/<fn>/ai_pr/`, LLM blind
  tests from `bench/llm_artifacts/`) against a mutant; caught = any failure. Skip a baseline cleanly
  if its files are absent, and say so in the report.
- `run_bench.py` / `doppel bench`: likely-equivalent detection (mutant == reference on all fuzzed
  inputs), catch rate per method on heldout, misses by name, false alarms on reference, time per run,
  chart PNG `docs/bench.png` + `docs/BENCH.md`. **Only real measured numbers.**

## Placeholder versions (until real twins land): `engine/tests/placeholders/`
- `float_twin.py` (uses float math -> rounding disagreements), `inclusive_twin.py` (counts cancel day
  as used -> the ambiguity), `buggy_pr.py` (off-by-one on total days).
