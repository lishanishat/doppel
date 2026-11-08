# Doppel

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

**Verify AI-written code by rebuilding it independently from the spec and making the versions argue.**
Built at the AIE Code Summit 2026 hackathon (Nov 7, 2026) for *Trust but Verify* and the Fetch.ai track
*Agents That Prove Their Work*.

> AI checking AI shares its blind spots. Doppel rebuilds your code independently and makes the versions argue.
> **LLMs propose evidence; code decides.**

## What it does

You talk to Doppel in an **ASI:One** chat. Give it a pull request and it:

1. Reads the PR and the linked issue (the spec) from GitHub.
2. Asks a separate **Twin builder** agent for two independent rebuilds of the function, written from the spec text
   only: Twin A (`meta/muse-spark-1.3`, normal approach) and Twin B (`gemini/gemini-3-flash-preview`, a different vendor, deliberately naive,
   literal, brute-force). The twins never see the PR's code.
3. Runs the PR and both twins as separate processes on the same generated inputs (Hypothesis), shrinks every
   disagreement to the smallest input that reproduces it, and re-runs it twice on fresh processes to rule out
   flakiness.
4. **Fixed code, never an LLM, decides** the verdict:

| Verdict | When |
|---|---|
| **BLOCKED** | The PR is outvoted 2-1 on a confirmed input, or breaks an active spec-cited rule. Returns the counterexample. |
| **QUESTION** | All three versions disagree, so the spec is likely ambiguous. Asks one precise question; the answer becomes a saved regression test. |
| **UNPROVEN** | Not enough evidence: a version failed to build or run, input out of scope, or a question unanswered. |
| **VERIFIED on N inputs** | All versions agree on N inputs and every active rule holds. Evidence, never "proven correct". |

5. Replies in chat and posts a **GitHub review** (request changes when blocked).

Every run writes an evidence ledger (hashes, models, seed, counterexamples, timings) so a result is reproducible.

## Try it

Open the **doppel-orchestrator** agent in ASI:One (Agentverse address
`agent1qw3l50t8rpzg9dfhpfnyrkpcceuxrmpxd6qtue2rfr86ddh5yg6jkvuue9m`) and use **Chat with Agent** so the message is
addressed to it. Then send:

- `verify pr #2`: an AI-written PR that is correct, so it comes back **VERIFIED**.
- `verify pr #3`: the same code with **one automatically injected bug**, so it comes back **BLOCKED** with a counterexample.
- `verify mutant #N`: verify a seeded, automatically generated mutant of the reference (any held-out `N`).
- `verify <github PR url> <function>`: any PR; out-of-scope functions return UNPROVEN with the reason.

A third agent, the **Coder agent** (Agentverse address `agent1q079huz7les8x0gvgxejagvdavlqzn0d0rqf5q97kerxx6433uxm6afu27c`),
submits its own PR to the Orchestrator over the chat protocol and logs each step (`make coder`; default text
`verify pr #3`, override with `CODER_SUBMIT_TEXT`). The Twin builder's address is
`agent1q0kqwvkmemtmpxeu2l56yt9qgc9p07q4legc98t9rlqxrcd9hxgawqlnk8c`.

PR #3 in `doppel-demo` is the AI-written code plus one automatically injected mutation. - `verify custom` + a spec + a Python function: **bring your own function** (live). Doppel asks Meta to write test inputs, then Meta and Gemini rebuild your function from your spec, then compares all three. Takes about 1.5 to 5 minutes. Scope: pure Python (standard library) functions with JSON-able arguments and return values. Format and examples: `docs/CUSTOM.md`, `examples/custom/`; run it without ASI:One with `python scripts/custom_check.py FILE`.

The demo target lives in a separate public repo: https://github.com/lishanishat/doppel-demo (issue #1 is the spec).

## Benchmark (measured, 15 held-out mutants)

All numbers come from `python -m bench.run_bench` (raw data `bench/results.json`, full report `docs/BENCH.md`).
Mutants are generated automatically by seeded AST operators from a correct reference and split into dev and
held-out *before* tuning anything; likely-equivalent mutants are excluded and counted.

| Method | Caught | Rate |
|---|---|---|
| Doppel (BLOCKED) | 15/15 | 100% |
| The AI-written PR's own tests | 13/15 | 87% |
| LLM-written blind tests (from the spec) | 15/15 | 100% |

False alarm on the correct reference: none. A Doppel run takes about 0.4 s with cached twins.

**Read this honestly.** Doppel clearly beats the PR's own tests (they missed `#1` and `#13`, listed by name in
`docs/BENCH.md`), but on this function it only *matches* spec-written blind tests. The benchmark is small (15
mutants, one function) and the spec is precise, which favors any approach that encodes it. What Doppel adds is that
no one has to write tests or an oracle, the verdict is deterministic and reproducible, and a three-way split exposes
an ambiguous spec. A baseline test only counts if it also passes on the correct reference (one test in each
baseline failed there and was excluded).

