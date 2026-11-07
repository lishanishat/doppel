"""ENGINE side public API. Owner: engine person. See contract/types.py.

Stub mode (default, DOPPEL_STUBS unset or 1): returns fixtures so the Fetch side can build now.
  DOPPEL_STUB_VERDICT = blocked | question | verified | unproven   (default: blocked)
Real mode (DOPPEL_STUBS=0): replace the NotImplementedError branches with the real Referee.
"""
from __future__ import annotations

import os

from contract import stubs
from contract.types import Evidence, VerifyRequest

_answered: list[dict] = []


def verify(req: VerifyRequest) -> Evidence:
    if stubs.stubs_on():
        ev = stubs.load(os.environ.get("DOPPEL_STUB_VERDICT", "blocked"))
        ev["seed"] = req.get("seed", 0)
        return ev  # type: ignore[return-value]
    raise NotImplementedError("engine.api.verify: real Referee not wired in yet")


def answer_question(question_id: str, chosen: str) -> int:
    if stubs.stubs_on():
        _answered.append({"question_id": question_id, "chosen": chosen})
        return len(_answered)
    raise NotImplementedError("engine.api.answer_question: real regression store not wired in yet")
