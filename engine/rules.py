"""Spec-cited invariants. A rule can block only if its spec line is quoted verbatim from spec.md
AND it passes on >= 1 twin (judged from the referee samples); otherwise it is advisory."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parent.parent
_PRICE_RE = re.compile(r"^\d+(\.\d{1,2})?$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TWO_DP = re.compile(r"^\d+\.\d{2}$")


@dataclass
class Rule:
    name: str
    spec_line: str
    check: Callable[[dict, dict], bool]   # (kwargs, result) -> True if the rule holds


def _d(s):
    if not isinstance(s, str) or not _DATE_RE.match(s):
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def is_valid_input(kw: dict) -> bool:
    """Spec rules 1-4."""
    p = kw.get("price")
    if not isinstance(p, str) or not _PRICE_RE.match(p):
        return False
    if not (Decimal(p) <= Decimal("1000000")):
        return False
    s, e, c = (_d(kw.get(k)) for k in ("period_start", "period_end", "cancel_date"))
    if None in (s, e, c) or not s < e:
        return False
    return s <= c <= e


def _never_out_of_range(kw, res) -> bool:
    if not res.get("ok"):
        return True
    try:
        v, price = Decimal(str(res["value"])), Decimal(str(kw["price"]))
    except (InvalidOperation, KeyError, TypeError):
        return False
    return Decimal(0) <= v <= price


def _two_dp(kw, res) -> bool:
    if not res.get("ok"):
        return True
    v = res.get("value")
    return isinstance(v, str) and bool(_TWO_DP.match(v))


def _invalid_raises(kw, res) -> bool:
    return is_valid_input(kw) or not res.get("ok")


RULES: dict[str, list[Rule]] = {
    "prorate_refund": [
        Rule("never_negative_or_above_price", "A refund is never negative and never more than `price`.",
             _never_out_of_range),
        Rule("exactly_2dp_string", "Return the refund as a string with exactly two decimal places",
             _two_dp),
        Rule("invalid_input_raises", "Invalid input must raise an exception. Never return a value for invalid input.",
             _invalid_raises),
    ]
}


def spec_text(fn: str) -> str:
    return (ROOT / "demo_target" / fn / "spec.md").read_text()


def _sample_parts(s: dict):
    return s.get("input", s.get("kwargs", {})), s.get("outputs", {})


def evaluate(fn: str, samples: list[dict], versions_outputs: Optional[dict] = None, spec: Optional[str] = None) -> list[dict]:
    """-> list[contract.RuleResult]. `passed` = the PR holds the rule on every sample.
    Samples: [{"input": kwargs, "outputs": {version: result}}]. versions_outputs (optional) maps
    version -> list of results aligned with samples, overriding sample outputs."""
    spec = spec if spec is not None else spec_text(fn)
    out = []
    for rule in RULES.get(fn, []):
        quoted = rule.spec_line in spec  # not quoted verbatim -> advisory, never blocks
        held = {"pr": True, "twin_a": True, "twin_b": True}
        for i, s in enumerate(samples):
            kw, outs = _sample_parts(s)
            for v in held:
                r = (versions_outputs or {}).get(v)
                r = r[i] if r is not None and i < len(r) else outs.get(v)
                if r is not None and not rule.check(kw, r):
                    held[v] = False
        twin_ok = (held["twin_a"] or held["twin_b"]) and bool(samples)
        out.append({"name": rule.name, "spec_line": rule.spec_line if quoted else None,
                    "status": "active" if (quoted and twin_ok) else "advisory", "passed": held["pr"]})
    return out
