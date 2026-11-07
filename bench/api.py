"""ENGINE side mutant API (used by the Fetch side's "Verify mutant #N" command). See contract/types.py.

Real mode (DOPPEL_STUBS=0) reads the seeded mutant cache bench/mutants/prorate_refund.json
(built by `python -m bench.mutate`, auto-built on first use). Stub mode keeps fixture behavior.
"""
from __future__ import annotations

import json

from contract import stubs
from contract.types import Mutant

FUNCTION = "prorate_refund"
_PUBLIC = ("id", "split", "operator", "description", "code", "entrypoint")


def _all(fn: str = FUNCTION) -> list[dict]:
    from bench import mutate
    path = mutate.CACHE_DIR / f"{fn}.json"
    if not path.exists():
        mutate.build_cache(fn)
    return json.loads(path.read_text())


def get_mutant(n: int) -> Mutant:
    if stubs.stubs_on():
        m = stubs.load("mutant")
        m["id"] = n
        return m  # type: ignore[return-value]
    for m in _all():
        if m["id"] == n:
            out = {k: m[k] for k in _PUBLIC}
            out["likely_equivalent"] = m.get("likely_equivalent", False)  # optional extra field
            return out  # type: ignore[return-value]
    raise KeyError(f"no mutant #{n}")


def list_mutants(split: str = "heldout") -> list[int]:
    """Ids in `split` ('dev' | 'heldout' | 'all'). Held-out excludes likely-equivalent mutants."""
    if stubs.stubs_on():
        return list(range(1, 21))
    ms = _all()
    if split == "all":
        return [m["id"] for m in ms]
    ids = [m["id"] for m in ms if m["split"] == split]
    if split == "heldout":
        eq = {m["id"] for m in ms if m.get("likely_equivalent")}
        ids = [i for i in ids if i not in eq]
    return ids
