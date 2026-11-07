# Demo script (3 min live + Q&A) and 1-minute submission video

Everything below has been run for real except the on-stage timing. Twins are cached; nothing in the demo calls an LLM.

## Before you go on stage (2 min)
- Laptop **plugged in**, Orchestrator + Twin builder running under `caffeinate` (`make orchestrator`, `make twin-builder`).
- ASI:One: open the **doppel-orchestrator** profile and click **Chat with Agent** so the message is addressed to it.
  (A message without the agent address goes to your personal AI instead.) Have the chat open in one window and
  https://github.com/lishanishat/doppel-demo/pull/2 and `/pull/3` in tabs.
- Have `docs/bench.png` / `docs/BENCH.md` open for the benchmark slide.

## Live demo (3:00)

| Time | What you do | What you say |
|---|---|---|
| 0:00-0:20 | Show PR #2 on GitHub: an AI-written proration function with its own tests, all passing. | "AI checking AI shares its blind spots. This PR was written by a coding agent from a spec, and its own tests pass. Would you merge it?" |
| 0:20-0:50 | In ASI:One: `verify pr #2`. Instant "Got it" reply, then **VERIFIED on N inputs** and a link to the GitHub review. | "Doppel reads the spec from the issue, asks a separate agent to rebuild the function twice, using two different models, one deliberately naive, and runs all three on a few hundred generated inputs. They agree. Note it says *evidence on N inputs*, not 'proven'." |
| 0:50-1:30 | `verify pr #3`. **BLOCKED**: counterexample, the PR returns `0.01`, both twins `0.00`, vote 2-1, review link. Show the review on GitHub. | "Same code, but with one bug injected **automatically** by our seeded mutation tool, not written by hand. Doppel found the exact input, one cent, one day, where the PR disagrees with both rebuilds. The verdict comes from fixed code, not an LLM." |
| 1:30-2:10 | Benchmark slide (`docs/bench.png`). | "On 15 automatically generated bugs held out before tuning: Doppel caught 15, the AI's own tests caught 13. Spec-written blind tests also caught 15, so we match them, we don't beat them, on this function. The difference is nobody wrote a test or an oracle here, and the verdict is deterministic." |
| 2:10-3:00 | **A judge picks a number** from {1, 2, 4, 5, 7, 8, 10, 11, 13, 14, 16, 17, 19, 20, 22}. Type `verify mutant #N`. | "Nobody, including us, chose that bug." Read the result as it appears; if it's a rare miss or equivalent, say so. |

Close: "Airplanes don't trust one flight computer. Why trust one AI?"

All 15 held-out mutants were blocked in the benchmark in well under a second each, so any number a judge picks should finish fast.
Fallback if ASI:One is slow: show the same results in `docs/BENCH.md` and the review comments already on PRs #2 and #3.

## One-minute submission video (~150 words, record screen + voice)
1. (0-10 s) "Doppel verifies AI-written code by rebuilding it independently from the spec and making the versions argue. Fixed code decides, not an LLM."
2. (10-25 s) Show ASI:One, `verify pr #2` -> VERIFIED, then `verify pr #3` -> BLOCKED with the counterexample.
3. (25-40 s) Show the GitHub review on PR #3 and the benchmark chart: "15 of 15 automatic bugs caught; the AI's own tests caught 13."
4. (40-55 s) "Everything here was built today: two Fetch agents on Agentverse using the chat protocol, a verification engine, a seeded mutation benchmark. The repo shows what we built, and the limits, in the README."
5. (55-60 s) "Doppel: airplanes don't trust one flight computer, why trust one AI?"

## Q&A (honest answers)
- **Isn't this just N-version programming?** Yes, applied to AI-written code. What we add is ambiguity detection (a three-way split becomes one question), verdicts decided by fixed code, and a benchmark that reports misses.
- **Why not just have an LLM write tests?** We tried that as a baseline: spec-written blind tests caught 15/15 too. On a precise spec they're as good. Doppel needs no one to write tests or oracles, and its verdict is deterministic and reproducible. We don't claim to beat them here.
- **Don't the twins share mistakes?** Sometimes. Both twins are Meta models (two different model lines), so that risk is real; a different algorithm, spec-cited rules and the benchmark limit it. We tried other vendors but they didn't work in time.
- **Did you hand-fix the twins?** No. They are committed unedited with model, prompt hash and timestamp in the header, and can be regenerated.
- **Was the bug in PR #3 written by you?** No. It's the first non-equivalent mutant our seeded tool produced for that file; the PR body says so.
- **Does it scale beyond one pure function?** Not yet. Today it targets pure functions with a written spec: money, dates, parsing. Stateful classes are next.
- **What if the spec is ambiguous?** The QUESTION path (all three versions disagree, so ask the human) is built and unit-tested, but in this demo function the models agree wherever the spec is clear, so we don't have a natural live example. We won't fake one.
- **What if both twins are wrong and the PR is right?** The PR is wrongly blocked, but the ledger shows every output, so a human sees it immediately. A false block is safer than a false merge.
