# Real AI code study (measured)

Independent implementations of the spec (issue #1), each written by a fresh coding agent from the issue text only, with its own tests. Ground truth: `reference.py` on 3000 seeded schema inputs. Twins: meta/muse-spark-1.3 and meta/muse-wonder-1.0. Raw data: `bench/wild/results.json`. Command: `python -m bench.wild bench/wild/impl_*`.

| Impl | Written by | Differs from reference on | Doppel | Own tests flag a bug | Blind tests flag a bug |
|---|---|---|---|---|---|
| impl_1 | claude-sonnet-5-5 | 0/3000 inputs | **VERIFIED** (0.7s) | no | no |
| impl_2 | claude-sonnet-5-5 | 0/3000 inputs | **VERIFIED** (0.8s) | no | no |
| impl_3 | claude-haiku-5-5 | 0/3000 inputs | **VERIFIED** (0.62s) | no | no |
| impl_4 | claude-haiku-5-5 | 0/3000 inputs | **VERIFIED** (0.64s) | no | no |
| impl_5 | claude-opus-5-5 | 0/3000 inputs | **VERIFIED** (0.62s) | no | no |

## Details

- **impl_1**: Doppel says VERIFIED: VERIFIED on 921 inputs: all versions agree and all active rules hold.
- **impl_2**: Doppel says VERIFIED: VERIFIED on 921 inputs: all versions agree and all active rules hold.
- **impl_3**: Doppel says VERIFIED: VERIFIED on 921 inputs: all versions agree and all active rules hold.
- **impl_4**: Doppel says VERIFIED: VERIFIED on 921 inputs: all versions agree and all active rules hold.
- **impl_5**: Doppel says VERIFIED: VERIFIED on 921 inputs: all versions agree and all active rules hold.

A baseline test only counts if it also passes on the correct reference. "Differs from reference" is ground truth (our hand-written reference), not Doppel's opinion; if an implementation differs only where the spec is silent, that is noted above rather than called a bug.

## Result in one line

All 5 independent AI implementations (3 different Claude models) are correct on the 3000 generated inputs, and Doppel
returned VERIFIED for all 5: **no false alarms on real AI-written code.** Their own tests and the blind tests also flagged
nothing, which is the right answer here.

## Inputs the spec does not pin down (checked by hand, not by Doppel's generator)

Every implementing agent independently said the issue does not define which price *formats* are valid. We ran all versions
on such inputs (price, 2026-04-01 to 2026-05-01, cancel 2026-04-10):

```
price    reference twin_a    twin_b    PR#2      impl_1    impl_2    impl_3    impl_4    impl_5   
'.5'     0.33      error     error     error     error     0.33      error     error     error    
'5.'     3.33      error     error     error     error     error     error     error     error    
' 5.00'  3.33      error     error     error     error     error     error     error     error    
'1e2'    66.67     error     error     error     error     error     error     error     error    
'+5'     3.33      error     error     error     error     error     error     error     error    
'5.00 '  3.33      error     error     error     error     error     error     error     error    
'1.500'  1.00      error     error     error     error     error     error     error     error
```

- **`"1.500"`: all 8 AI-written versions reject it; only our hand-written reference accepts it.** The spec says a price has
  "at most 2 decimal places", and `1.500` has three digits after the point. Read literally, our reference is the outlier,
  which is exactly the situation a majority vote is designed to expose. (Read numerically, `1.500` equals `1.50`; the spec
  does not say which reading is meant, so this is a genuine ambiguity, not a clear-cut bug.)
- **`".5"`: `impl_2` accepts it (refund `0.33`); every other AI version rejects it.** The spec is silent on this format.
- Doppel's fuzzer did **not** find these: its input generator only produces canonical prices. Widening the generator to
  include such formats is the obvious next step. We did not change the reference or the benchmark after this finding.
