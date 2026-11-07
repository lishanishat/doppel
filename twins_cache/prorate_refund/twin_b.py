# model: meta/muse-wonder-1.0
# prompt_sha256: bf1669c7b46fe071e97593a8192fb133f15471cd612a2e93a526550ca885d411
# generated_utc: 2026-11-07T21:47:19Z
import datetime


def _parse_price_to_cents(price):
    if not isinstance(price, str):
        raise ValueError("invalid price")
    if price == "":
        raise ValueError("invalid price")

    seen_dot = False
    digits_before_dot = 0
    digits_after_dot = 0

    for ch in price:
        if ch == ".":
            if seen_dot:
                raise ValueError("invalid price")
            seen_dot = True
        elif "0" <= ch <= "9":
            if seen_dot:
                digits_after_dot += 1
            else:
                digits_before_dot += 1
        else:
            raise ValueError("invalid price")

    if digits_before_dot == 0:
        raise ValueError("invalid price")
    if seen_dot and digits_after_dot == 0:
        raise ValueError("invalid price")
    if digits_after_dot > 2:
        raise ValueError("invalid price")

    whole_value = 0
    index = 0
    while index < len(price) and price[index] != ".":
        digit = ord(price[index]) - ord("0")
        whole_value = whole_value * 10 + digit
        index += 1

    cents = whole_value * 100

    if seen_dot:
        first_fraction_index = index + 1
        first_digit = ord(price[first_fraction_index]) - ord("0")
        if digits_after_dot == 1:
            cents += first_digit * 10
        else:
            second_digit = ord(price[first_fraction_index + 1]) - ord("0")
            cents += first_digit * 10 + second_digit

    return cents


def _parse_iso_date(value):
    if not isinstance(value, str):
        raise ValueError("invalid date")
    if len(value) != 10:
        raise ValueError("invalid date")
    if value[4] != "-" or value[7] != "-":
        raise ValueError("invalid date")

    for index in range(len(value)):
        if index == 4 or index == 7:
            continue
        ch = value[index]
        if ch < "0" or ch > "9":
            raise ValueError("invalid date")

    year = int(value[0:4])
    month = int(value[5:7])
    day = int(value[8:10])

    try:
        return datetime.date(year, month, day)
    except ValueError:
        raise ValueError("invalid date") from None


def prorate_refund(price: str, period_start: str, period_end: str, cancel_date: str) -> str:
    price_cents = _parse_price_to_cents(price)
    start = _parse_iso_date(period_start)
    end = _parse_iso_date(period_end)
    cancel = _parse_iso_date(cancel_date)

    if end <= start:
        raise ValueError("period_end must be after period_start")

    one_day = datetime.timedelta(days=1)

    total_days = 0
    current = start
    while current < end:
        total_days += 1
        current = current + one_day

    if cancel >= end:
        return "0.00"

    if cancel < start:
        used_days = 0
        unused_days = 0
        current = start
        while current < end:
            unused_days += 1
            current = current + one_day
    else:
        used_days = 0
        current = start
        while current <= cancel:
            used_days += 1
            current = current + one_day

        unused_days = 0
        current = cancel + one_day
        while current < end:
            unused_days += 1
            current = current + one_day

    if unused_days == 0 or price_cents == 0:
        refund_cents = 0
    else:
        numerator = price_cents * unused_days
        quotient, remainder = divmod(numerator, total_days)
        doubled_remainder = remainder + remainder
        if doubled_remainder >= total_days:
            quotient += 1
        refund_cents = quotient

    if refund_cents < 0:
        refund_cents = 0
    if refund_cents > price_cents:
        refund_cents = price_cents

    dollars, cents_part = divmod(refund_cents, 100)
    return f"{dollars}.{cents_part:02d}"
