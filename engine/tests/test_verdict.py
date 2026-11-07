"""Unit tests for pure verdict/rules/ledger/regression logic. Run: python -m engine.tests.test_verdict"""
import json
import tempfile
from pathlib import Path

from engine import ledger, regression, rules, verdict


def ok(v):
    return {"ok": True, "value": v}


RAISE = {"ok": False}
INP = {"price": "30.00", "period_start": "2026-04-01", "period_end": "2026-05-01", "cancel_date": "2026-04-16"}


def rr(confirmed=(), faults=None, n=100):
    return {"n_inputs": n, "disagreements": len(confirmed), "confirmed": list(confirmed), "flaky": 0,
            "faults": faults or {}, "samples": [], "timings": {}}


def ce(vote, outs, maj):
    return {"input": INP, "outputs": dict(zip(("pr", "twin_a", "twin_b"), outs)), "vote": vote, "majority": maj}


def active(name="r", passed=True):
    return {"name": name, "spec_line": "x", "status": "active", "passed": passed}


def test_decide():
    d = verdict.decide
    assert d(rr([ce("2-1", [ok("1.00"), ok("2.00"), ok("2.00")], ["twin_a", "twin_b"])]), [], {}, None)[0] == "BLOCKED"
    assert d(rr([ce("2-1", [ok("2.00"), ok("2.00"), ok("1.00")], ["pr", "twin_a"])]), [], {}, None)[0] == "VERIFIED"
    v = d(rr(), [active(passed=False)], {}, None)
    assert v[0] == "BLOCKED" and "r" in v[1]
    assert d(rr(), [{**active(passed=False), "status": "advisory"}], {}, None)[0] == "VERIFIED"
    three = ce("1-1-1", [ok("15.00"), ok("14.00"), ok("15.50")], [])
    v = d(rr([three]), [], {}, None)
    assert v[0] == "QUESTION" and v[3]["id"] == verdict.question_id(INP)
    for s in ("15.00", "14.00", "15.50"):
        assert repr(s) in v[3]["text"]
    assert d(rr(), [], {"twin_a": "syntax"}, None)[0] == "UNPROVEN"
    assert d(None, [], {}, "bad fn")[0] == "UNPROVEN"
    assert d(rr(faults={"twin_b": 2}), [], {}, None)[0] == "UNPROVEN"
    v = d(rr(n=77), [active()], {}, None)
    assert v[0] == "VERIFIED" and "77" in v[1] and "proven" not in v[1].lower()
    # saved answer applied
    qid = verdict.question_id(INP)
    ans = {qid: {"expected": ok("14.00"), "chosen": "twin_a"}}
    assert d(rr([three]), [], {}, None, answered=ans)[0] == "BLOCKED"
    ans = {qid: {"expected": ok("15.00"), "chosen": "pr"}}
    assert d(rr([three]), [], {}, None, answered=ans)[0] == "VERIFIED"
    assert d(rr(), [], {}, None, regression_failures=[{"input": INP}])[0] == "BLOCKED"
    # saved answer choosing the PR's output overrides a later 2-1 against the PR on that input
    two = ce("2-1", [ok("15.00"), ok("14.00"), ok("14.00")], ["twin_a", "twin_b"])
    assert d(rr([two]), [], {}, None, answered=ans)[0] == "VERIFIED"
    # unquoted rule -> advisory, not a crash
    r = rules.evaluate("prorate_refund", [{"input": INP, "outputs": {n: ok("99.00") for n in ("pr", "twin_a", "twin_b")}}], spec="")
    assert all(x["status"] == "advisory" and x["spec_line"] is None for x in r)


def test_rules():
    spec = rules.spec_text("prorate_refund")
    for r in rules.RULES["prorate_refund"]:
        assert r.spec_line in spec
    bad = {**INP, "price": "1.005"}
    samples = [
        {"input": INP, "outputs": {"pr": ok("-1.00"), "twin_a": ok("15.00"), "twin_b": ok("15.00")}},
        {"input": bad, "outputs": {"pr": ok("1.01"), "twin_a": RAISE, "twin_b": RAISE}},
        {"input": INP, "outputs": {"pr": ok("15"), "twin_a": ok("15.00"), "twin_b": ok("15.00")}},
    ]
    res = {r["name"]: r for r in rules.evaluate("prorate_refund", samples)}
    assert len(res) == 3 and all(r["status"] == "active" and not r["passed"] for r in res.values())
    # all versions break rule -> advisory
    s2 = [{"input": INP, "outputs": {n: ok("99.00") for n in ("pr", "twin_a", "twin_b")}}]
    r = {x["name"]: x for x in rules.evaluate("prorate_refund", s2)}
    assert r["never_negative_or_above_price"]["status"] == "advisory"
    assert rules.is_valid_input(INP) and not rules.is_valid_input({**INP, "cancel_date": "2026-05-02"})
    assert not rules.is_valid_input({**INP, "period_end": "2026-04-01"})


def test_ledger_regression():
    with tempfile.TemporaryDirectory() as t:
        ledger.LEDGERS = Path(t)
        p = ledger.write("x", {"a": 1})
        assert json.loads(Path(p).read_text()) == {"a": 1}
        regression.REG = Path(t) / "regression.json"
        regression.PENDING = Path(t) / "questions.json"
        q = verdict.build_question(ce("1-1-1", [ok("15.00"), ok("14.00"), ok("15.50")], []))
        regression.add_pending(q, "prorate_refund")
        assert regression.answer(q["id"], "twin_a") == 1
        assert regression.answer(q["id"], "twin_a") == 1  # idempotent
        assert regression.answered("prorate_refund")[q["id"]]["expected"] == ok("14.00")

        class R:
            def __init__(s, v): s.v = v
            def call(s, kw): return ok(s.v)
        assert regression.check("prorate_refund", R("14.00")) == (1, 0)
        assert regression.check("prorate_refund", R("15.00")) == (1, 1)


if __name__ == "__main__":
    test_decide()
    test_rules()
    test_ledger_regression()
    print("test_verdict: all passed")