## Real AI code study

Five more implementations of the spec, each written by a fresh coding agent (Claude Sonnet, Haiku and Opus) from the issue text only: all 5 are correct on 3000 generated inputs, and Doppel returned VERIFIED for all 5, so no false alarms on real AI-written code. Checking inputs the spec doesn't define, all 8 AI-written versions reject the price `"1.500"` while our own reference accepts it, and the Meta and Gemini twins disagree with each other on formats such as `".5"`. Details and the honest caveats: `docs/WILD.md`.

## Limitations

- **Independence is partial.** The twins come from two vendors (Meta and Google Gemini) and use different
  algorithms, but shared mistakes are still possible (SubQ Snap is a decision model that can't write code, so it is not
  used). Differing algorithms and spec-cited rules reduce this, and the
  benchmark counts what slips through.
- **Scope today:** pure functions with a written spec (money, dates, parsing, limits). No databases, UIs, network
  calls, concurrency or performance.
- **"VERIFIED on N inputs" is evidence, not proof.**
- The **QUESTION** path is implemented and unit-tested but has no natural trigger in the demo function: the twins
  agree everywhere the spec is clear. Its replies in the repo's stubs are labeled fixtures.
- The Orchestrator runs on a laptop behind an Agentverse mailbox.

## Run it yourself

Needs `uv` (if it is not on your PATH, use `python3 -m uv` in its place).

```bash
git clone https://github.com/lishanishat/doppel.git && cd doppel
uv venv -p 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt   # uagents needs Python 3.12
cp .env.example .env     # fill in MODEL_API_KEY (Meta), two random seed phrases, optionally GITHUB_TOKEN
.venv/bin/python -m pytest                      # unit tests
.venv/bin/python -m bench.run_bench             # the benchmark (writes docs/BENCH.md and docs/bench.png)
DOPPEL_STUBS=0 .venv/bin/python -m engine.cli --help   # run the engine from the command line
make test            # same as the pytest line above
make bench           # same as the benchmark line above (about 3 minutes)
make demo            # scripted demo run (scripts/demo_run.sh)
make twin-builder    # terminal 1: Twin builder agent (port 8004)
make orchestrator    # terminal 2: Orchestrator agent (port 8003)
```

Recovery demo: kill a twin mid-run and get a plain-English UNPROVEN instead of a crash
(tested in `engine/tests/test_chaos.py`):

```bash
.venv/bin/python -m engine.cli verify --fn prorate_refund --pr demo_target/prorate_refund/ai_pr/billing.py --chaos twin_b
```

Plant your own bug: `python scripts/plant_bug.py FILE LINE OPERATOR` applies one automatic mutation (`--list` shows
the sites). Six recorded plants are in `docs/live_bug_notes.md`: 5 blocked, 1 not blocked (a removed check that a later
regex check makes redundant), each in about 0.6 s.

Then open each agent's Agent Inspector link from its log, **Connect → Mailbox**, and chat with the Orchestrator
from its Agentverse profile. `DOPPEL_STUBS=1` (the default in `.env.example`) answers with labeled fixtures; set it to
`0` for the real engine. Cached twins live in `twins_cache/` with a header recording model, prompt hash and
timestamp, and are committed unedited (regenerate with `python -m twins.generate --spec ... --function ...`).

## Architecture

```
ASI:One user ──chat protocol──> Orchestrator ──> GitHub (read PR + issue, post review)
                                    │  ├──chat protocol──> Twin builder ──> Meta Model API (Twin A, Twin B)
                                    │  └──> engine: isolated processes, Hypothesis, shrink, confirm x2, vote, rules, verdict
                                    └──> evidence ledger (ledgers/*.json)
```

- `agents/`: Orchestrator and Twin builder (uAgents, Agent Chat Protocol, Agentverse mailbox), command parsing,
  GitHub client, reply formatting.
- `engine/`: harness, Referee, rules, verdicts, ledger, regression store.
- `bench/`: seeded mutation, baselines, benchmark runner.
- `twins/`, `common/`: twin generation and the model client. `contract/`: the interface between the two halves.
- `demo_target/`: the spec, a hand-written correct reference, input generators, and a copy of the AI-written PR.

## Built during the hackathon

Everything in this repository was written during the AIE Code Summit hackathon on Nov 7, 2026, by
**Lisha Nishat** and **Manank Maheshwari**, with AI coding agents (Claude Code), starting from an empty repository.
The commit history is the record. The Fetch quickstarter (`fetchai/innovation-lab-examples`) was used as the
reference pattern for the agent shell, and the demo PR (#2 in `doppel-demo`) was written by a fresh coding agent from
the issue text alone. No bug was hand-written; mutants are generated by the seeded tool in `bench/mutate.py`.
