# Project context: Doppel (AIE Code Summit 2026 hackathon, Fetch.ai track) — v2

## FINAL STATE (v3, Nov 7 ~3 pm): supersedes the plan below where they differ

- Twins come from two vendors: Twin A `meta/muse-spark-1.3`, Twin B `gemini/gemini-3-flash-preview` (deliberately naive; adopted ~3:45 pm after it matched the reference on 3000 inputs and the benchmark was unchanged). SubQ Snap is a decision model that cannot write code. Real-AI-code study: docs/WILD.md. No Subquadratic usage.
- Spec gap closed: cancel before period start = full refund.
- QUESTION demo dropped (no natural trigger in the demo function); the path is built and unit-tested.
- A Coder agent exists: it submits its PR to the Orchestrator and logs each step.
- Chaos/recovery test added (`--chaos`): a killed version yields UNPROVEN with a plain-English reason.
- PR #2 (doppel-demo) is correct and comes back VERIFIED; PR #3 has one auto-injected mutation and comes back BLOCKED.
- Benchmark (docs/BENCH.md), 15 held-out mutants: Doppel 15/15 (100%), PR's own tests 13/15 (87%), LLM blind tests 15/15 (100%).
- Honest note: blind tests tie Doppel on this function; we match them, we do not beat them.
- No false alarm on the correct reference; about 0.4 s per run with cached twins.
- The Orchestrator runs locally on a laptop with an Agentverse mailbox.

---

This file hands off everything decided in planning (claude.ai, 9:11–11:23 am, then Claude Code,
11:30 am–12:02 pm Pacific, Saturday Nov 7, 2026). **Read all of it before writing code.**
v1 of this file is saved as `CLAUDE.v1-backup.md`; this version supersedes it.

---

## 0. TL;DR for Claude Code

- **Who:** Lisha (SJSU Data Science student) and one teammate. Team of **two**.
- **Event:** AIE Code Summit 2026 hackathon (Cerebral Valley), Shack15, 1 Ferry Building Suite 201,
  San Francisco.
- **Primary target:** **Best Use of Fetch.ai** (two winners: 1st $2,500, 2nd $2,500).
  **Side bets:** Best Use of Meta Model API ($5,000), Best Use of Subquadratic (1st $5,000 + credits),
  overall track (1st $3,000 / 2nd $2,000 / 3rd $1,000 + extras).
- **Deadline:** **5:00 pm Pacific, submissions due (confirmed on the event page).** Round 1 judging
  5:00–6:45 pm, finals 7:00–8:00 pm, winners 8:15 pm. Demos happen after the code freeze: no risky
  pushes between submitting and demoing.
- **Problem statement:** "Trust but Verify". Fetch track: "Agents That Prove Their Work".
- **Project:** **Doppel** verifies AI-written code by having independent agents rebuild the same
  function from the spec alone (different model families, one deliberately naive algorithm), fuzzing
  all versions on thousands of generated inputs, and letting fixed code (not an LLM) decide:
  **BLOCKED / QUESTION / UNPROVEN / VERIFIED on N inputs**.
- **Lead claim:** "Doppel tells you two things: where your code is wrong, and where your spec is
  ambiguous."
- **Status at 12:02 pm:** idea final and locked (re-judged several times; do not reopen it).
  **No project code written yet.** Build plan in section 15.
- **What Lisha wants:** brutally honest, critical, accurate judgment; a winning project; execution
  and a reliable live demo over extra features.

### Changes from v1 (all decided)

1. **JavaScript twin cut.** Twin B is a deliberately naive **Python** twin from a different model
   family. Diversity = model family + algorithm.
2. **Twin models:** Twin A = Meta Model API, Twin B = SubQ Snap 1.1 (both free credits; makes the
   Meta and Subquadratic prizes possible). Any other provider is the fallback; never block on them.
3. **Coder agent cut.** Two agents: Orchestrator (runs the Referee) and Twin builder.
4. **QUESTION (spec ambiguity) case moves into the main demo**, replacing the Coder-agent segment.
5. **Honest baseline:** "existing tests" = the AI-written PR's **own** tests (not tests we write).
   LLM-written blind tests are the second baseline.
6. **Any PR URL + function name accepted**; out-of-scope input returns UNPROVEN with a reason.
7. **Judge picks a number → "Verify mutant #N"** live (seeded mutant from the held-out set), instead
   of a judge hand-writing a bug. Answers "is the demo staged?".
8. **Instant acknowledgement + follow-up verdict** in ASI:One to survive reply timeouts.
9. **Benchmark misses shown on stage by name.**
10. **New first stretch: "found in the wild" study** (section 9.4) — the single biggest lever on the
    score, only if the 1:00 checkpoint is hit.
