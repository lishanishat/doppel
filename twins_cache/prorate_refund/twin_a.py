# model: meta/muse-spark-1.3
# prompt_sha256: bc9adb602d031901ea37706f697b0bcbb3a9c59fe0bbd941a8f73dcd64b57aa8
# generated_utc: 2026-11-07T21:32:49Z
import re
from datetime import date

_PRICE_RE = re.compile(r'^\d+(\.\d{1,2})?$')
_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def _parse_price_to_cents(price: str) -> int:
    if not isinstance(price, str):
        raise ValueError("invalid price")
    if not _PRICE_RE.match(price):
        raise ValueError("invalid price")
    if "." in price:
        dollars_part, frac_part = price.split(".", 1)
        dollars = int(dollars_part)
        if len(frac_part) == 1:
            cents = int(frac_part) * 10
        else:
            cents = int(frac_part)
        return dollars * 100 + cents
    else:
        return int(price) * 100


def _parse_date(s: str) -> date:
    if not isinstance(s, str):
        raise ValueError("invalid date")
    if not _DATE_RE.match(s):
        raise ValueError("invalid date")
    try:
        y_str, m_str, d_str = s.split("-", 2)
        y = int(y_str)
        m = int(m_str)
        d = int(d_str)
        return date(y, m, d)
    except ValueError as e:
        raise ValueError("invalid date") from e


def prorate_refund(price: str, period_start: str, period_end: str, cancel_date: str) -> str:
    price_cents = _parse_price_to_cents(price)
    start = _parse_date(period_start)
    end = _parse_date(period_end)
    cancel = _parse_date(cancel_date)

    total_days = (end - start).days
    if total_days <= 0:
        raise ValueError("period_end must be after period_start")

    if cancel >= end:
        return "0.00"

    if cancel < start:
        refund_cents = price_cents
    else:
        used_days = (cancel - start).days + 1
        unused_days = total_days - used_days
        if unused_days < 0:
            unused_days = 0
        if unused_days > total_days:
            unused_days = total_days
        numerator = price_cents * unused_days
        q, r = divmod(numerator, total_days)
        if 2 * r >= total_days:
            q += 1
        refund_cents = q
        if refund_cents < 0:
            refund_cents = 0
        if refund_cents > price_cents:
            refund_cents = price_cents

    dollars = refund_cents // 100
    cents = refund_cents % 100
    return f"{dollars}.{cents:02d}"
