import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

_PRICE = re.compile(r"[0-9]+(\.[0-9]{1,2})?")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def _d(s):
    if not isinstance(s, str) or not _DATE.fullmatch(s):
        raise ValueError("bad date")
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise ValueError("bad date")


def prorate_refund(price: str, period_start: str, period_end: str, cancel_date: str) -> str:
    if not isinstance(price, str) or not _PRICE.fullmatch(price):
        raise ValueError("bad price")
    p = Decimal(price)
    start, end, cancel = _d(period_start), _d(period_end), _d(cancel_date)
    if end <= start:
        raise ValueError("period_end must be after period_start")
    total = (end - start).days
    if cancel >= end:
        refund = Decimal(0)
    elif cancel < start:
        refund = p
    else:
        unused = total - ((cancel - start).days + 1)
        refund = p * unused / total
    refund = refund.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    refund = max(Decimal("0.00"), min(refund, p))
    return format(refund.quantize(Decimal("0.01")), "f")
