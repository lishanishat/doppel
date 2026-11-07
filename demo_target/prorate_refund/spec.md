def prorate_refund(price: str, period_start: str, period_end: str, cancel_date: str) -> str

# Refund the unused part of a billing period when a customer cancels

When a customer cancels a subscription part-way through a billing period, we refund the part of the
period they did not use. Implement `prorate_refund` in Python (standard library only).

## Inputs
- `price`: the amount paid for the whole period, a decimal string such as `"30.00"` or `"12.5"`.
  It is zero or more, with at most 2 decimal places.
- `period_start`, `period_end`: ISO dates (`"YYYY-MM-DD"`).
- `cancel_date`: the ISO date on which the customer cancelled.

## Output
The refund as a decimal string with exactly 2 decimal places, such as `"14.50"`.

## Rules
1. The billing period includes `period_start` and excludes `period_end`.
   Its length is `total_days = (period_end - period_start)` in days.
2. Invalid input raises `ValueError`: a malformed or unparseable price or date, a negative price,
   more than 2 decimal places in the price, or a `period_end` that is not after `period_start`.
3. If `cancel_date` is on or after `period_end`, nothing is left unused and the refund is `"0.00"`.
4. If `cancel_date` is before `period_start`, the customer cancelled before the period began and the
   full `price` is refunded.
5. If `cancel_date` is inside the period (`period_start <= cancel_date < period_end`), the customer
   has used every day from `period_start` up to and including `cancel_date`.
   `unused_days = total_days - used_days`.
6. `refund = price * unused_days / total_days`, rounded to the nearest cent, with exact halves
   rounded up. Do not use binary floating point for money.
7. A refund is never negative and never more than the price.

## Examples
| price | period_start | period_end | cancel_date | refund |
|---|---|---|---|---|
| `"30.00"` | `2026-04-01` | `2026-05-01` | `2026-04-10` | `"20.00"` |
| `"30.00"` | `2026-04-01` | `2026-05-01` | `2026-04-15` | `"15.00"` |
| `"10.00"` | `2026-04-01` | `2026-05-01` | `2026-04-04` | `"8.67"` |
| `"29.00"` | `2028-02-01` | `2028-03-01` | `2028-02-28` | `"1.00"` |
| `"29.00"` | `2028-02-01` | `2028-03-01` | `2028-02-29` | `"0.00"` |
| `"30.00"` | `2026-04-01` | `2026-05-01` | `2026-05-01` | `"0.00"` |
| `"30.00"` | `2026-04-01` | `2026-05-01` | `2026-03-25` | `"30.00"` |
