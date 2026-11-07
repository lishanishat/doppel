"""Placeholder twin: counts the cancel day as used (the deliberate spec ambiguity)."""
import re
from datetime import date

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_PRICE = re.compile(r"\d+(\.\d{1,2})?")


def _d(s):
    if not isinstance(s, str) or not _DATE.fullmatch(s):
        raise ValueError("bad date")
    return date.fromisoformat(s)


def _check(price, period_start, period_end, cancel_date):
    if not isinstance(price, str) or not _PRICE.fullmatch(price) or float(price) > 1000000:
        raise ValueError("bad price")
    s, e, c = _d(period_start), _d(period_end), _d(cancel_date)
    if not s < e:
        raise ValueError("bad period")
    if not s <= c <= e:
        raise ValueError("cancel outside period")
    return float(price), s, e, c

from decimal import ROUND_HALF_UP, Decimal


def prorate_refund(price, period_start, period_end, cancel_date):
    _, s, e, c = _check(price, period_start, period_end, cancel_date)
    total = (e - s).days
    used = min(total, (c - s).days + 1)
    r = (Decimal(price) * (total - used) / total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{r:.2f}"
