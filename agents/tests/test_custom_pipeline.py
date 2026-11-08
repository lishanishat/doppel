import sys
import types
from types import SimpleNamespace

import pytest

from agents import formatting, pipeline


def _fake_custom(monkeypatch, fn):
    mod = types.ModuleType("agents.custom")
    mod.parse_custom = fn
    monkeypatch.setitem(sys.modules, "agents.custom", mod)
    import agents
    monkeypatch.setattr(agents, "custom", mod, raising=False)


def test_prepare_custom_ok(monkeypatch):
    req = SimpleNamespace(spec_text="s", code="def f(a): return a", function_name="f", signature="def f(a)")
    _fake_custom(monkeypatch, lambda t: req)
    p = pipeline.prepare_custom(SimpleNamespace(raw="x"))
    assert p.pr_ref == "custom:f" and p.pr["model"] == "user-submitted" and p.pr["entrypoint"] == "f"
    assert p.repo is None and p.pr_number is None and p.pr["prompt_hash"] is None


def test_prepare_custom_bad(monkeypatch):
    def boom(t):
        raise ValueError("no code block")
    _fake_custom(monkeypatch, boom)
    with pytest.raises(pipeline.UserFacingError, match="no code block"):
        pipeline.prepare_custom(SimpleNamespace(raw="x"))


def test_run_custom_passes_inputs_no_review(monkeypatch):
    from engine import api as engine_api
    seen = {}
    ev = {"verdict": "VERIFIED", "reason": "ok", "n_inputs": 1, "counterexample": None, "question": None,
          "rules": [], "flaky_excluded": 0, "regression_tests": 0, "seed": 0, "timings": {},
          "ledger_path": "", "repro_cmd": ""}
    monkeypatch.setattr(engine_api, "verify", lambda r: seen.update(r) or ev)
    monkeypatch.setattr(pipeline.github_client, "post_review",
                        lambda *a, **k: pytest.fail("must not post"))
    prep = pipeline.Prepared("s", "f", "def f()", SimpleNamespace(), "custom:f", None, None)
    e, text = pipeline.run_custom(prep, [{"name": "twin_a", "model": "m"}], [{"a": 1}], 50)
    assert seen["inputs"] == [{"a": 1}] and e["verdict"] == "VERIFIED" and isinstance(text, str)


def test_run_custom_never_raises(monkeypatch):
    from engine import api as engine_api
    def boom(r):
        raise RuntimeError("x")
    monkeypatch.setattr(engine_api, "verify", boom)
    prep = pipeline.Prepared("s", "f", "def f()", SimpleNamespace(), "custom:f", None, None)
    e, _ = pipeline.run_custom(prep, [], [], 5)
    assert e["verdict"] == "UNPROVEN"


def test_formatting():
    t = formatting.custom_ack_text("f")
    assert t.startswith("Got it.") and "3-5 minutes" in t and "1/3" in t and "2/3" in t and "3/3" in t
    assert formatting.progress_text(1, 3, "hi") == "Step 1/3: hi"
    assert "verify custom" in formatting.help_text() and "verify pr" in formatting.help_text()
