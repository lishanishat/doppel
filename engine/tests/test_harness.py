"""Run: python -m engine.tests.test_harness"""
import time
from pathlib import Path

from engine import protocol
from engine.harness import BuildError, Runner
from engine.target import load

PH = Path(__file__).parent / "placeholders"
OK_ARGS = {"price": "30.00", "period_start": "2026-01-01", "period_end": "2026-01-31",
           "cancel_date": "2026-01-11"}


def test_normal_and_reference():
    t = load("prorate_refund")
    assert t.entrypoint == "prorate_refund" and "def prorate_refund" in t.reference_code
    with Runner("ref", t.reference_code, t.entrypoint) as r:
        assert r.call(OK_ARGS) == {"ok": True, "value": "20.00"}
        assert r.call({**OK_ARGS, "price": "1.005"}) == {"ok": False}
    for name in ("float_twin", "inclusive_twin", "buggy_pr"):
        with Runner(name, (PH / f"{name}.py").read_text(), t.entrypoint) as r:
            assert r.call(OK_ARGS)["ok"] is True
            assert r.call({**OK_ARGS, "cancel_date": "2027-01-01"}) == {"ok": False}
            assert r.call({**OK_ARGS, "period_start": "2026/01/01"}) == {"ok": False}
    with Runner("bug", (PH / "buggy_pr.py").read_text(), t.entrypoint) as r:
        assert r.call(OK_ARGS)["value"] != "20.00"
    with Runner("inc", (PH / "inclusive_twin.py").read_text(), t.entrypoint) as r:
        assert r.call(OK_ARGS)["value"] != "20.00"


def test_raised():
    with Runner("r", "def f(x):\n    raise RuntimeError('boom')\n", "f") as r:
        assert r.call({"x": 1}) == {"ok": False}
        assert r.call({"x": 1}) == {"ok": False}


def test_timeout_restart():
    code = "def f(x):\n    while x == 0:\n        pass\n    return x\n"
    with Runner("t", code, "f", timeout_s=0.5) as r:
        t0 = time.time()
        assert r.call({"x": 0}) == {"ok": False, "error": "timeout"}
        assert time.time() - t0 < 3
        assert r.call({"x": 5}) == {"ok": True, "value": 5}


def test_crash_restart():
    code = "import os\ndef f(x):\n    if x == 0:\n        os._exit(3)\n    return x\n"
    with Runner("c", code, "f") as r:
        assert r.call({"x": 0}) == {"ok": False, "error": "crash"}
        assert r.call({"x": 2}) == {"ok": True, "value": 2}


def test_print_in_user_code():
    code = "import sys\nprint('module noise')\ndef f(x):\n    print('hello')\n    sys.stdout.write('{\"ok\": true}\\n')\n    return x\n"
    with Runner("p", code, "f") as r:
        assert r.call({"x": 7}) == {"ok": True, "value": 7}
        assert r.call({"x": 8}) == {"ok": True, "value": 8}


def test_build_error():
    for code, ep in [("def f(:\n", "f"), ("def g(x): return x\n", "f"), ("raise ValueError('x')\n", "f")]:
        try:
            Runner("b", code, ep)
        except BuildError as e:
            assert e.name == "b"
        else:
            raise AssertionError("expected BuildError")


def test_protocol():
    from decimal import Decimal
    from datetime import date
    assert protocol.normalize({"a": [Decimal("1E+2"), date(2026, 1, 2), 1.5, " x "]}) == \
        {"a": ["100", "2026-01-02", "1.5", "x"]}
    assert protocol.same({"ok": False}, {"ok": False, "error": "x"})
    assert not protocol.same({"ok": True, "value": "1"}, {"ok": False})
    assert protocol.key({"ok": True, "value": "1"}) == protocol.key({"ok": True, "value": "1"})


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
            print("ok", n)
    print("all passed")
