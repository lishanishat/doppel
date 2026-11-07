"""Have Meta write pytest tests from the spec only.

Usage: python bench/llm_artifacts/generate_blind_tests.py SPEC.md FUNCTION MODULE_PATH [OUT.py]
MODULE_PATH is the importable module (e.g. demo_target.prorate_refund.reference).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common import llm  # noqa: E402
from twins.generate import extract_code  # noqa: E402

SYSTEM = (
    "You write pytest test suites from a specification alone. Return a single Python test module in "
    "exactly one ```python code block, standard library plus pytest only. No explanation."
)


def main() -> None:
    spec_path, fn, module = sys.argv[1:4]
    out = Path(sys.argv[4]) if len(sys.argv) > 4 else Path(__file__).with_name(f"test_blind_{fn}.py")
    spec = Path(spec_path).read_text()
    user = (
        f"Specification:\n\n{spec}\n\nWrite pytest tests for the function `{fn}`, importing it with "
        f"`from {module} import {fn}`. Cover every rule in the spec, including edge cases and "
        "boundaries. Do not assume anything not stated in the spec."
    )
    text, model = llm.complete("meta", SYSTEM, user)
    out.write_text(f"# model: {model}\n" + extract_code(text))
    print(f"wrote {out} ({model})")


if __name__ == "__main__":
    main()
