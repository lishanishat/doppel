"""ENGINE side mutant API (used by the Fetch side's "Verify mutant #N" command). See contract/types.py."""
from __future__ import annotations

from contract import stubs
from contract.types import Mutant


def get_mutant(n: int) -> Mutant:
    if stubs.stubs_on():
        m = stubs.load("mutant")
        m["id"] = n
        return m  # type: ignore[return-value]
    raise NotImplementedError("bench.api.get_mutant: real seeded mutants not wired in yet")


def list_mutants(split: str = "heldout") -> list[int]:
    if stubs.stubs_on():
        return list(range(1, 21))
    raise NotImplementedError("bench.api.list_mutants: not wired in yet")
