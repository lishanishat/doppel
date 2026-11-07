"""Placeholder buggy PR: off-by-one on total days (period length counted inclusively)."""
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def _d(s):
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError) as e:
        raise ValueError("bad date") from e


def _check(price, period_start, period_end, cancel_date):
    try:
        p = Decimal(price)
    except (InvalidOperation, TypeError) as e:
        raise ValueError("bad price") from e
    if not p.is_finite() or p < 0 or p != p.quantize(Decimal("0.01")):
        raise ValueError("bad price")
    s, e, c = _d(period_start), _d(period_end), _d(cancel_date)
    if (e - s).days <= 0:
        raise ValueError("bad period")
    return p, s, e, c


def prorate_refund(price, period_start, period_end, cancel_date):
    p, s, e, c = _check(price, period_start, period_end, cancel_date)
    if c >= e:
        return "0.00"
    if c < s:
        raise ValueError("cancel before start")
    total = (e - s).days + 1  # BUG: off by one
    unused = total - ((c - s).days + 1)
    r = (p * unused / total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{max(Decimal('0'), min(r, p)):.2f}"
