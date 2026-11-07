# model: meta/muse-spark-1.3
# prompt_sha256: bf1669c7b46fe071e97593a8192fb133f15471cd612a2e93a526550ca885d411
# generated_utc: 2026-11-07T21:34:21Z
import datetime


def _parse_price_to_cents(price):
    if not isinstance(price, str):
        raise ValueError("invalid price")
    if len(price) == 0:
        raise ValueError("invalid price")
    dot_count = 0
    dot_pos = -1
    pos = 0
    while pos < len(price):
        ch = price[pos]
        if ch == ".":
            dot_count = dot_count + 1
            if dot_count > 1:
                raise ValueError("invalid price")
            dot_pos = pos
        elif ch >= "0" and ch <= "9":
            pass
        else:
            raise ValueError("invalid price")
        pos = pos + 1
    if dot_count == 0:
        int_value = 0
        i = 0
        while i < len(price):
            int_value = int_value * 10 + (ord(price[i]) - 48)
            i = i + 1
        return int_value * 100
    else:
        int_len = dot_pos
        frac_len = len(price) - dot_pos - 1
        if int_len == 0:
            raise ValueError("invalid price")
        if frac_len == 0 or frac_len > 2:
            raise ValueError("invalid price")
        int_value = 0
        i = 0
        while i < int_len:
            int_value = int_value * 10 + (ord(price[i]) - 48)
            i = i + 1
        frac_value = 0
        if frac_len == 1:
            frac_value = (ord(price[dot_pos + 1]) - 48) * 10
        else:
            frac_value = (ord(price[dot_pos + 1]) - 48) * 10 + (ord(price[dot_pos + 2]) - 48)
        return int_value * 100 + frac_value


def _parse_iso_date(s):
    if not isinstance(s, str):
        raise ValueError("invalid date")
    if len(s) != 10:
        raise ValueError("invalid date")
    if s[4] != "-" or s[7] != "-":
        raise ValueError("invalid date")
    for idx in (0, 1, 2, 3, 5, 6, 8, 9):
        ch = s[idx]
        if ch < "0" or ch > "9":
            raise ValueError("invalid date")
    year = 0
    for idx in (0, 1, 2, 3):
        year = year * 10 + (ord(s[idx]) - 48)
    month = 0
    for idx in (5, 6):
        month = month * 10 + (ord(s[idx]) - 48)
    day = 0
    for idx in (8, 9):
        day = day * 10 + (ord(s[idx]) - 48)
    try:
        return datetime.date(year, month, day)
    except ValueError:
        raise ValueError("invalid date")


def prorate_refund(price: str, period_start: str, period_end: str, cancel_date: str) -> str:
    price_cents = _parse_price_to_cents(price)
    start_date = _parse_iso_date(period_start)
    end_date = _parse_iso_date(period_end)
    cancel = _parse_iso_date(cancel_date)
    if end_date <= start_date:
        raise ValueError("period_end must be after period_start")
    one_day = datetime.timedelta(days=1)
    total_days = 0
    cur = start_date
    while cur < end_date:
        total_days = total_days + 1
        cur = cur + one_day
    if cancel >= end_date:
        return "0.00"
    if cancel < start_date:
        unused_days = total_days
    else:
        used_days = 0
        cur2 = start_date
        while True:
            used_days = used_days + 1
            if cur2 == cancel:
                break
            cur2 = cur2 + one_day
        unused_days = total_days - used_days
    if unused_days <= 0:
        return "0.00"
    if unused_days > total_days:
        unused_days = total_days
    numerator = 0
    k = 0
    while k < unused_days:
        numerator = numerator + price_cents
        k = k + 1
    denominator = total_days
    q = numerator // denominator
    r = numerator % denominator
    if r + r >= denominator:
        q = q + 1
    refund_cents = q
    if refund_cents < 0:
        refund_cents = 0
    if refund_cents > price_cents:
        refund_cents = price_cents
    dollars = refund_cents // 100
    cents_rem = refund_cents - dollars * 100
    dollars_str = str(dollars)
    cents_str = str(cents_rem)
    if cents_rem < 10:
        cents_str = "0" + cents_str
    return dollars_str + "." + cents_str
