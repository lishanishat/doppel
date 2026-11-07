#!/usr/bin/env python
"""Plant one mutation at a chosen line of a PR file and run Doppel on it (for "judge picks a line" demos).

  python scripts/plant_bug.py FILE --list                      # show every plantable site, by line
  python scripts/plant_bug.py FILE LINE OPERATOR [--variant N] [--notes docs/live_bug_notes.md]

OPERATOR: flip_comparison | swap_arith | off_by_one_const | remove_check | swap_rounding
LINE is the line number in FILE as written. The mutated file is rebuilt with ast.unparse, so only its
behaviour (not its formatting) is compared. Uses the real engine and the cached twins.
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["DOPPEL_STUBS"] = "0"

from bench import mutate  # noqa: E402


def sites_for(code: str):
    tree = ast.parse(code)
    out = []
    for s in mutate._sites(tree):
        m = re.match(r"line (\d+):", s[3])
        out.append((int(m.group(1)) if m else 0, s))
    return tree, out


def run(code: str, fn: str):
    from engine.api import verify
    spec = (ROOT / "demo_target" / fn / "spec.md").read_text()
    twins = {n: (ROOT / "twins_cache" / fn / f"{n}.py").read_text() for n in ("twin_a", "twin_b")}
    vs = [{"name": "pr", "code": code, "entrypoint": fn, "model": "planted", "prompt_hash": None}] + [
        {"name": n, "code": c, "entrypoint": fn, "model": "cached", "prompt_hash": None} for n, c in twins.items()]
    t = time.time()
    ev = verify({"function_name": fn, "spec_text": spec, "versions": vs, "max_examples": 300, "seed": 0})
    return ev, time.time() - t


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("line", nargs="?", type=int)
    ap.add_argument("operator", nargs="?")
    ap.add_argument("--variant", type=int, default=0, help="which variant at that site (default 0)")
    ap.add_argument("--fn", default="prorate_refund")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--notes", help="append the result to this markdown file")
    a = ap.parse_args()
    code = Path(a.file).read_text()
    tree, sites = sites_for(code)
    if a.list or a.line is None:
        for ln, s in sorted(sites, key=lambda x: x[0]):
            print(f"line {ln:>3}  {s[0]:<17} {s[3].split(': ', 1)[1]}")
        return 0
    match = [s for ln, s in sites if ln == a.line and s[0] == a.operator]
    if not match:
        print(f"No {a.operator} site on line {a.line}. Run with --list.", file=sys.stderr)
        return 2
    site = match[min(a.variant, len(match) - 1)]
    mutated = ast.unparse(mutate._apply(tree, site)) + "\n"
    if "ROUND_" in site[3]:  # make the replacement rounding name importable
        mutated = mutated.replace("from decimal import", f"from decimal import {site[3].split('-> ')[1]},", 1)
    ev, secs = run(mutated, a.fn)
    ce = ev.get("counterexample")
    line = f"| {Path(a.file).name}:{a.line} | {a.operator} | {site[3].split(': ', 1)[1]} | **{ev['verdict']}** | {secs:.1f}s |"
    print(line.replace("|", " ").strip())
    print(f"{ev['verdict']}: {ev['reason']}")
    if ce:
        print("counterexample:", ce["input"], {k: v.get("value", "err") for k, v in ce["outputs"].items()}, ce["vote"])
    if a.notes:
        p = Path(a.notes)
        if not p.exists():
            p.write_text("# Live bug plants (measured)\n\nEach row is one mutation planted with `scripts/plant_bug.py` on the AI-written PR file "
                         "and verified with the real engine and cached twins. Misses are listed too.\n\n"
                         "| Plant | Operator | Change | Verdict | Time |\n|---|---|---|---|---|\n")
        with p.open("a") as f:
            f.write(line + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
