"""Run the whole custom-verify path without ASI:One.

  python scripts/custom_check.py FILE                      # live: LLM inputs + live twins
  python scripts/custom_check.py FILE --no-llm --twin-a A.py --twin-b B.py   # offline

FILE is a chat-format request ("verify custom / spec: ... / ```python ... ```").
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, ROOT.as_posix())


def _twin(name: str, path: str, fn: str):
    return {"name": name, "code": Path(path).read_text(), "entrypoint": fn,
            "model": "hand-written", "prompt_hash": None}


def run(path: str, no_llm: bool = False, twin_a: str | None = None, twin_b: str | None = None,
        n: int = 300, max_examples: int = 1000, seed: int = 0, out=print) -> dict:
    from agents import formatting
    from agents.custom import parse_custom

    def step(label, t0):
        out(f"[{time.time() - t0:6.1f}s] {label}")

    text = Path(path).read_text()
    req = parse_custom(text)
    fn = req.function_name
    out(f"parsed: function={fn} signature={req.signature}")

    t0 = time.time()
    if no_llm:
        from engine.inputgen_fallback import typehint_inputs
        inputs = typehint_inputs(req.code, fn, n)
    else:
        from engine.inputgen import generate_inputs
        inputs = generate_inputs(req.spec_text, req.code, fn, n)
    step(f"step 1/3: {len(inputs)} test inputs", t0)

    t0 = time.time()
    if twin_a and twin_b:
        twins = [_twin("twin_a", twin_a, fn), _twin("twin_b", twin_b, fn)]
    elif no_llm:
        raise SystemExit("--no-llm needs --twin-a and --twin-b")
    else:
        from twins.api import build_twins
        twins = build_twins(req.spec_text, fn, req.signature)
    step(f"step 2/3: twins built ({', '.join(t.get('model', '?') for t in twins)})", t0)

    pr = {"name": "pr", "code": req.code, "entrypoint": fn, "model": "user-submitted", "prompt_hash": None}
    vreq = {"function_name": fn, "spec_text": req.spec_text, "versions": [pr, *twins], "seed": seed,
            "max_examples": max_examples, "pr_ref": f"custom:{fn}", "inputs": inputs}
    t0 = time.time()
    from engine.api import verify
    ev = verify(vreq)
    step("step 3/3: compared", t0)

    models = {t["name"]: t.get("model") for t in twins}
    out("")
    out(formatting.verdict_text(ev, models=models))
    return ev


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--no-llm", action="store_true", help="type-hint inputs, twins from files")
    ap.add_argument("--twin-a")
    ap.add_argument("--twin-b")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--max-examples", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    try:
        run(a.file, a.no_llm, a.twin_a, a.twin_b, a.n, a.max_examples, a.seed)
    except ValueError as e:
        print(f"Bad request: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
