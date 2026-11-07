"""python -m engine.cli verify --fn prorate_refund --pr PATH [--twin-a P --twin-b P] [--seed 0 --max-examples 2000]"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDERS = ROOT / "engine" / "tests" / "placeholders"


def _twin(arg, fn, which):
    if arg:
        return Path(arg), "cli-file"
    cached = ROOT / "twins_cache" / fn / f"{which}.py"
    if cached.exists():
        return cached, "twins_cache"
    return PLACEHOLDERS / ("lenient_twin.py" if which == "twin_a" else "float_twin.py"), "placeholder"


def summary(ev: dict) -> str:
    L = [f"== {ev['verdict']} == {ev['reason']}"]
    ce, q = ev.get("counterexample"), ev.get("question")
    src = ce or (q and {"input": q["input"], "outputs": q["options"], "vote": "1-1-1", "majority": []})
    if src:
        L.append("input: " + json.dumps(src["input"]))
        o = src["outputs"]
        L.append("  ".join(f"{n}={json.dumps(o[n].get('value') if o[n].get('ok') else 'RAISES')}" for n in o))
        L.append(f"vote {src['vote']}" + (f", winner: {' + '.join(src['majority'])}" if src["majority"] else ""))
    if q:
        L.append("ask: " + q["text"])
    L.append(f"inputs={ev['n_inputs']} flaky={ev['flaky_excluded']} regressions={ev['regression_tests']} "
             f"time={ev['timings'].get('total_s')}s")
    L.append("ledger: " + ev["ledger_path"])
    L.append("repro:  " + ev["repro_cmd"])
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="engine.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--fn", required=True)
    v.add_argument("--pr", required=True)
    v.add_argument("--twin-a")
    v.add_argument("--twin-b")
    v.add_argument("--seed", type=int, default=0)
    v.add_argument("--max-examples", type=int, default=2000)
    v.add_argument("--time-budget", type=float, default=60)
    a = ap.parse_args(argv)
    os.environ["DOPPEL_STUBS"] = "0"
    sys.path.insert(0, str(ROOT))
    from engine import api
    from engine.target import load
    try:
        tgt = load(a.fn)
        spec, entry = tgt.spec_text, tgt.entrypoint
    except Exception:
        spec, entry = "", a.fn
    pa, ta = _twin(a.twin_a, a.fn, "twin_a")
    pb, tb = _twin(a.twin_b, a.fn, "twin_b")
    mk = lambda name, p, model, ph: {"name": name, "code": Path(p).read_text(), "entrypoint": entry, "model": model, "prompt_hash": ph}
    req = {"function_name": a.fn, "spec_text": spec, "seed": a.seed, "max_examples": a.max_examples,
           "time_budget_s": a.time_budget, "pr_ref": str(a.pr),
           "versions": [mk("pr", a.pr, "claude-code", None), mk("twin_a", pa, ta, None), mk("twin_b", pb, tb, None)]}
    ev = api.verify(req)
    print(json.dumps(ev, indent=2))
    print()
    print(summary(ev))
    return 0


if __name__ == "__main__":
    sys.exit(main())
