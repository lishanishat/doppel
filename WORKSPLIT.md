# Doppel — work split (two people, both coding through AI agents)

Written 12:40 pm, Sat Nov 7. **Submissions due 5:00 pm.** Read this whole file, then give
`CLAUDE.md` + this file to your coding agent (Claude Code or Cursor) as context.

---

## 1. The idea in 60 seconds

**Doppel** is a verifier for AI-written code, delivered as Fetch.ai agents you use from an ASI:One
chat.

1. In ASI:One you type **"Verify PR #2"**.
2. Doppel reads the PR and the issue (spec) from GitHub.
3. A separate agent rebuilds the same function **from the spec only, twice**: Twin A with a Meta
   model (normal approach) and Twin B with SubQ Snap (deliberately naive brute force). The twins
   never see the PR.
4. The engine runs PR + Twin A + Twin B on thousands of generated inputs (Hypothesis), shrinks every
   disagreement to the smallest input, re-runs it twice to rule out flakiness, and **votes**.
5. Fixed code, not an LLM, decides:
   - **BLOCKED** — PR outvoted 2–1 (with the counterexample), or it breaks a spec-cited rule
   - **QUESTION** — all three disagree → the spec is ambiguous → one precise question to the human
   - **UNPROVEN** — not enough evidence (a twin failed, out of scope, question unanswered)
   - **VERIFIED on N inputs** — never "proven correct"
6. The verdict comes back in the chat and as a GitHub review.
7. A benchmark of automatically generated bugs (mutants) shows Doppel's catch rate vs the PR's own
   tests and LLM-written tests, **misses included**. On stage, a judge picks a number and Doppel
   verifies that mutant live.

Pitch: *"AI checking AI shares its blind spots. Doppel rebuilds your code independently and makes the
versions argue. It finds where your code is wrong, and where your spec is ambiguous."*

