import re
from datetime import date
from fractions import Fraction

_PRICE_RE = re.compile(r"^\d+(\.\d{1,2})?$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_date(value: str) -> date:
    if not isinstance(value, str) or not _DATE_RE.match(value):
        raise ValueError(f"invalid ISO date: {value!r}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid ISO date: {value!r}") from exc


def _parse_price(value: str) -> Fraction:
    if not isinstance(value, str) or not _PRICE_RE.match(value):
        raise ValueError(f"invalid price: {value!r}")
    return Fraction(value)


def prorate_refund(price: str, period_start: str, period_end: str, cancel_date: str) -> str:
    amount = _parse_price(price)
    start = _parse_date(period_start)
    end = _parse_date(period_end)
    cancel = _parse_date(cancel_date)

    if end <= start:
        raise ValueError("period_end must be after period_start")

    total_days = (end - start).days

    if cancel >= end:
        refund = Fraction(0)
    elif cancel < start:
        refund = amount
    else:
        used_days = (cancel - start).days + 1
        unused_days = total_days - used_days
        refund = amount * unused_days / total_days

    # Round to the nearest cent, exact halves rounded up (refund is never negative).
    cents = int(refund * 100 + Fraction(1, 2))
    cents = max(0, min(cents, int(amount * 100)))
    return f"{cents // 100}.{cents % 100:02d}"
