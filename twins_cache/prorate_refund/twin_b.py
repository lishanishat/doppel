# model: meta/muse-wonder-1.0
# prompt_sha256: a7f280c0d46490accfae019f16a9031d15566696be0cc5ca5f553f079acd1a1b
# generated_utc: 2026-11-07T22:01:59Z
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


def prorate_refund(price: str, period_start: str, period_end: str, cancel_date: str) -> str:
    if not isinstance(price, str):
        raise ValueError("invalid price")
    if price == "":
        raise ValueError("invalid price")

    dot_seen = False
    digits_before_dot = 0
    digits_after_dot = 0
    digits_seen = 0
    for ch in price:
        if ch == ".":
            if dot_seen:
                raise ValueError("invalid price")
            dot_seen = True
        elif ch >= "0" and ch <= "9":
            digits_seen += 1
            if dot_seen:
                digits_after_dot += 1
            else:
                digits_before_dot += 1
        else:
            raise ValueError("invalid price")

    if digits_seen == 0:
        raise ValueError("invalid price")
    if digits_before_dot == 0:
        raise ValueError("invalid price")
    if dot_seen and digits_after_dot == 0:
        raise ValueError("invalid price")
    if dot_seen and digits_after_dot > 2:
        raise ValueError("invalid price")

    try:
        price_value = Decimal(price)
    except Exception:
        raise ValueError("invalid price")

    if price_value < Decimal("0"):
        raise ValueError("invalid price")

    def parse_date(value):
        if not isinstance(value, str):
            raise ValueError("invalid date")
        if len(value) != 10:
            raise ValueError("invalid date")
        if value[4] != "-":
            raise ValueError("invalid date")
        if value[7] != "-":
            raise ValueError("invalid date")
        index = 0
        for ch in value:
            if index == 4 or index == 7:
                index += 1
                continue
            if ch < "0" or ch > "9":
                raise ValueError("invalid date")
            index += 1
        year_text = value[0:4]
        month_text = value[5:7]
        day_text = value[8:10]
        try:
            parsed = date(int(year_text), int(month_text), int(day_text))
        except Exception:
            raise ValueError("invalid date")
        return parsed

    start_day = parse_date(period_start)
    end_day = parse_date(period_end)
    cancel_day = parse_date(cancel_date)

    if end_day <= start_day:
        raise ValueError("period_end must be after period_start")

    total_days = 0
    used_days = 0
    unused_days = 0
    one_day = timedelta(days=1)
    current_day = start_day
    while current_day < end_day:
        total_days += 1
        if current_day <= cancel_day:
            used_days += 1
        else:
            unused_days += 1
        current_day = current_day + one_day

    if total_days == 0:
        raise ValueError("period_end must be after period_start")

    refund_value = price_value * Decimal(unused_days) / Decimal(total_days)
    refund_rounded = refund_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if refund_rounded < Decimal("0.00"):
        refund_rounded = Decimal("0.00")

    full_price_rounded = price_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if refund_rounded > full_price_rounded:
        refund_rounded = full_price_rounded

    return str(refund_rounded)
