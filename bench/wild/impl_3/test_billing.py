import pytest

from billing import prorate_refund


@pytest.mark.parametrize(
    "price, start, end, cancel, expected",
    [
        ("30.00", "2026-04-01", "2026-05-01", "2026-04-10", "20.00"),
        ("30.00", "2026-04-01", "2026-05-01", "2026-04-15", "15.00"),
        ("10.00", "2026-04-01", "2026-05-01", "2026-04-04", "8.67"),
        ("29.00", "2028-02-01", "2028-03-01", "2028-02-28", "1.00"),
        ("29.00", "2028-02-01", "2028-03-01", "2028-02-29", "0.00"),
        ("30.00", "2026-04-01", "2026-05-01", "2026-05-01", "0.00"),
        ("30.00", "2026-04-01", "2026-05-01", "2026-03-25", "30.00"),
    ],
)
def test_issue_examples(price, start, end, cancel, expected):
    assert prorate_refund(price, start, end, cancel) == expected


def test_cancel_on_first_day_refunds_all_but_one_day():
    # 30 days, used 1 -> 29/30 of 30.00 = 29.00
    assert prorate_refund("30.00", "2026-04-01", "2026-05-01", "2026-04-01") == "29.00"


def test_cancel_after_period_end_is_zero():
    assert prorate_refund("30.00", "2026-04-01", "2026-05-01", "2026-06-01") == "0.00"


def test_zero_price_refunds_zero():
    assert prorate_refund("0", "2026-04-01", "2026-05-01", "2026-04-10") == "0.00"


def test_price_without_decimals_formats_with_two_places():
    assert prorate_refund("12.5", "2026-04-01", "2026-05-01", "2026-05-01") == "0.00"
    assert prorate_refund("12.5", "2026-04-01", "2026-05-01", "2026-03-01") == "12.50"


def test_half_cent_rounds_up():
    # 1.00 * 1 / 2 = 0.5 exactly -> 0.50 (no cents to round here, check half-cent case)
    # 0.05 * 1 / 2 = 0.025 -> 0.03 (half rounds up)
    assert prorate_refund("0.05", "2026-04-01", "2026-04-03", "2026-04-01") == "0.03"


def test_no_float_artifacts():
    # 0.10 * 1 / 3 = 0.0333... -> 0.03; full-period check with 0.10 * 2/3 -> 0.07
    assert prorate_refund("0.10", "2026-04-01", "2026-04-04", "2026-04-02") == "0.03"


@pytest.mark.parametrize(
    "price",
    ["abc", "", "-1.00", "1.234", "1,000.00", " 30.00", "30.", "1e3", "+5.00"],
)
def test_bad_price_raises(price):
    with pytest.raises(ValueError):
        prorate_refund(price, "2026-04-01", "2026-05-01", "2026-04-10")


@pytest.mark.parametrize("bad", ["2026-4-1", "2026/04/01", "not-a-date", "2026-02-30", ""])
def test_bad_dates_raise(bad):
    with pytest.raises(ValueError):
        prorate_refund("30.00", bad, "2026-05-01", "2026-04-10")
    with pytest.raises(ValueError):
        prorate_refund("30.00", "2026-04-01", "2026-05-01", bad)


def test_period_end_not_after_start_raises():
    with pytest.raises(ValueError):
        prorate_refund("30.00", "2026-05-01", "2026-04-01", "2026-04-10")
    with pytest.raises(ValueError):
        prorate_refund("30.00", "2026-04-01", "2026-04-01", "2026-04-10")
