import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

_PRICE_RE = re.compile(r"\d+(\.\d+)?|\.\d+")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _date(s):
    if not isinstance(s, str) or not _DATE_RE.fullmatch(s):
        raise ValueError(f"invalid date: {s!r}")
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError) as e:
        raise ValueError(f"invalid date: {s!r}") from e


def prorate_refund(price: str, period_start: str, period_end: str, cancel_date: str) -> str:
    if not isinstance(price, str):
        raise ValueError("invalid price")
    if price.startswith("-") and _PRICE_RE.fullmatch(price[1:]):
        raise ValueError("negative price")
    if not _PRICE_RE.fullmatch(price):
        raise ValueError(f"invalid price: {price!r}")
    amount = Decimal(price)
    if amount != amount.quantize(Decimal("0.01")) or (
        "." in price and len(price.split(".")[1]) > 2
    ):
        raise ValueError("more than 2 decimal places")
    start, end, cancel = _date(period_start), _date(period_end), _date(cancel_date)
    if end <= start:
        raise ValueError("period_end must be after period_start")
    total = (end - start).days
    if cancel >= end:
        refund = Decimal(0)
    elif cancel < start:
        refund = amount
    else:
        unused = total - ((cancel - start).days + 1)
        refund = amount * unused / total
    refund = refund.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    refund = max(Decimal("0.00"), min(refund, amount.quantize(Decimal("0.01"))))
    return f"{refund:.2f}"
