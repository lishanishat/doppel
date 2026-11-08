"""Shared contract between the Fetch side (agents/, twins/) and the engine side (engine/, bench/).

FROZEN at 12:45 pm. Do not change field names or function signatures without telling the other
person first. Adding OPTIONAL fields is fine. All values crossing this boundary are plain JSON
(dicts, lists, str, int, float, bool, None) so they can be sent over the Agent Chat Protocol.

Value conventions (also used inside the engine's JSON-lines harness):
  - decimals are strings: "12.34"
  - dates are ISO strings: "2026-02-28"
  - an error/exception result is {"ok": false}; a normal result is {"ok": true, "value": <json>}
"""
from __future__ import annotations

from typing import Literal, Optional, TypedDict

Verdict = Literal["BLOCKED", "QUESTION", "UNPROVEN", "VERIFIED"]
VersionName = Literal["pr", "twin_a", "twin_b"]


class Version(TypedDict):
    name: VersionName          # "pr", "twin_a" or "twin_b"
    code: str                  # full Python module source
    entrypoint: str            # function name to call inside `code`
    model: str                 # model that wrote it, e.g. "meta/<model>", "subq/snap-1.1", "claude-code"
    prompt_hash: Optional[str] # sha256 of the prompt used (None for the PR)


class VerifyRequest(TypedDict, total=False):
    # required
    function_name: str
    spec_text: str             # raw issue/spec text
    versions: list[Version]    # exactly three: pr, twin_a, twin_b
    # optional
    seed: int                  # default 0
    max_examples: int          # default 2000; Fetch side lowers it to fit the ASI:One reply window
    time_budget_s: float       # default 60
    inputs: list[dict]         # bring-your-own function: kwargs dicts (JSON-able), one per call
    pr_ref: str                # e.g. "owner/repo#2" or "mutant#17", shown in the ledger


class Counterexample(TypedDict):
    input: dict                       # kwargs passed to the function (JSON form)
    outputs: dict[str, dict]          # version name -> {"ok": bool, "value": ...}
    vote: str                         # "2-1" or "1-1-1"
    majority: list[str]               # version names in the majority ([] for a 3-way split)


class Question(TypedDict):
    id: str                           # stable id, used by answer_question()
    text: str                         # one precise question for the human
    input: dict
    options: dict[str, dict]          # version name -> output it produced


class RuleResult(TypedDict):
    name: str
    spec_line: Optional[str]          # quoted spec line, or None
    status: Literal["active", "advisory"]
    passed: bool


class Evidence(TypedDict):
    verdict: Verdict
    reason: str                       # one human-readable sentence
    n_inputs: int                     # inputs actually run
    counterexample: Optional[Counterexample]   # set when BLOCKED by vote
    question: Optional[Question]               # set when QUESTION
    rules: list[RuleResult]
    flaky_excluded: int
    regression_tests: int             # saved answered questions checked this run
    seed: int
    timings: dict[str, float]         # e.g. {"total_s": 4.2}
    ledger_path: str                  # path of the full JSON ledger written for this run
    repro_cmd: str                    # exact command to reproduce


class Mutant(TypedDict):
    id: int
    split: Literal["dev", "heldout"]
    operator: str                     # e.g. "flip_comparison"
    description: str                  # e.g. "line 14: '<=' -> '<'"
    code: str                         # full mutated module source
    entrypoint: str


# ---------------------------------------------------------------------------
# Function signatures (implemented in engine/api.py, bench/api.py, twins/api.py)
#
#   engine.api.verify(req: VerifyRequest) -> Evidence                      [ENGINE side]
#   engine.api.answer_question(question_id: str, chosen: str) -> int       [ENGINE side]
#       chosen = a version name ("pr"/"twin_a"/"twin_b"); saves a regression test;
#       returns the new number of saved regression tests.
#   bench.api.get_mutant(n: int) -> Mutant                                 [ENGINE side]
#   bench.api.list_mutants(split: str = "heldout") -> list[int]            [ENGINE side]
#   twins.api.build_twins(spec_text, function_name, signature) -> list[Version]  [FETCH side]
#       returns [twin_a, twin_b]; cached in twins_cache/ by prompt hash.
#
# Until the real implementation lands, each api.py returns fixtures from contract/fixtures/.
# Switch with env var DOPPEL_STUBS=1 (stubs) / DOPPEL_STUBS=0 (real).
# ---------------------------------------------------------------------------
