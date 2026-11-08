import json

import pytest

from engine.inputgen_fallback import typehint_inputs

CODE = '''
def f(count: int, ratio: float, label: str, flag: bool, xs: list[int],
      m: dict[str, int], t: tuple, o: Optional[int] = None, start: str = "2024-01-01"):
    pass
'''


def test_types():
    ins = typehint_inputs(CODE, "f", 100)
    assert 50 < len(ins) <= 100
    for d in ins:
        assert set(d) == {"count", "ratio", "label", "flag", "xs", "m", "t", "o", "start"}
        assert isinstance(d["count"], int) and isinstance(d["ratio"], float)
        assert isinstance(d["label"], str) and isinstance(d["flag"], bool)
        assert all(isinstance(x, int) for x in d["xs"]) and isinstance(d["m"], dict)
        assert d["o"] is None or isinstance(d["o"], int)
    json.dumps(ins)
    assert any(d["o"] is None for d in ins)


def test_name_heuristics():
    code = "def g(start_date: str, price: str, name: str, n: int): pass"
    ins = typehint_inputs(code, "g", 200)
    dates = {d["start_date"] for d in ins}
    assert "2024-02-29" in dates and all(len(x) == 10 for x in dates)
    assert "0.00" in {d["price"] for d in ins}
    assert "" in {d["name"] for d in ins}
    assert all(d["n"] >= 0 for d in ins) and 0 in {d["n"] for d in ins}


def test_unannotated_deterministic_dedupe():
    code = "def h(a, b=3): pass"
    x = typehint_inputs(code, "h", 50)
    assert x == typehint_inputs(code, "h", 50)
    keys = [json.dumps(d, sort_keys=True) for d in x]
    assert len(keys) == len(set(keys))
    assert any(d["b"] == 3 for d in x)


def test_missing_function():
    with pytest.raises(ValueError):
        typehint_inputs("def a(): pass", "b")


def test_no_params():
    assert typehint_inputs("def a(): pass", "a") == [{}]
