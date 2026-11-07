"""Fixture loader used by the stub implementations. Stubs are on unless DOPPEL_STUBS=0."""
from __future__ import annotations

import json
import os
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def stubs_on() -> bool:
    return os.environ.get("DOPPEL_STUBS", "1") != "0"


def load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text())
