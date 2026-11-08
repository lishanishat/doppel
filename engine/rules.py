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
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TWO_DP = re.compile(r"^\d+\.\d{2}$")
_PLAIN_PRICE = re.compile(r"^\d+(\.\d{1,2})?$")


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


def classify_input(kw: dict) -> str:
    """Spec rule 2 -> "valid" | "invalid" | "unclear". Only clear-cut cases count, so a rule never
    blocks on a reading the spec leaves open (e.g. "1E+2" prices, cancel_date before period_start)."""
    p = kw.get("price")
    if not isinstance(p, str):
        return "invalid"
    try:
        dp = Decimal(p)
    except InvalidOperation:
        return "invalid"
    if not dp.is_finite() or dp < 0 or dp != dp.quantize(Decimal("0.01")):
        return "invalid"
    dates = [kw.get(k) for k in ("period_start", "period_end", "cancel_date")]
    parsed = [_d(x) for x in dates]
    for raw, d in zip(dates, parsed):
        if d is None:
            if isinstance(raw, str) and _DATE_RE.match(raw):
                return "invalid"  # right shape, not a real calendar date
            return "invalid" if not isinstance(raw, str) else "unclear"
    s, e, c = parsed
    if not s < e:
        return "invalid"
    if not _PLAIN_PRICE.match(p) or c < s:
        return "unclear"
    return "valid"


def is_valid_input(kw: dict) -> bool:
    return classify_input(kw) == "valid"


def _never_out_of_range(kw, res) -> bool:
    if not res.get("ok") or classify_input(kw) != "valid":
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
    return classify_input(kw) != "invalid" or not res.get("ok")


def _zero_after_end(kw, res) -> bool:
    if classify_input(kw) != "valid" or _d(kw["cancel_date"]) < _d(kw["period_end"]):
        return True
    return res.get("ok") is True and res.get("value") == "0.00"


RULES: dict[str, list[Rule]] = {
    "prorate_refund": [
        Rule("never_negative_or_above_price", "A refund is never negative and never more than the price.",
             _never_out_of_range),
        Rule("exactly_2dp_string", "The refund as a decimal string with exactly 2 decimal places",
             _two_dp),
        Rule("invalid_input_raises", "Invalid input raises `ValueError`", _invalid_raises),
        Rule("zero_on_or_after_end",
             "If `cancel_date` is on or after `period_end`, nothing is left unused and the refund is `\"0.00\"`.",
             _zero_after_end),
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
    if fn not in RULES:
        return []
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
