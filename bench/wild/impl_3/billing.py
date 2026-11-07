"""Prorated refund calculation for cancelled subscription periods."""

import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

_PRICE_RE = re.compile(r"^[0-9]+(\.[0-9]{1,2})?$")
_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_CENT = Decimal("0.01")


def _parse_price(price: str) -> Decimal:
    if not isinstance(price, str) or not _PRICE_RE.fullmatch(price):
        raise ValueError(f"invalid price: {price!r}")
    return Decimal(price)


def _parse_date(value: str, name: str) -> date:
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        raise ValueError(f"invalid {name}: {value!r}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid {name}: {value!r}") from exc


def prorate_refund(price: str, period_start: str, period_end: str, cancel_date: str) -> str:
    """Return the refund for the unused part of a billing period, as "N.NN".

    The period includes period_start and excludes period_end. If the customer
    cancels inside the period, every day from period_start through cancel_date
    counts as used. Refunds are rounded to the nearest cent, halves up.
    """
    amount = _parse_price(price)
    start = _parse_date(period_start, "period_start")
    end = _parse_date(period_end, "period_end")
    cancel = _parse_date(cancel_date, "cancel_date")

    if end <= start:
        raise ValueError("period_end must be after period_start")

    if cancel >= end:
        return "0.00"
    if cancel < start:
        return str(amount.quantize(_CENT, rounding=ROUND_HALF_UP))

    total_days = (end - start).days
    used_days = (cancel - start).days + 1
    unused_days = total_days - used_days

    refund = amount * unused_days / total_days
    refund = min(max(refund, Decimal("0")), amount)
    return str(refund.quantize(_CENT, rounding=ROUND_HALF_UP))
