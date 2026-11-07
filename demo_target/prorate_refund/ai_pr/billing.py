import re
from datetime import date
from decimal import Decimal

_PRICE_RE = re.compile(r"[0-9]+(\.[0-9]+)?")
_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def _parse_date(value: str) -> date:
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        raise ValueError(f"invalid date: {value!r}")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"invalid date: {value!r}") from None


def _parse_price(value: str) -> Decimal:
    if not isinstance(value, str):
        raise ValueError(f"invalid price: {value!r}")
    if value.startswith("-"):
        raise ValueError("negative price")
    if not _PRICE_RE.fullmatch(value):
        raise ValueError(f"invalid price: {value!r}")
    if "." in value and len(value.split(".")[1]) > 2:
        raise ValueError("more than 2 decimal places in price")
    return Decimal(value)


def prorate_refund(price: str, period_start: str, period_end: str, cancel_date: str) -> str:
    amount = _parse_price(price)
    start = _parse_date(period_start)
    end = _parse_date(period_end)
    cancel = _parse_date(cancel_date)
    if end <= start:
        raise ValueError("period_end must be after period_start")

    total_days = (end - start).days
    if cancel >= end:
        return "0.00"
    if cancel < start:
        return f"{amount:.2f}"

    used_days = (cancel - start).days + 1
    unused_days = total_days - used_days
    # Exact integer arithmetic in cents; round half up.
    cents = int(amount * 100)
    refund_cents = (2 * cents * unused_days + total_days) // (2 * total_days)
    refund_cents = max(0, min(refund_cents, cents))
    return f"{refund_cents // 100}.{refund_cents % 100:02d}"
