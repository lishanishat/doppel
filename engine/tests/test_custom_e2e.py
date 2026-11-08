"""Offline e2e for scripts/custom_check.py. I1/I2b/I3 may not exist yet: they are stubbed."""
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQ = """verify custom
spec: add_clamped returns a+b clamped to the range 0..100.
```python
def add_clamped(a: int, b: int) -> int:
    return max(0, min(100, a + b))
```
"""
TWIN = "def add_clamped(a, b):\n    return min(100, max(0, a + b))\n"


def _load():
    spec = importlib.util.spec_from_file_location("custom_check", ROOT / "scripts" / "custom_check.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _stub_modules(monkeypatch, captured):
    code = REQ.split("```python\n")[1].split("```")[0]
    cr = types.SimpleNamespace(spec_text="add_clamped returns a+b clamped to the range 0..100.", code=code,
                               function_name="add_clamped", signature="def add_clamped(a: int, b: int) -> int:")
    cust = types.ModuleType("agents.custom")
    cust.parse_custom = lambda text: cr
    fb = types.ModuleType("engine.inputgen_fallback")
    fb.typehint_inputs = lambda code, fn, n=300: [{"a": i, "b": 50} for i in range(5)]
    monkeypatch.setitem(sys.modules, "agents.custom", cust)
    monkeypatch.setitem(sys.modules, "engine.inputgen_fallback", fb)
    import engine.api

    def fake_verify(req):
        captured["req"] = req
        return {"verdict": "VERIFIED", "reason": "", "n_inputs": len(req["inputs"]), "counterexample": None,
                "question": None, "rules": [], "timings": {}}
    monkeypatch.setattr(engine.api, "verify", fake_verify)


def test_offline_run(monkeypatch, tmp_path, capsys):
    f = tmp_path / "req.txt"
    f.write_text(REQ)
    a, b = tmp_path / "a.py", tmp_path / "b.py"
    a.write_text(TWIN)
    b.write_text(TWIN)
    cap = {}
    _stub_modules(monkeypatch, cap)
    mod = _load()
    rc = mod.main([str(f), "--no-llm", "--twin-a", str(a), "--twin-b", str(b)])
    out = capsys.readouterr().out
    assert rc == 0
    req = cap["req"]
    assert [v["name"] for v in req["versions"]] == ["pr", "twin_a", "twin_b"]
    assert req["inputs"] == [{"a": i, "b": 50} for i in range(5)]
    assert req["function_name"] == "add_clamped"
    assert "step 1/3" in out and "step 3/3" in out and "VERIFIED on 5 inputs" in out


def test_no_llm_requires_twins(monkeypatch, tmp_path):
    import pytest
    f = tmp_path / "req.txt"
    f.write_text(REQ)
    _stub_modules(monkeypatch, {})
    with pytest.raises(SystemExit):
        _load().main([str(f), "--no-llm"])
