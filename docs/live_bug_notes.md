# Live bug plants (measured)

Each row is one mutation planted with `scripts/plant_bug.py` on the AI-written PR file and verified with the real engine and cached twins. Misses are listed too.

| Plant | Operator | Change | Verdict | Time |
|---|---|---|---|---|
| billing.py:21 | remove_check | removed check 'if value.startswith('-'): raise ...' | **VERIFIED** | 0.5s |
| billing.py:25 | flip_comparison | '>' -> '>=' | **BLOCKED** | 0.5s |
| billing.py:38 | swap_arith | '-' -> '+' | **BLOCKED** | 0.6s |
| billing.py:44 | off_by_one_const | constant 1 -> 2 | **BLOCKED** | 0.7s |
| billing.py:50 | off_by_one_const | constant 100 -> 99 | **BLOCKED** | 0.6s |
| billing.py:47 | swap_arith | '*' -> '/' | **BLOCKED** | 0.6s |

## Misses

- billing.py:21 (VERIFIED): `_PRICE_RE` on line 5 is `[0-9]+(\.[0-9]+)?`, which already rejects any leading `-` at line 23 with the same `ValueError` type, so removing the explicit negative check only changes the error message text. It is plausibly an equivalent change.

## Summary

6 plants run: 5 blocked, 1 not blocked (VERIFIED), 0 UNPROVEN. Average time 0.6s (sum 3.5s over 6 runs).