Full design, rules, demo script and risks: **`CLAUDE.md`** (source of truth; don't reopen the idea).

---

## 2. How the split works (why nobody waits)

- **Two halves that meet at one function:** `engine.api.verify(request) -> evidence`.
  - **Lisha = Fetch side** (agents, ASI:One, GitHub, twin generation, LLM-generated artifacts, demo
    repo, README, videos, submission).
  - **Teammate = Engine side** (spec + reference function, harness, Referee, voting, rules,
    verdicts, ledger, mutants, benchmark).
- **The contract is already written and committed:** `contract/types.py` defines every request and
  response shape. `contract/fixtures/*.json` holds example responses.
- **Every cross-boundary function already exists as a working stub** that returns fixtures:
  `engine/api.py`, `bench/api.py`, `twins/api.py`. Stubs are on by default (`DOPPEL_STUBS=1`).
  - Lisha builds the whole ASI:One flow against stubbed verdicts from minute one.
  - Teammate builds the Referee against placeholder versions (the reference function plus
    hand-mutated copies in `engine/tests/`) until real twins land.
- **Going "real" is a flag flip, not a meeting:** each side replaces its own stub bodies, then
  `DOPPEL_STUBS=0`.
- **No shared files to fight over:** each person owns separate folders (section 4).
- **Handoffs are pushes to `main`, each with a fallback** so the receiver keeps working if it's late
  (section 5).

---

## 3. Fixed decisions (so neither agent has to ask)

- **Demo function:** `prorate_refund(price: str, period_start: str, period_end: str, cancel_date: str) -> str`
  - Refund for the unused part of a billing period, rounded to cents; decimals and dates are
    strings (`"12.34"`, `"2026-02-28"`). Invalid input raises an exception.
  - **Fallback** (if twins catch nothing, or most disagreements are 3-way splits):
    `invoice_tax(lines: list[dict], rate: str) -> str`, where each line is
    `{"amount": "12.34", "qty": 2}`.
- **Language:** everything in Python 3. All three versions (PR, twins) are Python.
- **Harness wire format:** JSON lines over stdin/stdout. A result is `{"ok": true, "value": ...}`,
  an error is `{"ok": false}`. Compare raised-vs-not, never exception class names.
- **Twin files:**
  - `twins_cache/<function_name>/twin_a.py` and `twin_b.py`, plus `manifest.json` (a list of
    `{name, model, prompt_hash, created_at, entrypoint}`).
  - Each twin file starts with a comment header: model, prompt hash, timestamp.
  - **Committed unedited.**
- **Spec files:** `demo_target/<function_name>/spec.md` (the issue text; the signature is the first
  line) and `demo_target/<function_name>/reference.py` (our correct implementation).
- **Demo GitHub repo:** `lishanishat/doppel-demo` (public), separate from this repo. It holds the
  issue, and the AI-written PR with its own tests.
- **The AI PR is written by a fresh coding-agent session given only the issue text.** Record which
  model wrote it. Never hand-craft a bug. If the AI's PR is correct, apply a seeded mutant and say
  so on stage.
- **Models:** Meta Model API and SubQ Snap 1.1 only (those are the keys we have). Their
  OpenAI-compatible base URLs and model names are **unverified** — check the provider docs first.

---

## 4. Ownership (only edit your own folders)

| Path | Owner | Notes |
|---|---|---|
| `agents/` | Lisha | Orchestrator + Twin builder uAgents, chat protocol, mailbox, GitHub review, reply formatting |
| `twins/` | Lisha | `api.py` real `build_twins`, `generate.py` CLI |
| `common/llm.py` | Lisha (create it) | Meta + SubQ clients from env, temperature 0, retries. Teammate imports it later |
| `twins_cache/` | Lisha | Generated twins, committed unedited |
| `bench/llm_artifacts/` | Lisha | LLM-written blind tests; "found in the wild" AI implementations |
| `README.md`, `docs/` | Lisha | Teammate writes `docs/BENCH.md`; Lisha links it |
| `demo_target/` | Teammate | spec.md, reference.py, input schema / Hypothesis strategies |
| `engine/` | Teammate | protocol, harness, referee, rules, verdict, ledger, `api.py` real body, `cli.py` |
| `bench/` (except `llm_artifacts/`) | Teammate | `mutate.py`, `api.py` real body, baselines runner, `run_bench.py`, chart |
| `contract/` | **Frozen** | Change only after telling the other person. Adding optional fields is OK |
| `requirements.txt` | Both | Append-only |
| `CLAUDE.md`, `WORKSPLIT.md` | Lisha | — |

**Git:** both push straight to `main`. Run `git pull --rebase` before every push. Commit at least
every 30 minutes with clear messages: the commit history is our proof of what was built today.
Never commit `.env`.

---

## 5. Handoffs (pushes to `main`, each with a fallback)

| # | By | From → To | What lands | Receiver's fallback until then |
|---|---|---|---|---|
| H1 | **1:05** | Teammate → Lisha | `demo_target/prorate_refund/spec.md` + `reference.py` | Lisha keeps doing ASI:One setup |
| H2 | **1:50** | Lisha → Teammate | Real twins in `twins_cache/prorate_refund/` | Teammate uses placeholder versions |
| H3 | **2:00** | Teammate → both | **Switch decision**: twins vs reference disagreement measured; keep proration or switch to `invoice_tax` | — (if switching: Teammate writes the new spec in ~20 min, Lisha regenerates twins in ~5) |
| H4 | **2:40** | Teammate → Lisha | Real `engine.api.verify` + `answer_question` (`DOPPEL_STUBS=0` works) | Lisha keeps building against fixtures |
| H5 | **2:45** | Lisha → Teammate | `common/llm.py` + LLM blind tests in `bench/llm_artifacts/` | Teammate builds the benchmark with the PR-tests baseline first |
| H6 | **3:00** | Teammate → Lisha | Real `bench.api.get_mutant(n)` (seeded, held-out split) | "Verify mutant #N" uses the fixture mutant |
| H7 | **3:15** | Lisha → Teammate | AI-written PR + its own tests in `doppel-demo` (and copied to `demo_target/prorate_refund/ai_pr/`) | Benchmark runs without the PR-tests baseline |

If a handoff is more than 15 minutes late, say so in the team chat with a new ETA. **Don't wait —
keep working on the next item.**

---

## 6. Lisha — Fetch side

**Human-only steps** (agents can't do these): Agentverse account + API key, ASI:One account,
**Meta credit claim before 3:00 pm** (dev.meta.ai, billing, Team ID, same email), SubQ console key,
GitHub token, chatting in ASI:One to test, recording videos, submitting.

| Time | Task | Done when |
|---|---|---|
| 12:45–1:20 | **F1.** From Fetch's `fetch-hackathon-quickstarter`, build `agents/orchestrator.py` (uAgents + Agent Chat Protocol + Agentverse mailbox). Register it; message it from ASI:One. Test: (a) does ASI:One show a **second (follow-up)** message? (b) how long before ASI:One gives up waiting? Claim Meta credits. | Reply appears in ASI:One; answers to (a) and (b) written in `docs/FETCH_NOTES.md` |
| 1:20–1:50 | **F2.** `common/llm.py` (Meta + SubQ, from env, temperature 0, 3 retries). Real `twins.api.build_twins` + `twins/generate.py`: Twin A = Meta, normal; Twin B = SubQ, deliberately naive brute force. Prompt = raw spec text + signature only. Write the cache + header + manifest. Generate twins for `prorate_refund`. | **H2 pushed** |
| 1:50–2:40 | **F3.** Orchestrator against stubs: parse `Verify PR #N`, `Verify <github PR URL> <function>`, `Verify mutant #N`, and answers to QUESTIONs. Instant ack ("running ~N inputs across 3 versions…") then the verdict as a follow-up (or capped fuzzing if follow-ups don't work). Reply readable in 5 s: verdict, input, the three outputs, vote, reason. All errors become UNPROVEN with a reason, never a crash. `agents/twin_builder.py` as a second registered agent that wraps `build_twins`; the Orchestrator asks it over the chat protocol. | All four stub verdicts render well in ASI:One |
| 2:40–2:55 | **F4.** LLM blind tests: generate pytest tests from the spec only (Meta model) into `bench/llm_artifacts/`. | **H5 pushed** |
| 2:55–3:20 | **F5.** Create public `lishanishat/doppel-demo`: issue = spec.md; then a **fresh** agent session given only the issue writes the implementation + its own tests as PR #2 (record the model). GitHub reader (PR file + issue text) and **posting a review** with the verdict. Copy the PR into `demo_target/prorate_refund/ai_pr/`. | **H7 pushed**; review posts on PR #2 |
| 3:20–3:40 | **F6.** Flip to real: `DOPPEL_STUBS=0`. Run "Verify PR #2" and "Verify mutant #N" end to end in ASI:One. Fix integration bugs. | **BLOCKED in ASI:One, end to end, real** |
| 3:40–3:50 | Stretch, only if F6 works: (1) Interactive Card for the verdict (check the Fetch docs; keep a text fallback), then (2) Payment Protocol. | Hard stop 3:50 |
| 3:50–4:20 | README: what it is, setup, run, `doppel bench`, a **"Built during the hackathon"** section, the Innovation Lab badge, the agent's ASI:One handle. Push. Rehearse together. | Fresh README |
| 4:20–4:40 | Record the one-minute submission video (+ the backup full-run video if Teammate hasn't). | Video link works |
| 4:40–5:00 | Submit on Cerebral Valley (add the teammate, public repo, video) **and** register via the ASI:One Submission Agent. | Submitted |

---

## 7. Teammate — Engine side

No accounts are needed before ~2:45 (the blind tests come pre-generated from Lisha). Your agent
writes everything.

| Time | Task | Done when |
|---|---|---|
| 12:45–1:05 | **E1.** `demo_target/prorate_refund/spec.md`: the issue text, signature on the first line, precise numbered rules including "a refund is never negative"; leave one genuinely ambiguous point (does the cancel day count as used?) for the QUESTION demo. `reference.py`: a correct implementation using `Decimal`. `schema.py`: Hypothesis strategies for the inputs, biased to month ends, leap days, zero and limits. | **H1 pushed** |
| 1:05–1:50 | **E2.** `engine/protocol.py` (normalization), `engine/harness.py` (one long-lived subprocess per version, JSON lines, per-call timeout, restart on crash/hang), `engine/referee.py` (Hypothesis drives all three versions on the same inputs; record disagreements). Test with placeholder versions in `engine/tests/`. | Referee finds a disagreement between the reference and a broken copy |
| 1:50–2:00 | **E3.** Pull H2. Run twins vs reference on ~2,000 inputs: disagreement rate and 3-way split rate. Decide keep or switch (rule in `CLAUDE.md` §10). | **H3 posted** |
| 2:00–2:40 | **E4.** Shrinking, confirm-twice on restarted processes (flaky → excluded), voting, `engine/rules.py` (2–3 spec-cited invariants: active only if they quote a spec line and pass on ≥1 twin), `engine/verdict.py` (the decision table in `CLAUDE.md` §6, in order), `engine/ledger.py` (writes `ledgers/<run>.json` with the fields in §7), regression store for `answer_question`, `engine/cli.py`. Real body of `engine.api.verify`. | **H4 pushed**: `DOPPEL_STUBS=0 python -m engine.cli verify ...` gives BLOCKED on a buggy version |
| 2:40–3:00 | **E5.** `bench/mutate.py`: AST mutation operators (flip comparison, swap arithmetic, off-by-one constant, remove a check), **seeded**; split dev/held-out **before tuning anything**; mark likely-equivalent mutants. Real body of `bench.api.get_mutant` / `list_mutants`. | **H6 pushed** |
| 3:00–3:40 | **E6.** `bench/run_bench.py` (`doppel bench`): for each held-out mutant, run the baselines (the PR's own tests from H7; the LLM blind tests from H5) and Doppel. Report catch rate per method, misses **by name**, likely-equivalent count, false alarms on the correct reference, time and cost per run. Save the chart PNG + `docs/BENCH.md`. **Only real numbers.** | Real chart exists |
| 3:40–3:50 | Stretch: one metamorphic rule, or start "found in the wild" (`CLAUDE.md` §9.4) if Lisha generated implementations. | Hard stop 3:50 |
| 3:50–4:20 | Rehearse three full demo runs with Lisha; record the backup full-run video; pre-pick three mutant numbers known to finish fast. | Three clean runs |
| 4:20–4:40 | Fresh-clone test: follow the README from scratch on a clean checkout. Fix anything that fails. | README works |

---

## 8. Cut order (if behind, cut from the top)

1. Interactive Card / Payment Protocol (Lisha)
2. Metamorphic rule / "found in the wild" (Teammate)
3. LLM blind-test baseline (keep the PR-tests baseline)
4. Twin builder as a separate agent (call `build_twins` in-process instead)
5. Live "Verify mutant #N" (fall back to three pre-picked mutants)

**Never cut:** "Verify PR #2" → real BLOCKED inside ASI:One; the benchmark with misses; rehearsal.

---

## 9. First prompt to give your agent

**Lisha (Fetch side):**
> Read CLAUDE.md and WORKSPLIT.md in this repo. I am the Fetch side (WORKSPLIT §6). Only edit the
> folders I own (§4). Build against the stubs in engine/api.py, bench/api.py and twins/api.py;
> never change contract/. Start with task F1: an Orchestrator uAgent with the Agent Chat Protocol
> and an Agentverse mailbox, based on Fetch's fetch-hackathon-quickstarter. Check the uAgents and
> chat-protocol APIs against the Fetch docs and examples linked in CLAUDE.md §2, not from memory.
> Tell me exactly which human steps I need to do (accounts, keys) and when.

**Teammate (Engine side):**
> Read CLAUDE.md and WORKSPLIT.md in this repo. I am the Engine side (WORKSPLIT §7). Only edit the
> folders I own (§4); never change contract/ (contract/types.py is the interface I must implement).
> Start with task E1 (spec.md, reference.py, schema.py for prorate_refund), commit and push it
> (handoff H1), then E2. Use Hypothesis. The verdict must be decided by fixed code (CLAUDE.md §6),
> never an LLM. Never fabricate benchmark numbers.

---

## 10. Setup (both, ~3 minutes)

```bash
git clone https://github.com/lishanishat/doppel.git && cd doppel
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
DOPPEL_STUBS=1 python -c "from engine.api import verify; print(verify({'function_name':'f','spec_text':'s','versions':[]})['verdict'])"   # prints BLOCKED
```
