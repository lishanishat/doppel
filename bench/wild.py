"""Real-AI-code study: run Doppel and the baselines on independent AI implementations of the spec.

  python -m bench.wild IMPL_DIR [IMPL_DIR ...]      (each dir has billing.py + test_billing.py, written by a fresh
                                                    coding agent from the issue text only; MODELS.txt maps dir -> model)
Ground truth = demo_target/<fn>/reference.py on 3000 schema inputs (seeded). Writes docs/WILD.md. Only measured numbers.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path

os.environ["DOPPEL_STUBS"] = "0"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
FN = "prorate_refund"

from bench import baselines, mutate  # noqa: E402


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return getattr(m, FN)


def _run(f, kw):
    try:
        return ("ok", f(**kw))
    except Exception:
        return ("err",)


def main(dirs: list[str]) -> int:
    from engine.api import verify
    ref_code = (ROOT / "demo_target" / FN / "reference.py").read_text()
    ref = _load(ROOT / "demo_target" / FN / "reference.py", "ref")
    inputs = mutate.fuzz_inputs(FN, 3000, 0)
    spec = (ROOT / "demo_target" / FN / "spec.md").read_text()
    twins = {n: (ROOT / "twins_cache" / FN / f"{n}.py").read_text() for n in ("twin_a", "twin_b")}
    twin_models = {n: (twins[n].splitlines()[0].replace("# model: ", "")) for n in twins}
    blind = baselines.find_tests(baselines.LLM_TEST_DIR)
    models = {}
    for d in dirs:
        mf = Path(d).parent / "MODELS.txt"
        if mf.exists():
            for line in mf.read_text().splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    models[k.strip()] = v.strip()
    rows = []
    for d in dirs:
        d = Path(d)
        code = (d / "billing.py").read_text()
        impl = _load(d / "billing.py", f"impl_{d.name}")
        mism = [kw for kw in inputs if _run(impl, kw) != _run(ref, kw)]
        vs = [{"name": "pr", "code": code, "entrypoint": FN, "model": models.get(d.name, "?"), "prompt_hash": None}] + [
            {"name": n, "code": c, "entrypoint": FN, "model": twin_models[n], "prompt_hash": None} for n, c in twins.items()]
        t = time.time()
        ev = verify({"function_name": FN, "spec_text": spec, "versions": vs, "max_examples": 1000, "seed": 0})
        secs = time.time() - t
        own = baselines.run_tests(code, baselines.find_tests(d), valid_on=ref_code)
        bl = baselines.run_tests(code, blind, valid_on=ref_code) if blind else {"caught": None}
        ce = ev.get("counterexample")
        rows.append({"impl": d.name, "model": models.get(d.name, "?"), "buggy_vs_reference": len(mism),
                     "example_mismatch": mism[0] if mism else None,
                     "example_outputs": ({"impl": _run(impl, mism[0]), "reference": _run(ref, mism[0])} if mism else None),
                     "doppel": ev["verdict"], "doppel_reason": ev["reason"], "doppel_secs": round(secs, 2),
                     "counterexample": ce["input"] if ce else None,
                     "own_tests_caught": own["caught"], "own_tests_detail": own["detail"],
                     "blind_tests_caught": bl["caught"]})
        print(rows[-1]["impl"], rows[-1]["model"], "mismatches:", rows[-1]["buggy_vs_reference"], "| doppel:", ev["verdict"],
              "| own tests caught:", own["caught"], "| blind caught:", bl["caught"], flush=True)
    (ROOT / "bench" / "wild" / "results.json").write_text(json.dumps(rows, indent=1, default=str))
    L = ["# Real AI code study (measured)", "",
         f"Independent implementations of the spec (issue #1), each written by a fresh coding agent from the issue text only, "
         f"with its own tests. Ground truth: `reference.py` on 3000 seeded schema inputs. Twins: {twin_models['twin_a']} and "
         f"{twin_models['twin_b']}. Raw data: `bench/wild/results.json`. Command: `python -m bench.wild bench/wild/impl_*`.", "",
         "| Impl | Written by | Differs from reference on | Doppel | Own tests flag a bug | Blind tests flag a bug |",
         "|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['impl']} | {r['model']} | {r['buggy_vs_reference']}/3000 inputs | **{r['doppel']}** ({r['doppel_secs']}s) | "
                 f"{'yes' if r['own_tests_caught'] else 'no'} | {'yes' if r['blind_tests_caught'] else 'no'} |")
    L += ["", "## Details", ""]
    for r in rows:
        L.append(f"- **{r['impl']}**: Doppel says {r['doppel']}: {r['doppel_reason']}")
        if r["example_mismatch"]:
            L.append(f"  - First input where it differs from the reference: `{json.dumps(r['example_mismatch'])}` -> "
                     f"impl {r['example_outputs']['impl']}, reference {r['example_outputs']['reference']}")
    L += ["", "A baseline test only counts if it also passes on the correct reference. \"Differs from reference\" is ground truth "
          "(our hand-written reference), not Doppel's opinion; if an implementation differs only where the spec is silent, "
          "that is noted above rather than called a bug."]
    (ROOT / "docs" / "WILD.md").write_text("\n".join(L) + "\n")
    print("wrote docs/WILD.md")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
