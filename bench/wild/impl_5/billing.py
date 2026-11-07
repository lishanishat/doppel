import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

_PRICE_RE = re.compile(r"^-?\d+(\.\d{1,2})?$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_price(price):
    if not isinstance(price, str):
        raise ValueError("price must be a string")
    if not _PRICE_RE.match(price):
        raise ValueError(f"invalid price: {price!r}")
    value = Decimal(price)
    if value < 0:
        raise ValueError("price must not be negative")
    return value


def _parse_date(s, name):
    if not isinstance(s, str) or not _DATE_RE.match(s):
        raise ValueError(f"invalid {name}: {s!r}")
    try:
        return date.fromisoformat(s)
    except ValueError as e:
        raise ValueError(f"invalid {name}: {s!r}") from e


def prorate_refund(price: str, period_start: str, period_end: str, cancel_date: str) -> str:
    amount = _parse_price(price)
    start = _parse_date(period_start, "period_start")
    end = _parse_date(period_end, "period_end")
    cancel = _parse_date(cancel_date, "cancel_date")
    if end <= start:
        raise ValueError("period_end must be after period_start")

    total_days = (end - start).days
    if cancel >= end:
        refund = Decimal(0)
    elif cancel < start:
        refund = amount
    else:
        used_days = (cancel - start).days + 1
        unused_days = total_days - used_days
        refund = amount * unused_days / total_days

    refund = refund.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    refund = max(Decimal("0.00"), min(refund, amount.quantize(Decimal("0.01"))))
    return f"{refund:.2f}"
