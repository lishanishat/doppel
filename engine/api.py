"""ENGINE side public API. Owner: engine person. See contract/types.py.

Stub mode (default, DOPPEL_STUBS unset or 1): returns fixtures so the Fetch side can build now.
  DOPPEL_STUB_VERDICT = blocked | question | verified | unproven   (default: blocked)
Real mode (DOPPEL_STUBS=0): replace the NotImplementedError branches with the real Referee.
"""
from __future__ import annotations

import hashlib
import os
import time

from contract import stubs
from contract.types import Evidence, VerifyRequest
from engine import ledger, regression, rules
from engine import verdict as verdict_mod

_answered: list[dict] = []


def _verify_real(req: VerifyRequest) -> Evidence:
    t0 = time.time()
    seed = req.get("seed", 0)
    fn = req.get("function_name", "")
    run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{hashlib.sha256((str(t0) + fn).encode()).hexdigest()[:6]}"
    state: dict = {"rr": None, "rules": [], "n_reg": 0}
    try:
        verdict, reason, ce, q = _pipeline(req, state, run_id)
    except BaseException as e:  # never raise
        if isinstance(e, (KeyboardInterrupt, SystemExit)):
            raise
        verdict, reason, ce, q = "UNPROVEN", f"Engine error: {type(e).__name__}: {e}", None, None
    rr = state["rr"] or {}
    timings = {"total_s": round(time.time() - t0, 3), **{k: v for k, v in (rr.get("timings") or {}).items() if isinstance(v, (int, float))}}
    ev: Evidence = {
        "verdict": verdict, "reason": reason, "n_inputs": rr.get("n_inputs", 0), "counterexample": ce,
        "question": q, "rules": state["rules"], "flaky_excluded": rr.get("flaky", 0),
        "regression_tests": state["n_reg"], "seed": seed, "timings": timings,
        "ledger_path": "", "repro_cmd": _repro_cmd(req, run_id),
    }  # type: ignore[typeddict-item]
    try:
        if q:
            regression.add_pending(q, fn)
        ev["ledger_path"] = ledger.write(run_id, ledger.build_payload(req, ev, state["rr"]))
    except Exception as e:
        ev["reason"] += f" (ledger write failed: {e})"
    return ev


def _repro_cmd(req, run_id) -> str:
    d = ledger.LEDGERS / f"{run_id}_versions"
    try:
        d.mkdir(parents=True, exist_ok=True)
        for v in req.get("versions", []):
            (d / f"{v['name']}.py").write_text(v["code"])
    except Exception:
        pass
    return (f"python -m engine.cli verify --fn {req.get('function_name')} --pr {d}/pr.py --twin-a {d}/twin_a.py "
            f"--twin-b {d}/twin_b.py --seed {req.get('seed', 0)} --max-examples {req.get('max_examples', 2000)}")


def _pipeline(req, state, run_id):
    fn = req.get("function_name", "")
    versions = req.get("versions", [])
    by = {v["name"]: v for v in versions}
    if set(by) != {"pr", "twin_a", "twin_b"}:
        return "UNPROVEN", "Request must contain exactly the versions pr, twin_a, twin_b.", None, None
    from engine import target as target_mod
    inputs = req.get("inputs")
    try:
        if isinstance(inputs, list) and inputs and not (target_mod.ROOT / "demo_target" / fn).is_dir():
            target = target_mod.from_inputs(fn, req.get("spec_text", ""), inputs)
        else:
            target = target_mod.load(fn)
    except Exception as e:
        return "UNPROVEN", f"Function out of scope (no demo target for '{fn}'): {e}", None, None
    from engine.harness import BuildError, Runner
    runners, build_errors = {}, {}
    try:
        for name in ("pr", "twin_a", "twin_b"):
            v = by[name]
            try:
                runners[name] = Runner(name, v["code"], v["entrypoint"])
            except BuildError as e:
                build_errors[name] = str(e)
        if build_errors:
            return verdict_mod.decide(None, [], build_errors, None)
        from engine import referee
        rr = referee.run(target, versions, seed=req.get("seed", 0), max_examples=req.get("max_examples", 2000),
                         time_budget_s=req.get("time_budget_s", 60))
        state["rr"] = rr
        state["rules"] = rules.evaluate(fn, rr.get("samples", []), spec=target.spec_text)
        n, fails = regression.check_detail(fn, runners["pr"])
        state["n_reg"] = n
        return verdict_mod.decide(rr, state["rules"], {}, None, answered=regression.answered(fn), regression_failures=fails)
    finally:
        for r in runners.values():
            try:
                r.close()
            except Exception:
                pass


def verify(req: VerifyRequest) -> Evidence:
    if stubs.stubs_on():
        ev = stubs.load(os.environ.get("DOPPEL_STUB_VERDICT", "blocked"))
        ev["seed"] = req.get("seed", 0)
        return ev  # type: ignore[return-value]
    return _verify_real(req)


def answer_question(question_id: str, chosen: str) -> int:
    if stubs.stubs_on():
        _answered.append({"question_id": question_id, "chosen": chosen})
        return len(_answered)
    from engine import regression
    return regression.answer(question_id, chosen)
