"""CLAUDE.md section 6, pure and in order. No I/O, no LLM."""
from __future__ import annotations

import hashlib
import json

NAMES = ("pr", "twin_a", "twin_b")


def question_id(inp: dict) -> str:
    return "q-" + hashlib.sha256(json.dumps(inp, sort_keys=True).encode()).hexdigest()[:12]


def _same(a: dict, b: dict) -> bool:
    if not a.get("ok") and not b.get("ok"):
        return True
    return bool(a.get("ok")) == bool(b.get("ok")) and a.get("value") == b.get("value")


def _show(r: dict) -> str:
    return repr(r["value"]) if r.get("ok") else "raises"


def build_question(ce: dict) -> dict:
    o, i = ce["outputs"], ce["input"]
    args = ", ".join(f"{k}={v!r}" for k, v in i.items())
    text = (f"For input ({args}) the three versions return pr={_show(o['pr'])}, "
            f"twin_a={_show(o['twin_a'])}, twin_b={_show(o['twin_b'])}; which answer does the spec intend?")
    return {"id": question_id(i), "text": text, "input": i, "options": {n: o[n] for n in NAMES}}


def decide(referee_result, rule_results, build_errors, scope_error,
           answered=None, regression_failures=None):
    """-> (verdict, reason, counterexample|None, question|None).
    answered: {question_id: {"expected": result, "chosen": name}}; regression_failures: list of
    {"input","expected","got"} from saved regression tests the PR failed."""
    answered, rf = answered or {}, regression_failures or []
    rr = referee_result or {}
    confirmed = rr.get("confirmed", [])
    # 1. PR outvoted 2-1
    for ce in confirmed:
        a = answered.get(question_id(ce["input"]))
        if a and _same(ce["outputs"]["pr"], a["expected"]):
            continue  # a saved spec answer says the PR's output is the intended one
        if ce["vote"] == "2-1" and "pr" not in ce["majority"]:
            return ("BLOCKED", f"PR outvoted 2-1 by {' and '.join(ce['majority'])} on a confirmed input.", ce, None)
    # answered 1-1-1 questions: the saved answer is the expected value
    for ce in confirmed:
        a = answered.get(question_id(ce["input"]))
        if ce["vote"] == "1-1-1" and a and not _same(ce["outputs"]["pr"], a["expected"]):
            ce = dict(ce, majority=[a["chosen"]])
            return ("BLOCKED", f"PR contradicts a previously answered spec question (chose {a['chosen']}).", ce, None)
    if rf:
        return ("BLOCKED", f"PR fails {len(rf)} saved regression test(s).", None, None)
    # 2. active spec-cited rule
    for r in rule_results or []:
        if r["status"] == "active" and not r["passed"]:
            return ("BLOCKED", f"PR breaks spec rule '{r['name']}': {r['spec_line']}", None, None)
    # 3. three-way split -> QUESTION (unless already answered)
    for ce in confirmed:
        if ce["vote"] == "1-1-1" and question_id(ce["input"]) not in answered:
            return ("QUESTION", "All three versions disagree on a confirmed input; the spec is likely ambiguous. Unanswered: not merged.",
                    None, build_question(ce))
    # 4. unproven
    if scope_error:
        return ("UNPROVEN", f"Input out of scope: {scope_error}", None, None)
    if build_errors:
        return ("UNPROVEN", "Version failed to build: " + "; ".join(f"{k}: {v}" for k, v in build_errors.items()), None, None)
    if referee_result is None:
        return ("UNPROVEN", "No referee result.", None, None)
    faults = {k: v for k, v in rr.get("faults", {}).items() if v}
    if faults:
        return ("UNPROVEN", "Version fault(s) (timeout/crash): " + ", ".join(f"{k} x{v}" for k, v in faults.items()), None, None)
    n = rr.get("n_inputs", 0)
    if n <= 0:
        return ("UNPROVEN", "No inputs were run.", None, None)
    return ("VERIFIED", f"VERIFIED on {n} inputs: all versions agree and all active rules hold.", None, None)
