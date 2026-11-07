# model: meta/muse-spark-1.3
# prompt_sha256: 72dcb25a8748045c1955d25106bf9e4168b60b00d655a4cc70f40352dae8cfc9
# generated_utc: 2026-11-07T22:00:54Z
import re
from datetime import date

_PRICE_RE = re.compile(r'[0-9]+(?:\.[0-9]{1,2})?')
_DATE_RE = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}')


def _parse_price_cents(price: str) -> int:
    if not isinstance(price, str):
        raise ValueError("invalid price")
    if _PRICE_RE.fullmatch(price) is None:
        raise ValueError("invalid price")
    try:
        if '.' in price:
            whole_s, frac_s = price.split('.', 1)
            if len(frac_s) == 1:
                frac_s = frac_s + '0'
            return int(whole_s) * 100 + int(frac_s)
        else:
            return int(price) * 100
    except Exception as e:
        raise ValueError("invalid price") from e


def _parse_iso_date(s: str) -> date:
    if not isinstance(s, str):
        raise ValueError("invalid date")
    if _DATE_RE.fullmatch(s) is None:
        raise ValueError("invalid date")
    try:
        y = int(s[0:4])
        m = int(s[5:7])
        d = int(s[8:10])
        return date(y, m, d)
    except ValueError as e:
        raise ValueError("invalid date") from e


def prorate_refund(price: str, period_start: str, period_end: str, cancel_date: str) -> str:
    price_cents = _parse_price_cents(price)

    start = _parse_iso_date(period_start)
    end = _parse_iso_date(period_end)
    cancel = _parse_iso_date(cancel_date)

    if end <= start:
        raise ValueError("period_end must be after period_start")

    total_days = (end - start).days

    if cancel >= end:
        return "0.00"

    if cancel < start:
        refund_cents = price_cents
    else:
        used_days = (cancel - start).days + 1
        unused_days = total_days - used_days
        # clamp unused just in case
        if unused_days < 0:
            unused_days = 0
        if unused_days > total_days:
            unused_days = total_days
        numer = price_cents * unused_days
        q, r = divmod(numer, total_days)
        if 2 * r >= total_days:
            q += 1
        refund_cents = q
        if refund_cents < 0:
            refund_cents = 0
        if refund_cents > price_cents:
            refund_cents = price_cents

    return f"{refund_cents // 100}.{refund_cents % 100:02d}"
