"""Recovery: a version whose process dies mid-run must yield UNPROVEN (never VERIFIED or BLOCKED)."""
import os
from pathlib import Path

import pytest

from engine.chaos import inject_kill

ROOT = Path(__file__).resolve().parent.parent.parent
FN = "prorate_refund"


def _versions():
    spec = (ROOT / "demo_target" / FN / "spec.md").read_text()
    code = {
        "pr": (ROOT / "demo_target" / FN / "ai_pr" / "billing.py").read_text(),
        "twin_a": (ROOT / "twins_cache" / FN / "twin_a.py").read_text(),
        "twin_b": (ROOT / "twins_cache" / FN / "twin_b.py").read_text(),
    }
    return spec, code


def _verify(code, spec):
    os.environ["DOPPEL_STUBS"] = "0"
    from engine import api
    vs = [{"name": n, "code": c, "entrypoint": FN, "model": "test", "prompt_hash": None} for n, c in code.items()]
    return api.verify({"function_name": FN, "spec_text": spec, "versions": vs, "max_examples": 300, "seed": 0})


def test_control_without_chaos_is_verified():
    spec, code = _versions()
    assert _verify(code, spec)["verdict"] == "VERIFIED"


@pytest.mark.parametrize("victim", ["pr", "twin_a", "twin_b"])
def test_killed_process_gives_unproven_with_plain_reason(victim):
    spec, code = _versions()
    code[victim] = inject_kill(code[victim], FN)
    ev = _verify(code, spec)
    assert ev["verdict"] == "UNPROVEN", ev["reason"]
    assert victim in ev["reason"] and "crash" in ev["reason"].lower()
    assert ev["counterexample"] is None