11. **Laptop hosting:** run `caffeinate -dims` during judging.
12. **Payment Protocol moved from "cut" to stretch 3** (after the Interactive Card): pay per
    verification is a credible monetization model, and Fetch has a Stripe test-mode example.

### Why each change was made

1. JS twin: the cross-language harness (number formats, error mapping, Node process) was the biggest
   time sink and the main source of false blocks; frees ~1 hour for benchmark and rehearsal.
2. Meta/SubQ twins: two model families are needed anyway, so sponsor prize eligibility costs almost
   nothing. Sponsor "Best Use" prizes usually reward central use; here the models are one of two twin
   writers, so treat those prizes as long shots.
3. Coder agent: Orchestrator + Twin builder already count as multi-agent; the Coder agent was
   theater that cost reliability time.
4. QUESTION in demo: ambiguity detection is the most original part; in Q&A only, most judges would
   never see it.
5. Baseline: tests we wrote ourselves would look rigged; the PR's own AI-written tests are the
   realistic case (same model wrote code and tests).
6. Any PR URL: reliability bonus, and lets judges try it themselves.
7. Judge-picked mutant: every judge suspects a staged demo; a seeded random mutant nobody chose is
   faster and more predictable than a judge typing a bug.
8. Instant ack: ASI:One reply timeouts are unverified; fuzzing may exceed them.
9. Misses on stage: disarms "don't LLM versions share mistakes?"; judges rarely see teams report
   their own failure rate.
10. "Found in the wild": real bugs in real frontier-model code is the one lever that raises every
    criterion (impact, demo, creativity, difficulty) at once.

