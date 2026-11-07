"""Run: python -m engine.tests.test_referee"""
import time
from pathlib import Path

from engine import referee
from engine.target import load

PH = Path(__file__).parent / "placeholders"


def _versions(t, pr, a, b):
    code = {"ref": t.reference_code}
    for n in ("float_twin", "lenient_twin", "buggy_pr"):
        code[n] = (PH / f"{n}.py").read_text()
    return [{"name": n, "code": code[c], "entrypoint": t.entrypoint, "model": "test", "prompt_hash": None}
            for n, c in (("pr", pr), ("twin_a", a), ("twin_b", b))]


def test_vote():
    ok = {"ok": True, "value": "1"}
    assert referee.vote({"pr": ok, "twin_a": ok, "twin_b": ok}) == ("3-0", ["pr", "twin_a", "twin_b"])
    assert referee.vote({"pr": {"ok": True, "value": "2"}, "twin_a": ok, "twin_b": ok}) == ("2-1", ["twin_a", "twin_b"])
    assert referee.vote({"pr": {"ok": False}, "twin_a": ok, "twin_b": {"ok": True, "value": "3"}}) == ("1-1-1", [])


def test_clean():
    t = load("prorate_refund")
    r = referee.run(t, _versions(t, "ref", "ref", "ref"), max_examples=800, time_budget_s=40)
    print("clean", {k: v for k, v in r.items() if k not in ("samples",)})
    assert r["confirmed"] == [] and r["disagreements"] == 0 and r["flaky"] == 0
    assert r["n_inputs"] > 100 and len(r["samples"]) <= 200 and not any(r["faults"].values())


def test_buggy_pr():
    t = load("prorate_refund")
    t0 = time.time()
    r = referee.run(t, _versions(t, "buggy_pr", "ref", "ref"), max_examples=2000, time_budget_s=40)
    dt = time.time() - t0
    print("buggy", dt, r["timings"], r["n_inputs"], r["disagreements"], r["flaky"], r["confirmed"])
    assert dt < 40 and r["confirmed"]
    c = r["confirmed"][0]
    assert c["vote"] == "2-1" and c["majority"] == ["twin_a", "twin_b"]
    assert set(c["outputs"]["pr"]) <= {"ok", "value"}


def test_twin_disagreements():
    t = load("prorate_refund")
    r = referee.run(t, _versions(t, "ref", "float_twin", "lenient_twin"), max_examples=1500, time_budget_s=40)
    print("twins", r["timings"], r["n_inputs"], r["disagreements"], r["flaky"])
    for c in r["confirmed"]:
        print(" ", c["vote"], c["majority"], c["input"], c["outputs"])
    assert r["confirmed"] and r["disagreements"] > 0
    assert len(r["confirmed"]) <= 5


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
            print("PASS", n)
