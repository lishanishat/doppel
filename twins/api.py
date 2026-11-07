"""FETCH side twin API (used by the Twin builder agent; the engine side reads cached twins from
twins_cache/). See contract/types.py.

Stub mode returns two placeholder twins that simply return "0.00", so the engine can test
plumbing. Real mode: generate Twin A (Meta model, normal approach) and Twin B (SubQ Snap 1.1,
deliberately naive brute force) from the raw spec text only, cache them in twins_cache/ with a
header (model, prompt hash, timestamp), and return them.
"""
from __future__ import annotations

from contract import stubs
from contract.types import Version

_PLACEHOLDER = 'def {fn}(**kwargs):\n    return "0.00"\n'


def build_twins(spec_text: str, function_name: str, signature: str) -> list[Version]:
    if stubs.stubs_on():
        code = _PLACEHOLDER.format(fn=function_name)
        return [
            {"name": "twin_a", "code": code, "entrypoint": function_name, "model": "STUB", "prompt_hash": None},
            {"name": "twin_b", "code": code, "entrypoint": function_name, "model": "STUB", "prompt_hash": None},
        ]
    raise NotImplementedError("twins.api.build_twins: real generation not wired in yet")
