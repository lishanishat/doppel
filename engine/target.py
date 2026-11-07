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


def strategy_for(fn: str):
    """Kwargs strategy from demo_target/<fn>/schema.py: `inputs()`, else the one `*_inputs()` it defines."""
    schema = importlib.import_module(f"demo_target.{fn}.schema")
    if callable(getattr(schema, "inputs", None)):
        return schema.inputs()
    found = [n for n in dir(schema) if n.endswith("_inputs") and callable(getattr(schema, n))]
    if len(found) != 1:
        raise AttributeError(f"demo_target.{fn}.schema: expected inputs() or one *_inputs(), found {found}")
    return getattr(schema, found[0])()


def load(fn: str) -> Target:
    d = ROOT / "demo_target" / fn
    schema = importlib.import_module(f"demo_target.{fn}.schema")
    return Target(
        spec_text=(d / "spec.md").read_text(),
        reference_code=(d / "reference.py").read_text(),
        entrypoint=getattr(schema, "FUNCTION_NAME", fn),
        strategy=strategy_for(fn),
    )
