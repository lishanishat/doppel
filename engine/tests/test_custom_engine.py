import os

os.environ["DOPPEL_STUBS"] = "0"
from engine import api, protocol  # noqa: E402

INPUTS = [{"x": x, "lo": lo, "hi": hi} for x in range(-6, 7, 2) for lo in (-3, 0, 2) for hi in (3, 5)]
PR = "def clamp(x, lo, hi):\n    return max(lo, min(x, hi))\n"
BUGGY = "def clamp(x, lo, hi):\n    return max(lo, min(x, hi - 1))\n"
TWIN_A = "def clamp(x, lo, hi):\n    return lo if x < lo else hi if x > hi else x\n"
TWIN_B = "def clamp(x, lo, hi):\n    return sorted([lo, x, hi])[1]\n"
CRASH = ("_n = 0\ndef clamp(x, lo, hi):\n    global _n\n    _n += 1\n    if _n > 5:\n        import os\n        os._exit(1)\n"
         "    return max(lo, min(x, hi))\n")


def _req(fn, ep, pr, a, b, inputs=INPUTS):
    vs = [{"name": n, "code": c, "entrypoint": ep, "model": "t", "prompt_hash": None}
          for n, c in (("pr", pr), ("twin_a", a), ("twin_b", b))]
    return {"function_name": fn, "spec_text": "clamp x into [lo, hi]", "versions": vs, "inputs": inputs,
            "max_examples": 200, "time_budget_s": 30}


def test_verified():
    assert api.verify(_req("clamp", "clamp", PR, TWIN_A, TWIN_B))["verdict"] == "VERIFIED"


def test_blocked():
    ev = api.verify(_req("clamp", "clamp", BUGGY, TWIN_A, TWIN_B))
    assert ev["verdict"] == "BLOCKED" and ev["counterexample"]


def test_crash_unproven():
    ev = api.verify(_req("clamp", "clamp", PR, CRASH, TWIN_B))
    assert ev["verdict"] == "UNPROVEN", ev


def test_list_return():
    pr = "def evens(n):\n    return [i for i in range(n) if i % 2 == 0]\n"
    a = "def evens(n):\n    return list(range(0, n, 2))\n"
    b = "def evens(n):\n    return [i * 2 for i in range((n + 1) // 2)]\n"
    ins = [{"n": n} for n in range(0, 12)]
    assert api.verify(_req("evens", "evens", pr, a, b, ins))["verdict"] == "VERIFIED"
    bad = pr.replace("i % 2 == 0", "i % 2 == 1")
    assert api.verify(_req("evens", "evens", bad, a, b, ins))["verdict"] == "BLOCKED"


def test_protocol_compare():
    e = protocol.encode_result
    assert protocol.same(e([1, {"a": None}]), e([1, {"a": None}]))
    assert not protocol.same(e([1, 2]), e([1, 3]))
    assert protocol.same(e(0.1 + 0.2), e(0.1 + 0.2)) and not protocol.same(e(0.3), e(0.1 + 0.2))
    assert not protocol.same(e(True), e(False)) and protocol.same({"ok": False}, {"ok": False, "value": 1})
    assert not protocol.same({"ok": False}, e(None))
