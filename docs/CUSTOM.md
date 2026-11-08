# Custom mode: verify your own function

Paste a message to the Doppel agent in ASI:One (after the `@agent...` mention) in this format:

    verify custom
    spec: <plain-English description of what the function must do>
    ```python
    def my_func(a: int, b: str = "x") -> int:
        ...
    ```

Doppel then (about 3-5 minutes): 1) generates test inputs, 2) has two different AI models rebuild the
function from your spec alone, 3) compares your code with both rebuilds. Disagreements are checked
against the spec and reported as a verdict.

## Writing a good spec
Be precise about edge cases: ranges (inclusive/exclusive), rounding, what raises ValueError, empty input.
The AI rebuilds only know your spec, so vague specs produce false alarms.

## Scope
- Pure Python, standard library only; deterministic (no network, files, clock, randomness).
- Arguments and return value must be JSON-able (str, int, float, bool, list, dict, None).
- The first top-level `def` in the first python block is the function under test.

## Examples (examples/custom/)
Each correct file should verify clean; the `_buggy` twin has one subtle bug Doppel should catch:
- business_days_between: buggy counts the end date (differs on 2024-01-01 -> 2024-01-02: 1 vs 2)
- parse_duration: buggy ignores unknown units (differs on "1h5x": ValueError vs 3600)
- apply_discounts: buggy rounds after every step (differs on "10.05", [10, 10]: 8.14 vs 8.15)
