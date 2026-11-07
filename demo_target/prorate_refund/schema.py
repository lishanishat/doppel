"""Hypothesis strategy that generates kwargs for prorate_refund (strings only, JSON-friendly).

Biased toward edge cases: month ends, leap days, cancel dates at/around the period boundaries,
zero and tiny prices, and about 5% invalid inputs (so 'raises vs not' is compared too).
"""
from datetime import date, timedelta

from hypothesis import strategies as st

_PRICES = st.one_of(
    st.sampled_from(["0.00", "0.01", "0.50", "1.00", "9.99", "10.00", "29.00", "30.00", "99999.99", "12.5"]),
    st.builds(lambda c: f"{c // 100}.{c % 100:02d}", st.integers(0, 2_000_000)),
)
_EDGE_DATES = st.sampled_from(
    [date(2024, 2, 28), date(2024, 2, 29), date(2024, 3, 1), date(2026, 1, 31), date(2026, 2, 28),
     date(2026, 3, 31), date(2026, 4, 30), date(2026, 12, 31), date(2028, 2, 29), date(2027, 12, 31)]
)
_STARTS = st.one_of(_EDGE_DATES, st.dates(date(2024, 1, 1), date(2030, 12, 31)))
_LENGTHS = st.one_of(st.sampled_from([1, 2, 7, 28, 29, 30, 31, 365, 366]), st.integers(1, 400))


@st.composite
def prorate_inputs(draw):
    start = draw(_STARTS)
    length = draw(_LENGTHS)
    end = start + timedelta(days=length)
    offset = draw(st.one_of(
        st.sampled_from([-1, 0, 1, length - 2, length - 1, length, length + 1]),
        st.integers(-5, length + 5),
    ))
    cancel = start + timedelta(days=offset)
    kw = {
        "price": draw(_PRICES),
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "cancel_date": cancel.isoformat(),
    }
    if draw(st.integers(0, 99)) < 5:  # ~5% invalid inputs
        bad = draw(st.sampled_from(["neg_price", "three_decimals", "bad_date", "end_before_start", "garbage_price"]))
        if bad == "neg_price":
            kw["price"] = "-1.00"
        elif bad == "three_decimals":
            kw["price"] = "10.005"
        elif bad == "bad_date":
            kw["cancel_date"] = "2026-02-30"
        elif bad == "end_before_start":
            kw["period_end"] = (start - timedelta(days=draw(st.integers(0, 5)))).isoformat()
        else:
            kw["price"] = "abc"
    return kw
