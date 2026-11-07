import pytest
from hypothesis import given, settings

from demo_target.prorate_refund.reference import prorate_refund
from demo_target.prorate_refund.schema import prorate_inputs

EXAMPLES = [  # the table in spec.md
    ("30.00", "2026-04-01", "2026-05-01", "2026-04-10", "20.00"),
    ("30.00", "2026-04-01", "2026-05-01", "2026-04-15", "15.00"),
    ("10.00", "2026-04-01", "2026-05-01", "2026-04-04", "8.67"),
    ("29.00", "2028-02-01", "2028-03-01", "2028-02-28", "1.00"),
    ("29.00", "2028-02-01", "2028-03-01", "2028-02-29", "0.00"),
    ("30.00", "2026-04-01", "2026-05-01", "2026-05-01", "0.00"),
]


@pytest.mark.parametrize("price,s,e,c,expected", EXAMPLES)
def test_spec_examples(price, s, e, c, expected):
    assert prorate_refund(price, s, e, c) == expected


@pytest.mark.parametrize("args", [
    ("-1.00", "2026-04-01", "2026-05-01", "2026-04-10"),
    ("10.005", "2026-04-01", "2026-05-01", "2026-04-10"),
    ("abc", "2026-04-01", "2026-05-01", "2026-04-10"),
    ("10.00", "2026-05-01", "2026-05-01", "2026-05-01"),
    ("10.00", "2026-04-01", "2026-05-01", "2026-02-30"),
])
def test_invalid_raises(args):
    with pytest.raises(ValueError):
        prorate_refund(*args)


@settings(max_examples=500, deadline=None)
@given(prorate_inputs())
def test_never_negative_never_above_price(kw):
    try:
        out = prorate_refund(**kw)
    except ValueError:
        return
    from decimal import Decimal
    assert Decimal("0.00") <= Decimal(out) <= Decimal(kw["price"])