The v1 claude.ai outline (https://claude.ai/artifact/7cYHDVdwfa3HaqyX4G88AA) is **out of date**;
this file is the source of truth.

---

## 1. Hackathon facts (confirmed from the event page)

Event page: https://cerebralvalley.ai/e/aie-code-2026-hackathon/details

**Schedule (Sat Nov 7):** 9:00 doors · 10:00 kickoff · **10:45 hacking began** · 1:00 lunch ·
**5:00 submissions due** · 5:00–6:45 Round 1 judging · 6:00 dinner · 7:00–8:00 finals · 8:15 winners ·
10:00 doors close.

**Problem statements** (project must fit at least one):

1. **The System That Gets Better.** Autonomous coding system that completes a hard, tightly coupled
   software task and improves itself as it works; each failure becomes a versioned change to its
   skills, tools, routing or context; each change proves itself on held-out work; adopt only
   confirmed changes, roll back the rest.
2. **Software Archaeology.** Recover, rebuild, port or extend authorized software from incomplete
   evidence; ship behavioral evidence separating observed from inferred; prove behavioral
   equivalence across platforms, languages or runtimes.
3. **Trust but Verify** (Doppel). AI writes code faster than teams can check it. Build an independent
   verifier that evaluates AI-generated changes, catches defects, and blocks or rolls back anything
   below the standard. How can a verifier write its own tests without sharing the implementer's blind
   spots, and stay independent, reproducible and hard to game?

**Rules:**
- Repositories must be **public**.
- Max four members; solo allowed. (We are two.)
- Demo must only highlight features, code and functionality **built during the hackathon**; judges
  must be able to clearly identify what was created during the event, or **immediate
  disqualification**.
- New work only; clearly distinguish your contributions.
- Disqualified for violating legal/ethical/platform policies or using code, data or assets you lack
  rights to.

**Banned anti-projects:** AI mental health advisor; basic RAG apps; **Streamlit apps**; image
analyzers; "AI for Education" chatbot; AI job application screener; AI nutrition coach; personality
analyzers; AI medical advice; **any project where a dashboard is the main feature**; sports
analyzers/coaches. → The benchmark chart is **one slide**, never the centerpiece. No frontend.

**Judging:**

| Criterion | Round 1 | Finals (top 6, on stage) |
|---|---|---|
| Impact Potential: significant real-world pain point? | 20% | 25% |
| Technical Demo: impressive, well-engineered, working? | 35% | 25% |
| Creativity: never seen before? | 15% | 25% |
| Implementation Difficulty: more than a few AI prompts away? | 30% | 25% |

~3 min live demo + 1–2 min Q&A in both rounds.

**Submission:** Cerebral Valley form (https://cerebralvalley.ai/e/aie-code-2026-hackathon/hackathon/submit)
with a **one-minute demo video** of what was built during the hackathon. Repo public, demo link
accessible, **all team members added**. Then **also** register via the ASI:One Submission Agent
(section 2).

**Partner resources:**
- **Meta:** $100 Model API credits. **Claim closes 3:00 pm PT.** Steps: create account at dev.meta.ai;
  complete billing with a valid payment method (promo credits don't bypass billing verification);
  Team ID = 15–17 digit number after `team_id=` in the dev.meta.ai URL; use the **same email** as the
  hackathon acceptance; submit the claim form (linked on the event page). Credits arrive in batches;
  **don't make calls until credits appear** if you don't want the card charged; set a spending
  notification. If credits are late, ask at the Meta booth. Docs: https://dev.meta.ai/docs/overview,
  quickstart https://dev.meta.ai/docs/quickstart, models https://dev.meta.ai/docs/models, cookbook
  https://github.com/meta-models/meta-model-cookbook (includes "Muse Code" recipes).
- **Subquadratic:** 100M free tokens for SubQ Snap 1.1 at console.subq.ai.
- **Meta claim form:** https://docs.google.com/forms/d/e/1FAIpQLSdQuKkkBi-RT4ExsK96yonl-L8kwFvaFiT9xA43SnZqkRxVyA/viewform?usp=header
- **Google DeepMind guide:** https://docs.google.com/document/d/1kN0n6hPNNTIHMVqf5-hDACrZuIg4KFrWiYpla4WQW8w/edit?usp=sharing
- **MongoDB:** code `MKT-BUILDERS-100` ($100 credits). Not used.

**Help:** Discord https://discord.com/invite/TAsaaxcXB (#questions, ping @CV; #announcements for
updates); organizer email gina@cerebralvalley.ai.

---

## 2. Fetch.ai challenge guide

Source: https://docs.google.com/document/d/1z7ybvx9I80KI-n4DEieN9i11Zoj4ki4TTvtUWqnULQQ/edit?usp=sharing

**Track: "Agents That Prove Their Work."** Build an AI agent, discoverable through ASI:One, that
understands a user's intent and takes meaningful action on a real software problem, and shows
evidence that what it did is correct, safe, or getting better over time. Starting points: agents that
get better; agents that reconstruct the past; agents that verify before they trust.

**Mandatory (prize eligibility):**
1. Register at least one agent on Agentverse (https://agentverse.ai).
2. Implement the Agent Chat Protocol.
3. Discoverable and directly usable through ASI:One (https://asi1.ai).
4. Meaningful tool execution or multi-agent orchestration.
5. Primary user workflow completed **entirely within an ASI:One conversation** (no custom frontend).
6. Public GitHub repo with instructions to run or test.

**Bonus:** multi-agent collaboration; Payment Protocol with credible monetization; ASI Interactive
Cards; reliability, error handling and recovery from failed tool calls; real-time data/external
services; agent that could keep operating after the hackathon. **No scoring weights published.**

**Deliverables:** after Cerebral Valley, register via the AIE Summit ASI:One Submission Agent:
https://asi1.ai/auth/signup?returnTo=%2Ffestival%2Faiesummit2026%2Fdashboard%3Futm_source%3Daiesummit%26skip_onboarding%3Dtrue
Walkthrough video: https://drive.google.com/file/d/1EDfKrM7l8soO-40eKkPYDAEkRUTwQKyf
Submission details: https://docs.google.com/document/d/1U9NUNpSli2vxpKWo233nmt6m01QHl_7ANhNKvdQnM_Y

**Fetch resources:**
- 5-minute setup: https://docs.google.com/document/d/1_Tb76j7zlzodhTiofHX_uPuEIfrDuQ3QAyk7c4osrd4/edit?usp=sharing
- Pre-hack workshop: https://drive.google.com/file/d/1UKOz1kmxXulFWwajimJriH9mi8GiC3B6/view?usp=sharing
- Basic ASI1-compatible agent: https://uagents.fetch.ai/docs/examples/asi-1
- Multi-agent quickstarter (**start here**): https://github.com/fetchai/innovation-lab-examples/tree/main/fetch-hackathon-quickstarter
- Concepts: https://innovationlab.fetch.ai/resources/docs/intro
- Examples repo: https://github.com/fetchai/innovation-lab-examples (see `news-card-agent` for cards)
- Stripe Payment Protocol: https://innovationlab.fetch.ai/resources/docs/examples/agent-transaction/stripe-horoscope-payment-protocol
- Payment agents: https://github.com/fetchai/innovation-lab-examples/tree/main/stripe-payment-agents
- Interactive Cards: https://innovationlab.fetch.ai/resources/docs/interactive-cards/asi-interactive-cards
- OpenClaw orchestrator pattern (local execution): https://innovationlab.fetch.ai/resources/docs/examples/openclaw/openclaw-fetchai-orchestrator
- Past projects: https://innovationlab.fetch.ai/projects
- Add the "Innovation Lab" badge to the README (past events required it; costs nothing).

---

## 3. Pitch and positioning

- **Opening:** "AI checking AI shares its blind spots. Doppel rebuilds your code independently and
  makes the versions argue."
- **Lead claim:** "It finds where your code is wrong, and where your spec is ambiguous."
- **Slogan:** "LLMs propose evidence; code decides."
- **Close:** "Airplanes don't trust one flight computer. Why trust one AI?"
- **Impact line:** "Every team merging AI code has this problem, and the PR's own tests can't catch
  it, because the same model wrote both."

**Distinctive, in priority order:** (1) ambiguity detection: a three-way split becomes one precise
question (most verifiers silently guess); (2) verdict issued by fixed code, never an LLM;
(3) a benchmark that publishes its own misses by name; (4, stretch) real bugs found in real
frontier-model code.

**Do not claim** differential testing / N-version programming is new (it dates to the 1970s).
The novelty is applying it to AI code with ambiguity detection, deterministic verdicts, and an
honest benchmark.

**Common approach vs Doppel:**

| | Common approach | Doppel |
|---|---|---|
| What decides | LLM review or LLM-written tests | Independent rebuilds, fuzzing, spec-cited rules; fixed code |
| Independence | Prompting | Different model family per version + a deliberately naive algorithm |
| Expected outputs | Written by the LLM | Versions check each other; metamorphic rules need none |
| Ambiguous spec | Silently guessed | Detected, turned into one precise question |
| Evidence the verifier works | Usually none | Benchmark vs baselines, misses included |

---

## 4. Architecture

### 4.1 Agents (two, both registered on Agentverse, talking over the Agent Chat Protocol)

| Agent | Job | Sees | Never sees |
|---|---|---|---|
| **Orchestrator** (runs the Referee in-process) | Talks to ASI:One users; parses "Verify PR #N" / "Verify <PR URL> <function>" / "Verify mutant #N" / QUESTION answers; fetches PR file and issue via the GitHub API; runs the spec step; asks the Twin builder for twins; runs the Referee; posts the GitHub review; replies in chat | Everything | — |
| **Twin builder** | Builds Twin A and Twin B from the raw issue text + function signature; caches them by hash; returns them over the chat protocol | Issue text, signature | The PR code |

- **Hosting:** Orchestrator runs on a laptop with an Agentverse **mailbox**, so it executes code
  locally. Run `caffeinate -dims` during judging. Twin builder can run on the same laptop.
- **Start from** Fetch's `fetch-hackathon-quickstarter` (orchestrator + worker pattern).
- **Verify uAgents chat-protocol, mailbox and Interactive Card APIs against the linked Fetch docs and
  examples, not from memory.**
- **Coder agent: cut.**

### 4.2 Models

| Version | Model | Approach |
|---|---|---|
| PR under test | A **third** model family (whatever writes the "AI PR"), recorded in the ledger | Normal implementation + its own tests |
| Twin A | Meta Model API, a coding model (e.g. Muse Code) — **unverified: exact model name/availability** | Normal implementation, Python |
| Twin B | SubQ Snap 1.1 — **unverified: API format** | **Deliberately naive brute force** (e.g. walk day by day), Python |

- Temperature 0. Model, base URL and key from env (`engine/llm.py`).
- **Fallback:** if Meta billing or either API fails, use any other provider key available. Never let
  a sponsor API block the build.
- **Twins get the raw issue text**, never the spec step's summary, so a misread spec can't spread.
- **Twin integrity:** each cached twin file has a header with model, prompt hash and timestamp, and is
  committed **unedited**. Offer a live rebuild if a judge asks.

### 4.3 The demo PR must be honestly AI-written

- Generate the PR (implementation + its own tests) with a third model from the issue text.
- If that PR contains a real bug that fuzzing finds → use it (best case).
- If it's correct → apply a mutant from `bench/mutate.py` and say so plainly: "AI-written PR with an
  automatically injected bug."
- **Never hand-craft the bug.**

---

## 5. Verification engine (the Referee)

1. **Process isolation:** each version runs as its own **long-lived Python subprocess** answering JSON
   lines on stdin/stdout. Starts once, answers many calls. Per-call timeout; a crash or hang is
   recorded as an error, not a disagreement, and the process is restarted.
2. **Shared format:** decimals as strings (`"12.34"`), dates as ISO strings (`"2026-02-28"`), errors as
   `{"ok": false}`. Compare raised-vs-not, never exception class names.
3. **Input generation:** Hypothesis, from the spec step's schema (types, ranges, decimal places),
   favoring edge values: month ends, leap days, zero, limits.
4. **Shrinking:** Hypothesis reduces each disagreement to the smallest input that reproduces it.
5. **Confirmation:** each shrunk counterexample re-run **twice** on freshly restarted processes. Only
   identical repeats count; anything else is labeled flaky and excluded.
6. **Voting:** PR + two twins = three votes, grouped by normalized output per confirmed
   counterexample. 2 of 3 wins. Three-way split = likely spec ambiguity.
7. **Rules (`engine/rules.py`):**
   - **Spec-cited invariants** (aim 2–3, reviewed by hand), e.g. "a refund is never negative". Can
     block only if it quotes its spec line **and** passes on at least one twin; otherwise advisory.
   - **Metamorphic rules** (stretch, 1–2), e.g. "splitting the period in two gives the same total
     refund", "doubling the price doubles the refund". Catch bugs even when all versions agree.
8. **Spec step (`engine/spec_step.py`):** one cached LLM call → input schema + candidate rules.
9. **Live budget:** cap live fuzzing to fit the ASI:One reply window (measured in hour one).

---

## 6. Decision rules (`engine/verdict.py`; fixed code, checked in this order)

| Condition | Verdict |
|---|---|
| PR outvoted 2–1 on a confirmed input | **BLOCKED**, with the counterexample |
| PR breaks an active spec-cited invariant or metamorphic rule | **BLOCKED**, even if all agree |
| All three versions give different answers on a confirmed input | **QUESTION**: one precise question showing all three answers |
| Question unanswered | **UNPROVEN**; never merged on ambiguity |
| A twin fails to build/run, or input out of scope | **UNPROVEN**, with the reason |
| All agree on N inputs and all active rules hold | **VERIFIED on N inputs** (never "proven correct") |

**BLOCKED reply must be readable in 5 seconds:** the input, the three answers side by side, which
version won, the vote, and a link to the GitHub review.

---

## 7. Evidence ledger (`engine/ledger.py`; JSON for every run)

- hashes of the spec, PR code and each twin, with model, prompt hash and temperature
- random seed, number of inputs tried, disagreement rate
- each counterexample with every version's raw and normalized output
- each rule, its cited spec line, active or advisory
- timings, cost per run, exact command to reproduce
- count of saved regression tests

---

## 8. Learning loop (stretch; claim only this)

1. When a QUESTION is answered in ASI:One, save input + expected output + question + timestamp to
   `regression.json`.
2. Every future run checks the PR against all saved regression tests; the ledger reports the count.

Re-scoring the whole setup on held-out bugs after each answer is **future work; do not claim it**.

---

## 9. Benchmark (strongest slide; only real measured numbers)

### 9.1 Mutants
- Generated **automatically** by standard mutation operators on a correct reference (flipped
  comparisons, swapped arithmetic, off-by-one constants, removed checks). **Seeded**, so
  "mutant #N" is reproducible. Nothing hand-picked; report the real count.
- Mutants identical to the correct code on every input tried → "likely equivalent", excluded,
  count reported.
- **Split mutants into dev and held-out sets before tuning anything.** "Verify mutant #N" draws from
  the held-out set.

### 9.2 Baselines

| Method | Counts as caught when |
|---|---|
| The AI-written PR's **own** tests | Any test fails |
| LLM-written blind tests from the issue | Any generated test fails |
| **Doppel** | Verdict is BLOCKED (QUESTION counted separately) |

### 9.3 Report
Catch rate per method on held-out; bugs caught only by rules when all versions agreed; **misses
listed by name**; false-alarm rate on the correct reference; likely-equivalent count; average time
and cost per run. One command: `doppel bench`, which outputs a chart image (one slide, not a
dashboard). Optional (Meta/SubQ stretch): how often each model family's twin disagrees with the
correct reference — report whatever the numbers show.

### 9.4 "Found in the wild" study (FIRST stretch item; only if the 1:00 checkpoint is hit)
- 4–5 realistic business functions with tricky edges: proration, tax rounding, business-day
  counting, a rate-limit window, discount stacking.
- Have current frontier models write each one from the spec, with their own tests, as a coding agent
  would. Run Doppel on all of them.
- Slide: "Doppel found real bugs in X of Y AI-written functions that passed their own tests" plus
  "N genuine ambiguities in specs we thought were clear."
- **Every claimed bug must have its counterexample confirmed against a correct reference we wrote.**
  X may be small or zero; report it honestly. Cost ~45–60 min.

---

## 10. Demo function

- **Primary:** billing proration (refund the unused part of a billing period on cancellation, rounded
  to cents with decimals; leap years and month ends).
- **Fallback:** tax rounding (per-line vs per-invoice).
- **Switch rule (judgment, not measured):** in the first hour, run both twins against the correct
  reference. Switch to tax rounding if (a) twins agree with each other and the reference almost
  everywhere, so nothing would be caught, or (b) most confirmed disagreements are three-way splits, so
  QUESTION drowns everything.
- **Only use demo cases you have actually run.** (v1's 2.675 rounding example was wrong: in Python
  and JS floating point, 2.675 rounds to 2.67.)

---

## 11. Three-minute demo script

Twins built and cached before going on stage; everything else runs live.

| Time | What happens | What to say |
|---|---|---|
| 0:00–0:20 | An AI-written proration PR on GitHub; its own tests pass | "AI checking AI shares its blind spots. Would you merge this?" |
| 0:20–1:10 | ASI:One: "Verify PR #2." Instant reply "running ~N inputs across 3 versions…", then BLOCKED: shrunk counterexample, 2–1 vote, GitHub review posted | "We rebuilt it twice from the spec, once deliberately naively, with two different model families. Code decides, not an LLM." |
| 1:10–1:40 | QUESTION case: all three versions disagree (e.g. does the cancellation day count as used?). One precise question appears | "Most verifiers silently guess. Doppel tells you your spec is ambiguous." |
| 1:40–2:20 | Benchmark slide: held-out catch rates, **misses shown by name** (+ "found in the wild" result if built) | "Here's proof it works, including what it missed." |
| 2:20–3:00 | A judge picks a number → "Verify mutant #N" runs live | "Nobody, including us, chose that bug." |

- If the judge's mutant is likely-equivalent or a miss, say so honestly; it matches the benchmark.
- Show the agent's ASI:One handle on screen so judges can try "Verify mutant #N" from their own
  phones during Q&A.
- Rehearse three full runs. Record a backup video of the full run. Separately record the
  one-minute submission video.

---

## 12. Judge Q&A to rehearse

- "Isn't this N-version programming?" — Yes, applied to AI code; new parts are ambiguity detection,
  deterministic verdicts, and a benchmark that publishes misses.
- "Don't LLM versions share mistakes?" — Sometimes; hence different model families, a naive
  algorithm, spec-cited rules, and a benchmark that counts what slips through.
- "Did you hand-fix the twins?" — No; committed unedited with model and prompt hash; we can rebuild
  one now.
- "Isn't the demo staged?" — You picked the mutant.
- "Only pure functions? Does it scale?" — Targets the riskiest functions chosen by path or label;
  twins cached per function; stateful classes next.
- "What if both twins are wrong and the PR is right?" — False block, but the ledger shows every output
  so a human sees it at once; a false block is safer than a false merge.
- "What does a run cost?" — Give measured time and cost.
- "Will it keep running?" — It's a verification service other coding agents can call over the chat
  protocol; hosted on a laptop today.

---

## 13. Fetch requirement mapping

| Requirement | How Doppel meets it | Priority |
|---|---|---|
| Agent on Agentverse | Orchestrator and Twin builder registered | Mandatory |
| Agent Chat Protocol | Orchestrator ↔ ASI:One; Orchestrator ↔ Twin builder | Mandatory |
| Usable in ASI:One | "Verify PR #2", "Verify <URL> <function>", "Verify mutant #N" | Mandatory |
| Tool execution / multi-agent | Code execution, fuzzing, GitHub API, twin delegation | Mandatory |
| Whole workflow in ASI:One | No custom frontend | Mandatory |
| Public repo + run instructions | README: setup, run, `doppel bench`, "Built during the hackathon" section | Mandatory |
| Reliability (bonus) | Retries on failed tool/model calls; instant ack; UNPROVEN with reason instead of crash | Core |
| Multi-agent (bonus) | Twin builder isolated from the PR | Core |
| Interactive Cards (bonus) | Verdict card with button to post the GitHub review; plain-text fallback | Stretch 2 |
| Payment Protocol (bonus) | Pay per verification, Stripe test mode | Stretch 3 |
| Keeps running (bonus) | Pitch only | — |

---

## 14. Unverified: test before relying on them

1. Does ASI:One show a follow-up message after an instant acknowledgement? How long does it wait for
   a reply? (Person 1, first hour.)
2. Interactive Card message format.
3. Do the Meta and SubQ APIs work with an OpenAI-compatible client? Exact model names?
4. Can one project win multiple sponsor prizes? Ask in Discord #questions.

---

## 15. Build plan (12:00 pm → 5:00 pm; shift if behind)

Person 1 = Fetch side, Person 2 = engine (which teammate is which: not decided). They meet at one
function: `verify(pr_code, spec) -> evidence JSON`.

| Time | Person 1 (Fetch side) | Person 2 (engine) | Checkpoint |
|---|---|---|---|
| 12:00–12:45 | ASI:One "hello" via mailbox from the quickstarter; test follow-up messages and timeout; **claim Meta credits** | Public demo repo (spec issue, correct reference, AI PR + its own tests); generate both twins; quick fuzz; apply the switch rule | Reply in ASI:One; demo function locked |
| 12:45–1:00 | Orchestrator stub: parse "verify PR #N", fetch PR + issue | Referee skeleton: subprocess harness + Hypothesis | **1:00: "Verify PR" works end to end with a stub reply** |
| 1:00–2:15 | GitHub review posting; instant ack + follow-up; retries; UNPROVEN paths; Twin builder agent | Shrinking, confirmation, voting, 2–3 invariants, verdict, ledger | Referee blocks the buggy PR locally |
| 2:15–2:45 | Integrate together | Integrate together | "Verify PR #2" → BLOCKED in ASI:One |
| 2:45–3:30 | "Verify mutant #N" command; QUESTION flow | `mutate.py`, dev/held-out split, baselines, chart | Real benchmark numbers |
| 3:30–3:50 | Stretch: "found in the wild" study, then Interactive Card | Stretch: "found in the wild" study, then metamorphic rule / Meta-SubQ stat | **Hard stop on new work at 3:50** |
| 3:50–4:20 | README ("Built during the hackathon", run steps, badge); push | Three rehearsed runs; backup video | Three clean runs |
| 4:20–4:40 | One-minute submission video | Fresh-clone README test | — |
| 4:40–5:00 | Submit on Cerebral Valley **and** the ASI:One Submission Agent | Buffer | Submitted before 5:00 |

**Cut order if a checkpoint slips:** Interactive Card → Payment Protocol → metamorphic rules →
Meta/SubQ disagreement stat → "found in the wild" study → live "Verify mutant #N" (fall back to a
pre-generated mutant list).
**Never cut:** end-to-end ASI:One flow, benchmark with misses, rehearsal.
**Already cut:** JavaScript twin, Coder agent, stateful mode, assumption diff, LLM-review baseline,
Docker sandbox, any frontend/dashboard.

---

## 16. Repo layout (not yet created)

```
doppel/
  agents/
    orchestrator.py      # uAgents + chat protocol + mailbox; runs Referee; GitHub review; instant ack
    twin_builder.py      # Twin A (Meta) + Twin B (SubQ, naive); cached by hash; header per file
  engine/
    protocol.py          # JSON lines, normalization (decimal strings, ISO dates, ok/err)
    harness.py           # long-lived Python subprocess per version, per-call timeout, restart
    referee.py           # Hypothesis fuzzing, shrinking, confirm-twice, voting
    rules.py             # spec-cited invariants + metamorphic rules (active vs advisory)
    verdict.py           # fixed decision rules
    ledger.py            # evidence JSON
    spec_step.py         # one cached LLM call -> input schema + rules
    llm.py               # provider clients from env, temperature 0, retries
  bench/
    mutate.py            # seeded AST mutation operators
    baselines.py         # PR's own tests; LLM-written blind tests
    run_bench.py         # `doppel bench`: dev/held-out split, catch rates, misses, chart image
    wild/                # (stretch) "found in the wild" functions, specs, references, results
  demo_target/           # (or a separate public repo) spec issue, correct reference, AI PR + its tests
  twins_cache/           # committed unedited twins with header: model, prompt hash, timestamp
  regression.json        # (stretch) answered QUESTIONs
  README.md              # setup, run, `doppel bench`, "Built during the hackathon", Innovation Lab badge
  .env.example
```

---

## 17. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Too much to build by 5:00 | Checkpoints, fixed cut order, hard stop at 3:50 |
| Twins agree with everything, or split three ways too often | Measure in the first hour; switch to tax rounding |
| ASI:One reply times out | Instant ack + follow-up; cap live fuzzing; cached twins |
| Meta/SubQ API or billing fails | Any other provider key as fallback |
| Judges suspect a staged demo | Judge picks the mutant; PR honestly AI-written; twins committed unedited |
| Judges suspect hand-fixed twins | Header with model, prompt hash, timestamp; offer live rebuild |
| Benchmark looks cherry-picked | Automatic seeded mutants, held-out split, misses published |
| Laptop sleeps during judging | `caffeinate -dims` |
| Live demo fails | Backup video; three rehearsed runs |
| Unclear what was built during the event | Commit history + README section |
| Looks like a dashboard project | Chart is one slide; everything else happens in ASI:One |

---

## 18. Honest outlook (Claude's estimates; other teams unknown)

| Scenario | Weighted score (Round 1 weights) |
|---|---|
| Plan as written, everything works | ~7.3 |
| Expected, including failure risk | ~6.6 |
| Plus "found in the wild" with real bugs found | ~8–8.5 |
| Live demo breaks | ~5 |

- Fetch prize: realistic; a complete working ASI:One flow stands out among thin wrappers, and two
  teams win.
- Overall top 3: possible; Trust but Verify is likely the most crowded statement.
- Meta / Subquadratic prizes: long shots; the models are used for real (twin independence) but are
  not the centerpiece.
- What decides the result: **a clean live run and real benchmark numbers, misses included.**
  9–10 is not realistic from design alone.
- v1 self-assessed ~7.8. Revised down after a judge-perspective review: v1 scored the
  everything-works case and was optimistic on creativity and difficulty.

**Weaknesses judges will push on (from that review), and the response:**

| Weakness | Response |
|---|---|
| N-version programming is from the 1970s; other teams can get "compare against a generated reference" from an LLM too. Creativity ~6, not 8 | Lead with ambiguity detection; don't claim differential testing is new |
| "You wrote the spec, the bug and the target" | Judge-picked seeded mutant; honestly AI-written PR; unedited twins |
| Spec sweet spot is narrow: precise spec → plain property tests suffice; vague spec → three-way splits everywhere | Measure in the first hour; tax-rounding fallback |
| Impact limited: real AI PRs are rarely one pure function with a clean spec | Q&A answer: gate for the riskiest functions by path/label; stateful next |
| Shared mistakes: PR and twins can misread the spec the same way → VERIFIED wrongly | Model + algorithm diversity, spec-cited rules, misses reported |
| Fetch fragility: laptop-hosted mailbox; reply timeout and card format unverified | Instant ack + follow-up; caffeinate; test in first hour; text fallback |
| Difficulty is moderate (Hypothesis + subprocesses + voting) | The mutation benchmark and "found in the wild" study carry it; don't add features to look harder |
| Time: ~5 hours for two people; roughly even odds the full demo works cleanly | Cut order, checkpoints, hard stop at 3:50 |

**Crowding (estimates; other teams unknown):** "Trust but Verify" likely the most crowded statement
(many "LLM writes tests, blocks PR" entries); self-improving agents common in "System That Gets
Better"; Software Archaeology likely least crowded. Many Fetch entries will barely meet the mandatory
list, so a complete working ASI:One flow is itself a differentiator. Any idea Claude suggests may be
suggested to other teams too; execution, real numbers and a working demo are what can't be copied.

**Idea history (context only, do not revisit):** ProofMerge (obvious, crowded) → self-improving
verifier (Fetch guide suggests it; crowded) → **Doppel (chosen)**. Rejected: Agentverse agent auditor
(depends on flaky third-party agents), Software Archaeology port (too risky), Ratchet (regex engine
self-improvement; weak Fetch fit, needs hours of loop time), Whittle (self-pruning playbook;
statistically underpowered deletion gate, dashboard risk, weak Fetch fit).

---

## 19. Instructions for Claude Code

- Priority order: (1) ASI:One ↔ Agentverse connectivity, (2) Referee core working locally,
  (3) end-to-end "Verify PR #N" → BLOCKED in ASI:One, (4) "Verify mutant #N" + QUESTION flow,
  (5) benchmark with real numbers, (6) stretch items only after the core works, in cut-order reverse.
- **Never fabricate benchmark numbers or claim untested capabilities** in the README, pitch or
  slides. Report misses.
- Keep the verdict deterministic: LLMs only generate twins, the schema/rules, the AI PR, and the
  blind-test baseline.
- Verify uAgents chat-protocol, mailbox, and Interactive Card APIs against the linked Fetch docs and
  examples, not from memory.
- Keep everything built today clearly attributable (commits, README "Built during the hackathon"
  section).
- Be honest and direct with Lisha about risks and trade-offs; she wants critical, accurate judgment,
  not reassurance. Don't reopen the idea choice.

---

## 20. Work split

Lisha = Fetch side, teammate = Engine side. Ownership, handoffs, timeline and the frozen interface
are in **`WORKSPLIT.md`** and **`contract/types.py`**. Stubs in `engine/api.py`, `bench/api.py`,
`twins/api.py` return fixtures until `DOPPEL_STUBS=0`.
