"""`python -m bench.run_bench` — measure catch rate on held-out, non-equivalent mutants.

Methods: Doppel (engine.api.verify, DOPPEL_STUBS=0), PR's own tests, LLM blind tests.
Writes docs/BENCH.md and docs/bench.png with ONLY measured numbers. Also dumps bench/results.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ["DOPPEL_STUBS"] = "0"

from bench import api, baselines, mutate  # noqa: E402

ROOT = mutate.ROOT
FN = "prorate_refund"


def _twins() -> tuple[str, str, str]:
    cache = ROOT / "twins_cache" / FN
    a, b = cache / "twin_a.py", cache / "twin_b.py"
    if a.exists() and b.exists():
        return a.read_text(), b.read_text(), f"twins_cache/{FN}/ (real twins)"
    ph = ROOT / "engine" / "tests" / "placeholders"
    return ((ph / "lenient_twin.py").read_text(), (ph / "float_twin.py").read_text(),
            "engine/tests/placeholders/lenient_twin.py + float_twin.py (PLACEHOLDER twins; twins_cache absent)")


def _verify(pr_code: str, tag: str, args) -> dict:
    from engine import api as eapi
    ta, tb, _ = _twins()
    spec = (ROOT / "demo_target" / FN / "spec.md").read_text()
    req = {"function_name": FN, "spec_text": spec, "seed": 0, "max_examples": args.max_examples,
           "time_budget_s": args.time_budget, "pr_ref": tag,
           "versions": [
               {"name": "pr", "code": pr_code, "entrypoint": FN, "model": "mutant", "prompt_hash": None},
               {"name": "twin_a", "code": ta, "entrypoint": FN, "model": "placeholder", "prompt_hash": None},
               {"name": "twin_b", "code": tb, "entrypoint": FN, "model": "placeholder", "prompt_hash": None}]}
    t = time.time()
    try:
        ev = eapi.verify(req)
        return {"verdict": ev["verdict"], "reason": ev["reason"], "secs": time.time() - t}
    except Exception as e:  # engine fault; recorded, never silently counted as caught
        return {"verdict": "ERROR", "reason": f"{type(e).__name__}: {e}", "secs": time.time() - t}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-examples", type=int, default=1000)
    ap.add_argument("--time-budget", type=float, default=20)
    ap.add_argument("--skip-doppel", action="store_true")
    args = ap.parse_args(argv)

    all_m = {m["id"]: m for m in json.loads((mutate.CACHE_DIR / f"{FN}.json").read_text())} \
        if (mutate.CACHE_DIR / f"{FN}.json").exists() else {m["id"]: m for m in mutate.build_cache(FN)}
    n_total = len(all_m)
    n_equiv = sum(1 for m in all_m.values() if m["likely_equivalent"])
    heldout = api.list_mutants("heldout")
    n_dev = sum(1 for m in all_m.values() if m["split"] == "dev")
    ref_code = (ROOT / "demo_target" / FN / "reference.py").read_text()

    pr_files = baselines.find_tests(baselines.PR_TEST_DIR)
    llm_files = baselines.find_tests(baselines.LLM_TEST_DIR)
    res = {"heldout_ids": heldout, "rows": {}, "n_total": n_total, "n_equiv": n_equiv, "n_dev": n_dev,
           "twins": _twins()[2], "pr_files": [str(p.relative_to(ROOT)) for p in pr_files],
           "llm_files": [str(p.relative_to(ROOT)) for p in llm_files],
           "max_examples": args.max_examples, "time_budget_s": args.time_budget}

    for mid in heldout:
        m = all_m[mid]
        row = {"description": m["description"], "operator": m["operator"]}
        if not args.skip_doppel:
            row["doppel"] = _verify(m["code"], f"mutant#{mid}", args)
        if pr_files:
            row["pr_tests"] = baselines.run_tests(m["code"], pr_files)
        if llm_files:
            row["llm_tests"] = baselines.run_tests(m["code"], llm_files)
        res["rows"][mid] = row
        print(mid, m["description"], {k: (v.get("verdict") or v.get("status")) for k, v in row.items()
                                       if isinstance(v, dict)}, flush=True)

    if not args.skip_doppel:
        res["false_alarm"] = _verify(ref_code, "reference-as-pr", args)
    if pr_files:
        res["pr_on_reference"] = baselines.run_tests(ref_code, pr_files)
    if llm_files:
        res["llm_on_reference"] = baselines.run_tests(ref_code, llm_files)

    (ROOT / "bench" / "results.json").write_text(json.dumps(res, indent=1))
    summarize(res, args)


def _rate(res, key, caught_fn):
    rows = res["rows"]
    n = len(rows)
    caught = [i for i, r in rows.items() if key in r and caught_fn(r[key])]
    return caught, n


def summarize(res, args):
    rows = res["rows"]
    n = len(rows)
    methods = []  # (label, caught_ids|None, extra)
    if rows and all("doppel" in r for r in rows.values()):
        blocked = [i for i, r in rows.items() if r["doppel"]["verdict"] == "BLOCKED"]
        question = [i for i, r in rows.items() if r["doppel"]["verdict"] == "QUESTION"]
        other = [i for i, r in rows.items() if r["doppel"]["verdict"] not in ("BLOCKED", "QUESTION")]
        methods.append(("Doppel (BLOCKED)", blocked, {"question": question, "other": other}))
    else:
        methods.append(("Doppel", None, None))
    for label, key, files in (("PR's own tests", "pr_tests", res["pr_files"]),
                              ("LLM blind tests", "llm_tests", res["llm_files"])):
        if files:
            c, _ = _rate(res, key, lambda v: v["caught"])
            methods.append((label, c, None))
        else:
            methods.append((label, None, None))

    # chart
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ran = [(l, len(c) / n * 100 if n else 0, len(c)) for l, c, _ in methods if c is not None]
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar([r[0] for r in ran], [r[1] for r in ran], color=["#1f6feb"] + ["#8b949e"] * (len(ran) - 1))
    for b, r in zip(bars, ran):
        ax.text(b.get_x() + b.get_width() / 2, r[1] + 1.5, f"{r[2]}/{n}\n{r[1]:.0f}%", ha="center", fontsize=10)
    ax.set_ylim(0, 115)
    ax.set_ylabel("held-out mutants caught (%)")
    ax.set_title(f"Catch rate on {n} held-out non-equivalent mutants of {FN}")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    skipped = [l for l, c, _ in methods if c is None]
    if skipped:
        ax.text(0.99, 0.02, "not run: " + ", ".join(skipped), transform=ax.transAxes, ha="right", fontsize=8,
                color="#555")
    fig.tight_layout()
    fig.savefig(ROOT / "docs" / "bench.png", dpi=150)

    # markdown
    L = [f"# Doppel benchmark ({FN})", "",
         "All numbers below were measured by `python -m bench.run_bench` (raw data: `bench/results.json`).", "",
         "## Setup",
         f"- Mutants: {res['n_total']} generated by seeded AST operators (seed 0) from `reference.py`; "
         f"{res['n_dev']} dev, {res['n_total'] - res['n_dev']} held-out (`id % 3 == 0` -> dev, fixed before tuning).",
         f"- Likely-equivalent (identical to reference on 3000 fuzzed schema inputs): {res['n_equiv']}; excluded.",
         f"- Held-out non-equivalent mutants evaluated: {n}.",
         f"- Doppel config: max_examples={res['max_examples']}, time_budget_s={res['max_examples'] and res['time_budget_s']}; "
         f"twins: {res['twins']}.", "",
         "## Catch rate (held-out)", "", "| Method | Caught | Rate |", "|---|---|---|"]
    for l, c, extra in methods:
        L.append(f"| {l} | {len(c)}/{n} | {len(c) / n * 100:.0f}% |" if c is not None
                 else f"| {l} | not run: {'skipped by flag' if l == 'Doppel' else 'files absent'} | - |")
    L.append("")
    if methods[0][1] is not None:
        _, c, extra = methods[0]
        L.append(f"Doppel QUESTION (counted separately, not as caught): {len(extra['question'])}; "
                 f"other verdicts (VERIFIED/UNPROVEN/ERROR): {len(extra['other'])}.")
        rt = [r["doppel"]["secs"] for r in rows.values()]
        L.append(f"Doppel average time per run: {sum(rt) / len(rt):.1f}s (cost: no LLM calls in the verify path measured here).")
        if "false_alarm" in res:
            fa = res["false_alarm"]
            L.append(f"False alarm check (correct reference submitted as the PR): verdict {fa['verdict']} "
                     f"({fa['reason']}); false alarm = {'YES' if fa['verdict'] in ('BLOCKED', 'QUESTION') else 'no'}.")
        L.append("")
    for label, key, files, ref_key in (("PR's own tests", "pr_tests", res["pr_files"], "pr_on_reference"),
                                       ("LLM blind tests", "llm_tests", res["llm_files"], "llm_on_reference")):
        if files:
            L.append(f"{label}: files {', '.join(files)}; on the correct reference: {res[ref_key]['status']}; "
                     f"collection/other errors on mutants: "
                     f"{sum(1 for r in rows.values() if r[key]['status'] == 'error')}.")
        else:
            L.append(f"{label}: not run: files absent.")
    L += ["", "## Misses by name (held-out)", ""]
    for l, c, _ in methods:
        if c is None:
            continue
        missed = [i for i in rows if i not in c]
        L.append(f"**{l}** missed {len(missed)}:")
        for i in missed:
            extra = ""
            if l.startswith("Doppel"):
                extra = f" [verdict {rows[i]['doppel']['verdict']}]"
            L.append(f"- #{i} ({rows[i]['operator']}) {rows[i]['description']}{extra}")
        L.append("")
    L += ["## Test-file contract for baselines", "",
          "- Plain pytest files named `test_*.py` or `*_test.py` (functions `test_*` using `assert`).",
          "- Import the function under test with `from solution import prorate_refund`. The loader writes the "
          "mutant's full module source to `solution.py` in a temp dir and runs `python -m pytest` there; "
          "no other imports of repo code are available.",
          f"- PR's own tests: `demo_target/{FN}/ai_pr/`. LLM blind tests: `bench/llm_artifacts/` "
          "(all files in the directory are run together; a mutant is caught if any test fails, a pytest timeout "
          "counts as failure, a collection error does not count as caught).",
          "- Tests should pass on the correct reference; the run reports whether they do.", ""]
    (ROOT / "docs" / "BENCH.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    sys.exit(main())
