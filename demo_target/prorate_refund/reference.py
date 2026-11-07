"""Correct reference implementation of prorate_refund (written by hand from spec.md).

Used only by our own tooling: mutants are generated from this file, and it is the ground truth for
the benchmark. It is never shown to the twin builder or to the verifier's voting.
"""
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_CENT = Decimal("0.01")


def _parse_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError) as e:
        raise ValueError(f"bad date: {s!r}") from e


def prorate_refund(price: str, period_start: str, period_end: str, cancel_date: str) -> str:
    try:
        p = Decimal(price)
    except (InvalidOperation, TypeError) as e:
        raise ValueError(f"bad price: {price!r}") from e
    if not p.is_finite() or p < 0 or p != p.quantize(_CENT):
        raise ValueError(f"bad price: {price!r}")

    start, end, cancel = _parse_date(period_start), _parse_date(period_end), _parse_date(cancel_date)
    total_days = (end - start).days
    if total_days <= 0:
        raise ValueError("period_end must be after period_start")

    if cancel >= end:
        return "0.00"
    if cancel < start:
        return f"{p:.2f}"  # cancelled before the period began: full refund
    used_days = (cancel - start).days + 1
    unused_days = total_days - used_days

    refund = (p * unused_days / total_days).quantize(_CENT, rounding=ROUND_HALF_UP)
    refund = max(Decimal("0.00"), min(refund, p))
    return f"{refund:.2f}"
