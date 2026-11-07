"""Saved answered questions (regression.json at repo root) and pending questions (ledgers/questions.json)."""
from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "regression.json"
PENDING = ROOT / "ledgers" / "questions.json"


def _load(p: Path, default):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def load() -> list[dict]:
    return _load(REG, [])


def count(fn: str | None = None) -> int:
    return len([e for e in load() if fn is None or e.get("fn") == fn])


def answered(fn: str | None = None) -> dict:
    return {e["question_id"]: e for e in load() if fn is None or e.get("fn") in (None, fn)}


def add_pending(question: dict, fn: str) -> None:
    PENDING.parent.mkdir(exist_ok=True)
    d = _load(PENDING, {})
    d[question["id"]] = {"fn": fn, "question": question}
    PENDING.write_text(json.dumps(d, indent=2))


def save(question: dict, chosen: str, fn: str = "prorate_refund") -> int:
    if chosen not in question["options"]:
        raise ValueError(f"chosen must be one of {list(question['options'])}")
    entries = [e for e in load() if e["question_id"] != question["id"]]
    entries.append({"question_id": question["id"], "fn": fn, "input": question["input"],
                    "expected": question["options"][chosen], "chosen": chosen,
                    "question": question["text"], "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
    REG.write_text(json.dumps(entries, indent=2))
    return len(entries)


def answer(question_id: str, chosen: str) -> int:
    p = _load(PENDING, {}).get(question_id)
    if p is None:
        raise KeyError(f"unknown question id {question_id}")
    return save(p["question"], chosen, p["fn"])


def _same(a, b) -> bool:
    if not a.get("ok") and not b.get("ok"):
        return True
    return bool(a.get("ok")) == bool(b.get("ok")) and a.get("value") == b.get("value")


def check_detail(fn: str, runner_pr) -> tuple[int, list[dict]]:
    n, fails = 0, []
    for e in load():
        if e.get("fn") not in (None, fn):
            continue
        n += 1
        got = runner_pr.call(e["input"])
        if "error" in got or not _same(got, e["expected"]):
            fails.append({"question_id": e["question_id"], "input": e["input"], "expected": e["expected"], "got": got})
    return n, fails


def check(fn: str, runner_pr) -> tuple[int, int]:
    n, fails = check_detail(fn, runner_pr)
    return n, len(fails)
