import pytest

from agents import commands
from agents.custom import parse_custom

MSG = """@agent1qabc verify custom
spec: Returns the sum of a and b.
Negative numbers allowed.
```python
import math

def add(a: int, b: int = 0) -> int:
    return a + b
```
"""


def test_happy():
    r = parse_custom(MSG)
    assert r.function_name == "add"
    assert r.signature == "def add(a: int, b: int = 0) -> int:"
    assert r.spec_text == "Returns the sum of a and b.\nNegative numbers allowed."
    assert "return a + b" in r.code


def test_no_prefix_spec():
    r = parse_custom("verify custom\nAdds numbers\n```python\ndef f(x):\n    return x\n```")
    assert r.spec_text == "Adds numbers"


def test_errors():
    with pytest.raises(ValueError):
        parse_custom("verify custom\nspec: hi")
    with pytest.raises(ValueError):
        parse_custom("verify custom\nspec: hi\n```python\nx = 1\n```")
    with pytest.raises(ValueError):
        parse_custom("verify custom\n```python\ndef f(x):\n    return x\n```")


def test_commands_parse_multiline():
    c = commands.parse(MSG)
    assert c.kind == "verify_custom"
    assert c.raw == MSG
    assert parse_custom(c.raw).function_name == "add"


def test_existing_unchanged():
    assert commands.parse("verify pr 3").kind == "verify_pr"
    assert commands.parse("hello").kind == "help"
