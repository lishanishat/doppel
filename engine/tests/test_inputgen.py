import pytest

from engine import inputgen

CODE = "def f(a: int, b: str = 'x') -> int:\n    return a\n"

GOOD = """```python
def gen(rng):
    return {"a": rng.randint(-50, 50), "b": rng.choice(["", "x", "yy", "z" * rng.randint(0, 30)])}
```"""


def _fb(code, function_name, n=300):
    return [{"a": 0, "b": "fb"}]


@pytest.fixture(autouse=True)
def _patch_fb(monkeypatch):
    import types, sys
    mod = types.ModuleType("engine.inputgen_fallback")
    mod.typehint_inputs = _fb
    monkeypatch.setitem(sys.modules, "engine.inputgen_fallback", mod)
    import engine
    monkeypatch.setattr(engine, "inputgen_fallback", mod, raising=False)


def test_good_llm(monkeypatch):
    monkeypatch.setattr("common.llm.complete", lambda p, s, u, temperature=0.0: (GOOD, "meta/x"))
    out = inputgen.generate_inputs("spec", CODE, "f", n=100)
    assert 20 <= len(out) <= 100
    assert all(set(r) == {"a", "b"} for r in out)
    assert len({repr(sorted(r.items())) for r in out}) == len(out)


def test_llm_failure_falls_back(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("no key")
    monkeypatch.setattr("common.llm.complete", boom)
    assert inputgen.generate_inputs("spec", CODE, "f") == [{"a": 0, "b": "fb"}]


def test_bad_keys_and_few_inputs_fall_back(monkeypatch):
    bad = "```python\ndef gen(rng):\n    return {'wrong': 1}\n```"
    monkeypatch.setattr("common.llm.complete", lambda *a, **k: (bad, "m"))
    assert inputgen.generate_inputs("spec", CODE, "f")[0]["b"] == "fb"
    crash = "```python\ndef gen(rng):\n    raise ValueError()\n```"
    monkeypatch.setattr("common.llm.complete", lambda *a, **k: (crash, "m"))
    assert inputgen.generate_inputs("spec", CODE, "f")[0]["b"] == "fb"


def test_missing_function():
    with pytest.raises(ValueError):
        inputgen.generate_inputs("spec", CODE, "nope")
