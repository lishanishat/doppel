"""Load a demo target by function name: demo_target/<fn>/{spec.md, reference.py, schema.py}."""
import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Target:
    spec_text: str
    reference_code: str
    entrypoint: str
    strategy: Any  # Hypothesis strategy of kwargs dicts


def load(fn: str) -> Target:
    d = ROOT / "demo_target" / fn
    schema = importlib.import_module(f"demo_target.{fn}.schema")
    return Target(
        spec_text=(d / "spec.md").read_text(),
        reference_code=(d / "reference.py").read_text(),
        entrypoint=schema.FUNCTION_NAME,
        strategy=schema.inputs(),
    )
