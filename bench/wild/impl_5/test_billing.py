import pytest
from billing import prorate_refund


@pytest.mark.parametrize("price,start,end,cancel,expected", [
    ("30.00", "2026-04-01", "2026-05-01", "2026-04-10", "20.00"),
    ("30.00", "2026-04-01", "2026-05-01", "2026-04-15", "15.00"),
    ("10.00", "2026-04-01", "2026-05-01", "2026-04-04", "8.67"),
    ("29.00", "2028-02-01", "2028-03-01", "2028-02-28", "1.00"),
    ("29.00", "2028-02-01", "2028-03-01", "2028-02-29", "0.00"),
    ("30.00", "2026-04-01", "2026-05-01", "2026-05-01", "0.00"),
    ("30.00", "2026-04-01", "2026-05-01", "2026-03-25", "30.00"),
])
def test_issue_examples(price, start, end, cancel, expected):
    assert prorate_refund(price, start, end, cancel) == expected


def test_cancel_on_start_day_uses_one_day():
    assert prorate_refund("30.00", "2026-04-01", "2026-05-01", "2026-04-01") == "29.00"


def test_half_rounds_up():
    # 0.05 * 1 / 2 = 0.025 -> 0.03
    assert prorate_refund("0.05", "2026-01-01", "2026-01-03", "2026-01-01") == "0.03"


def test_one_decimal_price_and_zero_price():
    assert prorate_refund("12.5", "2026-04-01", "2026-05-01", "2026-03-01") == "12.50"
    assert prorate_refund("0", "2026-04-01", "2026-05-01", "2026-04-02") == "0.00"


def test_after_period_end():
    assert prorate_refund("30.00", "2026-04-01", "2026-05-01", "2027-01-01") == "0.00"


@pytest.mark.parametrize("price", ["-1.00", "1.234", "abc", "", "1e2", " 1.00", "NaN", "1."])
def test_bad_price(price):
    with pytest.raises(ValueError):
        prorate_refund(price, "2026-04-01", "2026-05-01", "2026-04-10")


@pytest.mark.parametrize("d", ["2026-13-01", "2026-02-30", "20260401", "nope", ""])
def test_bad_dates(d):
    for args in [(d, "2026-05-01", "2026-04-10"),
                 ("2026-04-01", d, "2026-04-10"),
                 ("2026-04-01", "2026-05-01", d)]:
        with pytest.raises(ValueError):
            prorate_refund("30.00", *args)


@pytest.mark.parametrize("start,end", [("2026-05-01", "2026-05-01"), ("2026-05-02", "2026-05-01")])
def test_end_not_after_start(start, end):
    with pytest.raises(ValueError):
        prorate_refund("30.00", start, end, "2026-04-10")
