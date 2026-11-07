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
        ("30.00", "2026-04-01", "2026-05-01", "2026-04-01", "29.00"),
        ("12.5", "2026-04-01", "2026-05-01", "2026-04-01", "12.08"),
        ("0", "2026-04-01", "2026-05-01", "2026-04-10", "0.00"),
        ("30.00", "2026-04-01", "2026-05-01", "2027-01-01", "0.00"),
    ],
)
def test_examples(price, start, end, cancel, expected):
    assert prorate_refund(price, start, end, cancel) == expected


def test_half_cent_rounds_up():
    # 0.01 * 1 / 2 = 0.005 exactly -> 0.01
    assert prorate_refund("0.01", "2026-04-01", "2026-04-03", "2026-04-01") == "0.01"


def test_no_float_error():
    # 0.10 * 1 / 3 = 0.0333... -> 0.03
    assert prorate_refund("0.10", "2026-04-01", "2026-04-04", "2026-04-02") == "0.03"


@pytest.mark.parametrize(
    "price",
    ["-1.00", "1.001", "abc", "", "1e3", " 5.00", "5.", ".5"],
)
def test_invalid_price(price):
    with pytest.raises(ValueError):
        prorate_refund(price, "2026-04-01", "2026-05-01", "2026-04-10")


@pytest.mark.parametrize(
    "start, end, cancel",
    [
        ("2026-13-01", "2026-05-01", "2026-04-10"),
        ("2026-4-1", "2026-05-01", "2026-04-10"),
        ("not-a-date", "2026-05-01", "2026-04-10"),
        ("2026-04-01", "2026-02-30", "2026-04-10"),
        ("2026-04-01", "2026-05-01", "2026-04-31"),
    ],
)
def test_invalid_dates(start, end, cancel):
    with pytest.raises(ValueError):
        prorate_refund("30.00", start, end, cancel)


def test_end_not_after_start():
    with pytest.raises(ValueError):
        prorate_refund("30.00", "2026-05-01", "2026-05-01", "2026-05-01")
    with pytest.raises(ValueError):
        prorate_refund("30.00", "2026-05-01", "2026-04-01", "2026-04-10")
