# model: meta/muse-spark-1.3
from solution import prorate_refund
import re
import pytest
from decimal import Decimal

MONEY_RE = re.compile(r"^\d+\.\d{2}$")


def assert_money(s):
    assert isinstance(s, str), f"expected str, got {type(s)}"
    assert MONEY_RE.match(s), f"refund {s!r} does not have exactly 2 decimal places"


# ---- Examples from spec ----
@pytest.mark.parametrize(
    "price,start,end,cancel,expected",
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
def test_spec_examples(price, start, end, cancel, expected):
    r = prorate_refund(price, start, end, cancel)
    assert r == expected
    assert_money(r)


# ---- Rule 1: period includes start, excludes end ----
def test_april_30_day_period_start_day():
    # total 30, used 1, unused 29 => 30*29/30 = 29.00
    assert prorate_refund("30.00", "2026-04-01", "2026-05-01", "2026-04-01") == "29.00"


def test_april_30_day_period_second_day():
    # used 2, unused 28 => 28.00
    assert prorate_refund("30.00", "2026-04-01", "2026-05-01", "2026-04-02") == "28.00"


def test_april_30_day_period_last_day():
    # 2026-04-30 is last included day: used 30, unused 0
    assert prorate_refund("30.00", "2026-04-01", "2026-05-01", "2026-04-30") == "0.00"


def test_single_day_period_cancel_on_that_day():
    assert prorate_refund("99.99", "2026-04-01", "2026-04-02", "2026-04-01") == "0.00"


def test_single_day_period_cancel_before():
    assert prorate_refund("99.99", "2026-04-01", "2026-04-02", "2026-03-31") == "99.99"


def test_single_day_period_cancel_on_end():
    assert prorate_refund("99.99", "2026-04-01", "2026-04-02", "2026-04-02") == "0.00"


def test_single_day_period_cancel_after():
    assert prorate_refund("99.99", "2026-04-01", "2026-04-02", "2026-04-05") == "0.00"


def test_february_non_leap_28_days():
    # 2026 is not leap: 2026-02-01 to 2026-03-01 is 28 days
    assert prorate_refund("28.00", "2026-02-01", "2026-03-01", "2026-02-01") == "27.00"
    assert prorate_refund("28.00", "2026-02-01", "2026-03-01", "2026-02-15") == "13.00"
    assert prorate_refund("28.00", "2026-02-01", "2026-03-01", "2026-02-28") == "0.00"


def test_february_leap_29_days():
    # 2028 is leap: covered by examples, plus start day check
    # total 29, cancel on start: used 1 unused 28 => 29*28/29 = 28.00
    assert prorate_refund("29.00", "2028-02-01", "2028-03-01", "2028-02-01") == "28.00"


def test_year_boundary_period():
    # 2025-12-30 to 2026-01-02 is 3 days
    assert prorate_refund("9.00", "2025-12-30", "2026-01-02", "2025-12-30") == "6.00"
    assert prorate_refund("9.00", "2025-12-30", "2026-01-02", "2025-12-31") == "3.00"
    assert prorate_refund("9.00", "2025-12-30", "2026-01-02", "2026-01-01") == "0.00"
    assert prorate_refund("9.00", "2025-12-30", "2026-01-02", "2025-12-29") == "9.00"
    assert prorate_refund("9.00", "2025-12-30", "2026-01-02", "2026-01-02") == "0.00"


def test_large_price():
    assert prorate_refund("1000000.00", "2026-04-01", "2026-05-01", "2026-04-15") == "500000.00"


# ---- Rule 3: cancel on or after period_end ----
def test_cancel_on_end_is_zero():
    assert prorate_refund("30.00", "2026-04-01", "2026-05-01", "2026-05-01") == "0.00"


def test_cancel_day_after_end_is_zero():
    assert prorate_refund("30.00", "2026-04-01", "2026-05-01", "2026-05-02") == "0.00"


def test_cancel_far_after_end_is_zero():
    assert prorate_refund("30.00", "2026-04-01", "2026-05-01", "2030-01-01") == "0.00"
    assert prorate_refund("0.01", "2026-04-01", "2026-04-03", "2027-01-01") == "0.00"
    assert prorate_refund("0.00", "2026-04-01", "2026-05-01", "2026-06-01") == "0.00"


# ---- Rule 4: cancel before period_start ----
def test_cancel_day_before_start_full_refund():
    assert prorate_refund("30.00", "2026-04-01", "2026-05-01", "2026-03-31") == "30.00"


def test_cancel_far_before_start_full_refund():
    assert prorate_refund("30.00", "2026-04-01", "2026-05-01", "2020-01-01") == "30.00"


def test_cancel_before_start_normalizes_to_two_decimals():
    assert prorate_refund("12.5", "2026-04-01", "2026-05-01", "2026-03-25") == "12.50"
    assert prorate_refund("30", "2026-04-01", "2026-05-01", "2026-03-25") == "30.00"
    assert prorate_refund("0.5", "2026-04-01", "2026-04-03", "2026-03-31") == "0.50"
    assert prorate_refund("0", "2026-04-01", "2026-05-01", "2026-03-01") == "0.00"
    assert prorate_refund("0.00", "2026-04-01", "2026-05-01", "2026-03-01") == "0.00"


# ---- Rule 5: inside period uses inclusive cancel day ----
def test_inside_period_inclusive_counting():
    # verified against spec examples: Apr10 => 20 unused, Apr15 => 15 unused
    assert prorate_refund("30.00", "2026-04-01", "2026-05-01", "2026-04-10") == "20.00"
    # one-decimal price inside period: 12.5 * 29 / 30 = 12.0833.. => 12.08
    assert prorate_refund("12.5", "2026-04-01", "2026-05-01", "2026-04-01") == "12.08"
    # integer price inside: 10c * 9 / 10
    assert prorate_refund("0.10", "2026-04-01", "2026-04-11", "2026-04-01") == "0.09"


def test_zero_price_always_zero():
    assert prorate_refund("0.00", "2026-04-01", "2026-05-01", "2026-03-15") == "0.00"
    assert prorate_refund("0.00", "2026-04-01", "2026-05-01", "2026-04-10") == "0.00"
    assert prorate_refund("0.00", "2026-04-01", "2026-05-01", "2026-05-01") == "0.00"
    assert prorate_refund("0.00", "2026-04-01", "2026-05-01", "2026-06-01") == "0.00"
    assert prorate_refund("0", "2026-04-01", "2026-05-01", "2026-04-10") == "0.00"


# ---- Rule 6: rounding half up ----
def test_rounding_standard_up():
    # 10*26/30 = 8.666.. => 8.67
    assert prorate_refund("10.00", "2026-04-01", "2026-05-01", "2026-04-04") == "8.67"


def test_rounding_half_cent_up_smallest():
    # 0.01 * 1 / 2 = 0.005 => 0.01 (half up; half-even would give 0.00)
    assert prorate_refund("0.01", "2026-04-01", "2026-04-03", "2026-04-01") == "0.01"


def test_rounding_half_cent_up_12_5_cents():
    # 1.00 * 1 / 8 = 0.125 => 0.13 (half up; half-even would give 0.12)
    assert prorate_refund("1.00", "2026-04-01", "2026-04-09", "2026-04-07") == "0.13"


def test_rounding_half_cent_up_87_5_cents():
    # 1.00 * 7 / 8 = 0.875 => 0.88
    assert prorate_refund("1.00", "2026-04-01", "2026-04-09", "2026-04-01") == "0.88"


def test_rounding_half_cent_up_187_5_cents():
    # 2.50 * 3 / 4 = 1.875 => 1.88
    assert prorate_refund("2.50", "2026-04-01", "2026-04-05", "2026-04-01") == "1.88"


def test_rounding_exact_value_unchanged():
    # 1.00 * 6 / 8 = 0.75 exact
    assert prorate_refund("1.00", "2026-04-01", "2026-04-09", "2026-04-02") == "0.75"


def test_rounding_down():
    # 0.01 * 1 / 3 = 0.00333.. => 0.00
    assert prorate_refund("0.01", "2026-04-01", "2026-04-04", "2026-04-02") == "0.00"


def test_rounding_up_non_half():
    # 0.01 * 2 / 3 = 0.00666.. => 0.01
    assert prorate_refund("0.01", "2026-04-01", "2026-04-04", "2026-04-01") == "0.01"


def test_output_always_two_decimals():
    cases = [
        ("30.00", "2026-04-01", "2026-05-01", "2026-04-10"),
        ("12.5", "2026-04-01", "2026-05-01", "2026-03-01"),
        ("30", "2026-04-01", "2026-05-01", "2026-03-01"),
        ("0.01", "2026-04-01", "2026-04-03", "2026-04-01"),
        ("0.00", "2026-04-01", "2026-05-01", "2026-04-10"),
        ("1.00", "2026-04-01", "2026-04-09", "2026-04-07"),
    ]
    for price, s, e, c in cases:
        r = prorate_refund(price, s, e, c)
        assert_money(r)


# ---- Rule 7: never negative, never more than price ----
def test_refund_never_negative_never_exceeds_price():
    price = "30.00"
    start = "2026-04-01"
    end = "2026-05-01"
    cancels = [
        "2026-03-01",
        "2026-03-31",
        "2026-04-01",
        "2026-04-10",
        "2026-04-15",
        "2026-04-30",
        "2026-05-01",
        "2026-05-02",
        "2027-01-01",
    ]
    for c in cancels:
        r = prorate_refund(price, start, end, c)
        assert Decimal(r) >= Decimal("0.00")
        assert Decimal(r) <= Decimal(price)


def test_refund_bounds_small_price():
    for c in ["2026-03-31", "2026-04-01", "2026-04-02", "2026-04-03", "2026-04-04"]:
        r = prorate_refund("0.01", "2026-04-01", "2026-04-04", c)
        assert Decimal(r) >= Decimal("0.00")
        assert Decimal(r) <= Decimal("0.01")


def test_refund_bounds_zero_price():
    for c in ["2026-03-31", "2026-04-01", "2026-05-01", "2026-06-01"]:
        r = prorate_refund("0.00", "2026-04-01", "2026-05-01", c)
        assert r == "0.00"


# ---- Rule 2: invalid inputs raise ValueError ----
@pytest.mark.parametrize(
    "bad_price",
    [
        "",
        "abc",
        "twelve",
        "12.3.4",
        "12,00",
        "$10.00",
        "10.001",
        "0.001",
        "12.345",
        "1.234",
        "-0.01",
        "-30.00",
        "-1",
        "-12.50",
    ],
)
def test_invalid_price_raises(bad_price):
    with pytest.raises(ValueError):
        prorate_refund(bad_price, "2026-04-01", "2026-05-01", "2026-04-10")


@pytest.mark.parametrize(
    "bad_date",
    [
        "",
        "not-a-date",
        "2026-13-01",
        "2026-00-10",
        "2026-02-30",
        "2026-04-31",
        "2026/04/01",
        "2026-02-29",  # 2026 is not a leap year
        "2026-04-32",
    ],
)
def test_invalid_period_start_raises(bad_date):
    with pytest.raises(ValueError):
        prorate_refund("10.00", bad_date, "2026-05-01", "2026-04-10")


@pytest.mark.parametrize(
    "bad_date",
    [
        "",
        "not-a-date",
        "2026-13-01",
        "2026-02-30",
        "2026/05/01",
        "2026-02-29",
    ],
)
def test_invalid_period_end_raises(bad_date):
    with pytest.raises(ValueError):
        prorate_refund("10.00", "2026-04-01", bad_date, "2026-04-10")


@pytest.mark.parametrize(
    "bad_date",
    [
        "",
        "not-a-date",
        "2026-13-01",
        "2026-02-30",
        "2026/04/10",
        "2026-02-29",
    ],
)
def test_invalid_cancel_date_raises(bad_date):
    with pytest.raises(ValueError):
        prorate_refund("10.00", "2026-04-01", "2026-05-01", bad_date)


def test_period_end_equal_start_raises():
    with pytest.raises(ValueError):
        prorate_refund("10.00", "2026-04-01", "2026-04-01", "2026-04-01")


def test_period_end_before_start_raises():
    with pytest.raises(ValueError):
        prorate_refund("10.00", "2026-05-01", "2026-04-01", "2026-04-10")
    with pytest.raises(ValueError):
        prorate_refund("10.00", "2026-04-02", "2026-04-01", "2026-04-01")


def test_invalid_price_still_raises_when_cancel_after_end():
    # validation must happen even if refund would otherwise be 0.00
    with pytest.raises(ValueError):
        prorate_refund("10.001", "2026-04-01", "2026-05-01", "2026-05-01")
    with pytest.raises(ValueError):
        prorate_refund("-5.00", "2026-04-01", "2026-05-01", "2027-01-01")


def test_invalid_cancel_still_raises_when_would_be_full_or_zero():
    with pytest.raises(ValueError):
        prorate_refund("10.00", "2026-04-01", "2026-05-01", "bad-date")
    with pytest.raises(ValueError):
        prorate_refund("10.00", "bad-start", "2026-05-01", "2026-06-01")


def test_more_than_two_decimals_always_invalid():
    with pytest.raises(ValueError):
        prorate_refund("12.500", "2026-04-01", "2026-05-01", "2026-03-01")
    with pytest.raises(ValueError):
        prorate_refund("0.000", "2026-04-01", "2026-05-01", "2026-04-01")
