import re
from pathlib import Path

import pytest

from common import llm
from twins import generate, prompts

SPEC, SIG = "Refund prorated.", "def f(x: int) -> str"


def _fake(calls):
    def complete(provider, system, user, temperature=0.0):
        calls.append((provider, temperature))
        return f"blah\n```python\ndef f(x):\n    return '{provider}'\n```\nbye", f"{provider}/m"
    return complete


def test_extract_code():
    assert generate.extract_code("a\n```python\nx=1\n```\nb") == "x=1\n"
    assert generate.extract_code("x=1") == "x=1\n"
    assert generate.extract_code("```\nshort\n```\n```python\nlonger=1\n```") == "longer=1\n"


def test_header_cache_and_manifest(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(llm, "complete", _fake(calls))
    v = generate.generate_twins(SPEC, "f", SIG, tmp_path)
    assert [x["name"] for x in v] == ["twin_a", "twin_b"] and len(calls) == 2
    src = (tmp_path / "f" / "twin_a.py").read_text()
    assert re.match(r"# model: meta/m\n# prompt_sha256: [0-9a-f]{64}\n# generated_utc: \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ\n", src)
    assert (tmp_path / "f" / "manifest.json").exists()
    v2 = generate.generate_twins(SPEC, "f", SIG, tmp_path)  # cached
    assert len(calls) == 2 and v2 == v
    generate.generate_twins(SPEC + " changed", "f", SIG, tmp_path)  # new prompt -> regenerate
    assert len(calls) == 4


def test_subq_failure_falls_back_to_meta(tmp_path, monkeypatch):
    calls = []

    def complete(provider, system, user, temperature=0.0):
        calls.append((provider, temperature))
        if provider == "subq":
            raise RuntimeError("down")
        return "```python\ndef f(x): return 'm'\n```", "meta/real"
    monkeypatch.setattr(llm, "complete", complete)
    a, b = generate.generate_twins(SPEC, "f", SIG, tmp_path)
    assert calls == [("meta", 0.0), ("subq", 0.0), ("meta", 0.7)]
    assert b["model"] == "meta/real"
    assert "meta/real" in (tmp_path / "f" / "manifest.json").read_text()


def test_prompts_contain_only_spec_and_signature():
    for fn in (prompts.twin_a_prompt, prompts.twin_b_prompt):
        s, u = fn(SPEC, SIG)
        assert SPEC in u and SIG in u
