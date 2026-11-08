"""Prepare / run / answer. Pure Python (no uagents). Network via agents.github_client."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from contract.types import Evidence, Version

from agents import formatting, github_client
from agents.commands import Command

ROOT = Path(__file__).resolve().parent.parent


class UserFacingError(Exception):
    """Message is safe to show in chat."""


@dataclass
class Prepared:
    spec_text: str
    function_name: str
    signature: str
    pr: Version
    pr_ref: str
    repo: Optional[str]
    pr_number: Optional[int]


def _is_test_file(path: str) -> bool:
    p = path.split("/")
    base = p[-1]
    return base.startswith("test_") or base.endswith("_test.py") or "tests" in p[:-1] or base == "conftest.py"


def _signature(spec: str, fn: str) -> str:
    for line in spec.splitlines():
        if "def " in line:
            return line.strip().strip("`").strip()
    return f"def {fn}(...)"


def _spec_issue(body: str) -> Optional[int]:
    m = re.search(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)", body or "", re.I)
    if m:
        return int(m.group(1))
    env = os.environ.get("DEMO_SPEC_ISSUE")
    return int(env) if env and env.isdigit() else None


def prepare(cmd: Command) -> Prepared:
    fn = cmd.function_name or os.environ.get("DEMO_FUNCTION", "prorate_refund")

    if cmd.kind in ("verify_pr", "verify_url"):
        repo = cmd.repo or os.environ.get("DEMO_REPO", "lishanishat/doppel-demo")
        n = cmd.pr_number
        pr = github_client.get_pr(repo, n)
        defining = re.compile(rf"^\s*def\s+{re.escape(fn)}\s*\(", re.M)
        cands = [f for f in pr["files"] if f["path"].endswith(".py") and not _is_test_file(f["path"])]
        hit = next((f for f in cands if defining.search(f["content"])), None)
        if hit is None:
            raise UserFacingError(f"I couldn't find a non-test .py file defining `{fn}` in {repo}#{n}.")
        issue_no = _spec_issue(pr["body"])
        if issue_no is None:
            raise UserFacingError(f"{repo}#{n} doesn't say which issue it closes (add `Closes #N`).")
        spec = github_client.get_issue(repo, issue_no)["body"]
        return Prepared(
            spec_text=spec, function_name=fn, signature=_signature(spec, fn),
            pr=Version(name="pr", code=hit["content"], entrypoint=fn, model="unknown (PR author)", prompt_hash=None),
            pr_ref=f"{repo}#{n}", repo=repo, pr_number=n,
        )

    if cmd.kind == "verify_mutant":
        spec_path = ROOT / "demo_target" / "prorate_refund" / "spec.md"
        if not spec_path.exists():
            raise UserFacingError("spec not ready yet")
        spec = spec_path.read_text()
        from bench import api as bench_api
        try:
            m = bench_api.get_mutant(cmd.mutant_id)
        except UserFacingError:
            raise
        except Exception as e:
            raise UserFacingError(f"Couldn't load mutant #{cmd.mutant_id}: {e}")
        fn = m.get("entrypoint") or fn
        return Prepared(
            spec_text=spec, function_name=fn, signature=_signature(spec, fn),
            pr=Version(name="pr", code=m["code"], entrypoint=fn, model="mutant", prompt_hash=None),
            pr_ref=f"mutant#{cmd.mutant_id}", repo=None, pr_number=None,
        )

    raise UserFacingError("Nothing to prepare for that command.")


def prepare_custom(cmd: Command) -> Prepared:
    from agents import custom  # built in parallel; import lazily
    try:
        req = custom.parse_custom(getattr(cmd, "raw", None) or "")
    except ValueError as e:
        raise UserFacingError(str(e))
    fn = req.function_name
    return Prepared(
        spec_text=req.spec_text, function_name=fn, signature=req.signature,
        pr=Version(name="pr", code=req.code, entrypoint=fn, model="user-submitted", prompt_hash=None),
        pr_ref=f"custom:{fn}", repo=None, pr_number=None,
    )


def _unproven(reason: str) -> Evidence:
    return Evidence(
        verdict="UNPROVEN", reason=reason, n_inputs=0, counterexample=None, question=None,
        rules=[], flaky_excluded=0, regression_tests=0, seed=0, timings={}, ledger_path="", repro_cmd="",
    )


def run(prep: Prepared, twins: list[Version], max_examples: int) -> tuple[Evidence, str]:
    try:
        from engine import api as engine_api
        req = {
            "function_name": prep.function_name,
            "spec_text": prep.spec_text,
            "versions": [prep.pr, *twins],
            "max_examples": max_examples,
            "pr_ref": prep.pr_ref,
        }
        evidence = engine_api.verify(req)
        models = {v.get("name"): v.get("model") for v in twins}
        url = None
        if prep.repo and prep.pr_number:
            body = formatting.verdict_text(evidence, None, models)
            event = "REQUEST_CHANGES" if evidence["verdict"] == "BLOCKED" else "COMMENT"
            try:
                url = github_client.post_review(prep.repo, prep.pr_number, body, event)
            except Exception:
                if event != "COMMENT":  # e.g. can't request changes on own PR
                    try:
                        url = github_client.post_review(prep.repo, prep.pr_number, body, "COMMENT")
                    except Exception:
                        url = None
        return evidence, formatting.verdict_text(evidence, url, models)
    except Exception as e:  # never raise
        ev = _unproven(f"verification failed: {str(e)[:200] or type(e).__name__}")
        return ev, formatting.verdict_text(ev, None)


def run_custom(prep: Prepared, twins: list[Version], inputs: list[dict], max_examples: int) -> tuple[Evidence, str]:
    try:
        from engine import api as engine_api
        req = {
            "function_name": prep.function_name,
            "spec_text": prep.spec_text,
            "versions": [prep.pr, *twins],
            "max_examples": max_examples,
            "pr_ref": prep.pr_ref,
            "inputs": inputs,
        }
        evidence = engine_api.verify(req)
        models = {v.get("name"): v.get("model") for v in twins}
        return evidence, formatting.verdict_text(evidence, None, models)
    except Exception as e:  # never raise
        ev = _unproven(f"verification failed: {str(e)[:200] or type(e).__name__}")
        return ev, formatting.verdict_text(ev, None)


def answer(question_id: str, choice: str) -> str:
    try:
        from engine import api as engine_api
        n = engine_api.answer_question(question_id, choice)
        label = {"pr": "the submitted code", "twin_a": "Rebuild 1", "twin_b": "Rebuild 2"}.get(choice, choice)
        return f"Recorded: {label} is correct. Saved as a regression test ({n} saved in total)."
    except Exception as e:
        return formatting.error_text(f"Couldn't save that answer: {str(e)[:200]}")
