"""Evidence ledger (CLAUDE.md section 7): one JSON file per run in ledgers/."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGERS = ROOT / "ledgers"


def sha(s: str | None) -> str | None:
    return None if s is None else hashlib.sha256(s.encode()).hexdigest()


def write(run_id: str, payload: dict) -> str:
    LEDGERS.mkdir(exist_ok=True)
    p = LEDGERS / f"{run_id}.json"
    p.write_text(json.dumps(payload, indent=2, default=str))
    return str(p)


def build_payload(req: dict, evidence: dict, referee_result: dict | None, extra: dict | None = None) -> dict:
    rr = referee_result or {}
    n = rr.get("n_inputs", 0)
    vs = {v["name"]: v for v in req.get("versions", [])}
    ces = []
    for ce in rr.get("confirmed", []):  # outputs are already protocol-normalized; raw kept alongside
        ces.append({**ce, "raw_outputs": ce.get("raw_outputs", ce["outputs"]), "normalized_outputs": ce["outputs"]})
    return {
        "function": req.get("function_name"), "pr_ref": req.get("pr_ref"),
        "spec_hash": sha(req.get("spec_text", "")),
        "versions": {k: {"code_hash": sha(v["code"]), "model": v.get("model"), "prompt_hash": v.get("prompt_hash"),
                         "temperature": v.get("temperature")} for k, v in vs.items()},
        "seed": evidence["seed"], "n_inputs": evidence["n_inputs"],
        "disagreements": rr.get("disagreements", 0),
        "disagreement_rate": (rr.get("disagreements", 0) / n) if n else 0.0,
        "flaky_excluded": evidence["flaky_excluded"], "faults": rr.get("faults", {}),
        "counterexamples": ces, "rules": evidence["rules"],
        "verdict": evidence["verdict"], "reason": evidence["reason"], "question": evidence["question"],
        "timings": evidence["timings"], "cost_usd": 0.0,
        "repro_cmd": evidence["repro_cmd"], "regression_tests": evidence["regression_tests"],
        **(extra or {}),
    }
