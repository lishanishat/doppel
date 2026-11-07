# Fetch-side build plan (Lisha's half), executed by Claude Code + subagents

Planned 1:05 pm with Opus; executed with Sonnet. The main session coordinates; subagents build in
parallel on **disjoint files** in this checkout (no worktrees). **Only the main session commits**
(no `Co-Authored-By` lines), after checking each agent's work. Every brief below is self-contained:
**subagents must NOT read CLAUDE.md or WORKSPLIT.md** (saves ~10k tokens each); everything they
need is in their brief. Each subagent ends with a **report of 150 words or fewer**: files changed,
how it was tested, open issues.

---

## Verified facts (checked against sources at 1:00 pm; put the relevant ones in each brief)

- **Fetch quickstarter** (`fetchai/innovation-lab-examples/fetch-hackathon-quickstarter`):
  `uagents==0.22.8`, `uagents-core==0.3.8`, Python **3.12**. Pattern:
  - `Agent(name=..., seed=..., port=..., mailbox=True, publish_agent_details=True)`;
    `agent.include(chat_proto, publish_manifest=True)`.
  - `from uagents_core.contrib.protocols.chat import ChatAcknowledgement, ChatMessage,
    EndSessionContent, TextContent, chat_protocol_spec`; `chat_proto = Protocol(spec=chat_protocol_spec)`.
  - On a `ChatMessage`: first `ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(),
    acknowledged_msg_id=msg.msg_id))`; text = join of `TextContent.text` items.
  - Reply: `ctx.send(sender, ChatMessage(timestamp=datetime.now(tz=timezone.utc), msg_id=uuid4(),
    content=[TextContent(type="text", text=...), EndSessionContent(type="end-session")]))`.
  - **Delayed replies work by design**: the orchestrator forwards a `Model` to a helper agent, and
    replies to the stored `user_sender_address` when the helper's `Model` comes back
    (`@agent.on_message(SomeModel)`). So "instant ack text, then verdict later" is supported. The
    ack text message should **omit** `EndSessionContent`; the final verdict includes it.
  - Agent ↔ agent messages are `uagents.Model` (pydantic) classes; addresses come from
    `uagents_core.identity.Identity.from_seed(seed=..., index=0).address`.
  - Registration is a human step: run the agent, open its **Agent Inspector** link from the log,
    sign in to agentverse.ai and asi1.ai, click **Connect** → **Mailbox**, then "Chat with Agent".
- **Meta Model API** (meta-model-cookbook): OpenAI SDK, `OpenAI(base_url="https://api.meta.ai/v1",
  api_key=os.environ["MODEL_API_KEY"])`, model **`muse-spark-1.3`**; `chat.completions.create`
  works with `temperature`. A dedicated "Muse Code" model name is **unverified**: use
  `META_MODEL` env, default `muse-spark-1.3`.
- **SubQ Snap 1.1**: API format **unverified**. Assume OpenAI-compatible with `SUBQ_BASE_URL`,
  `SUBQ_MODEL`, `SUBQ_API_KEY` from env. If it fails, Twin B falls back to Meta with a different
  model/temperature and the manifest records that honestly.
- **Local machine**: only Python **3.14** is installed; no `uv`, no Homebrew Python. `uagents`
  0.22.8 pins pydantic 2.11.9, which likely has no 3.14 wheels → **use Python 3.12 via `uv`**.
- **GitHub**: `gh` is logged in as `lishanishat`; code can use `GITHUB_TOKEN` or fall back to
  `gh auth token`.
- **Contract**: `contract/types.py` (frozen). Stubs: `engine/api.py`, `bench/api.py`,
  `twins/api.py`, toggled by `DOPPEL_STUBS` (1 = fixtures).

---

## Agents

| Agent | Model | Phase | Owns (only these files) |
|---|---|---|---|
| **A1 Agents & runtime** | Sonnet | 1 (now) | `.venv` setup, `agents/messages.py`, `agents/config.py`, `agents/orchestrator.py`, `agents/twin_builder.py`, `Makefile`, `requirements.txt` (append) |
| **A2 Pipeline logic** | Sonnet | 1 (now) | `agents/commands.py`, `agents/pipeline.py`, `agents/formatting.py`, `agents/github_client.py`, `agents/tests/` |
| **A3 LLM & twins** | Sonnet | 1 (now), then 2 | `common/llm.py`, `common/__init__.py`, `twins/generate.py`, `twins/prompts.py`, `twins/api.py` (real branch), `twins_cache/`, `bench/llm_artifacts/` |
| **A4 PR author** | Sonnet, **fresh context** | 2 (after H1) | the public `lishanishat/doppel-demo` repo + `demo_target/prorate_refund/ai_pr/` |

**Why this split:**
- A1 and A2 are separated so all the logic (A2) is testable without `uagents` or a network, and the
  agent shell (A1) stays thin.
- A3 is independent until the spec exists.
- A4 must be a fresh context that has seen only the issue text, so the PR is honestly AI-written
  from the spec. Record the model in its PR description.

**Flow/token optimization (done by the main session, not a fifth agent):**
- Lean briefs, so subagents don't read the big docs.
- Short reports back to the main session.
- Background runs, so the main session keeps working meanwhile.
- No exploratory reading: the verified facts are already above.
- A dedicated "optimizer" agent running alongside would cost tokens without producing code; the
  4th slot is more valuable as the honest PR author.

---

## Interfaces between A1 and A2 (fixed now so both build at once)

`agents/commands.py` (A2):
```python
@dataclass
class Command:
    kind: Literal["verify_pr", "verify_url", "verify_mutant", "answer", "help"]
    repo: str | None = None          # "owner/name"; default env DEMO_REPO
    pr_number: int | None = None
    function_name: str | None = None
    mutant_id: int | None = None
    answer: str | None = None        # "pr" | "twin_a" | "twin_b"
def parse(text: str) -> Command
```
Accepted inputs: `verify pr #2` / `verify PR 2`; `verify https://github.com/o/r/pull/7 prorate_refund`;
`verify mutant #17` / `mutant 17`; answers `answer 1|2|3`, `A`/`B`/`C`, `pr`/`twin a`/`twin b`;
anything else → `help`. Case-insensitive.

`agents/pipeline.py` (A2):
```python
class UserFacingError(Exception): ...   # message is safe to show in chat

@dataclass
class Prepared:
    spec_text: str
    function_name: str
    signature: str
    pr: Version          # contract Version, name="pr"
    pr_ref: str          # "owner/repo#2" or "mutant#17"
    repo: str | None
    pr_number: int | None

def prepare(cmd: Command) -> Prepared
def run(prep: Prepared, twins: list[Version], max_examples: int) -> tuple[Evidence, str]
def answer(question_id: str, choice: str) -> str
```
- `prepare`, PR case:
  - Fetch the PR's changed `.py` files (not tests) and pick the one defining `function_name`.
  - Find the spec issue via `Closes/Fixes/Resolves #N` in the PR body (fallback: env
    `DEMO_SPEC_ISSUE`).
  - The issue body is the spec; the signature is the first line containing `def `.
- `prepare`, mutant case:
  - Spec from `demo_target/prorate_refund/spec.md` (if it's missing → `UserFacingError("spec not
    ready yet")`).
  - Code from `bench.api.get_mutant(n)`.
- `run`:
  - Build the contract `VerifyRequest`, call `engine.api.verify`, and post the GitHub review if
    this is a PR (`REQUEST_CHANGES` when BLOCKED, `COMMENT` otherwise).
  - Return the evidence plus `formatting.verdict_text(...)`.
  - Any exception → UNPROVEN text with a reason, never raised.

`agents/formatting.py` (A2): `help_text()`, `ack_text(prep, max_examples)`,
`verdict_text(evidence, review_url | None)`, `error_text(msg)`.
- BLOCKED must be readable in 5 seconds: verdict line, the input as one line, three outputs side by
  side marked ✓/✗ by the majority, the vote, the reason, the review link.
- QUESTION shows the question, the three options numbered 1/2/3, and "reply `answer 1`/`2`/`3`".
- Plain text with light Markdown. Under ~1,200 characters.

`agents/github_client.py` (A2): `get_pr(repo, n) -> dict(body, head_sha, files=[{path, content}])`,
`get_issue(repo, n) -> dict(title, body)`, `post_review(repo, n, body, event) -> url`.
- Uses `requests` with `GITHUB_TOKEN`, or `gh auth token` if that's unset.
- 3 retries with backoff; raises `UserFacingError` on 404.

`agents/messages.py` (A1): `TwinRequest(session_id, spec_text, function_name, signature)`,
`TwinResponse(session_id, versions_json: str, error: str = "")`.

**Orchestrator flow (A1):**
1. Ack the message.
2. `cmd = parse(text)`.
3. `help` → reply with `help_text()`.
4. `answer` → look up the session's last question id → `pipeline.answer` → reply.
5. Otherwise:
   - `prep = await asyncio.to_thread(pipeline.prepare, cmd)` (a `UserFacingError` becomes the
     reply).
   - Send `ack_text` **without** `EndSessionContent`.
   - Store `(sender, prep)` by session.
   - Send `TwinRequest` to the Twin builder, unless `TWINS_IN_PROCESS=1`.
   - Use a timeout via `ctx` interval or `asyncio`: after `TWIN_TIMEOUT_S` (default 45) with no
     `TwinResponse`, build twins in-process with `twins.api.build_twins`.
6. On `TwinResponse` (or the fallback):
   - `evidence, text = await asyncio.to_thread(pipeline.run, prep, twins, MAX_EXAMPLES)`.
   - Remember the question id if the verdict is QUESTION.
   - Reply with `EndSessionContent`.
7. Every handler is wrapped in `try/except` → `error_text`. Never crash.

**Twin builder (A1):** `@on_message(TwinRequest)` → `twins.api.build_twins(...)` in a thread →
`TwinResponse` (versions as JSON). Errors go in `error`.

---

## Phases and timing

| Phase | When | What |
|---|---|---|
| **1** | ~1:10–1:50 | A1, A2, A3 in parallel (background). Meanwhile the main session guides Lisha's human steps. |
| **check** | as each finishes | Main session: run A2's tests, a stub smoke test of the orchestrator, review diffs, commit + push. |
| **2** | when H1 lands (spec.md + reference.py from the teammate) | A3: generate the real twins (H2) + LLM blind tests (H5). A4: create `doppel-demo` with the issue, then write the AI PR + its tests from the issue only (H7). |
| **3** | live | Lisha runs the orchestrator + twin builder, registers both via the Inspector, and tests in ASI:One against stubs; follow-up message and timeout results go in `docs/FETCH_NOTES.md`. |
| **4** | when H4 lands (~2:40) | `DOPPEL_STUBS=0`, end-to-end "Verify PR #2" in ASI:One, fix integration bugs. |

**Human steps for Lisha during Phase 1:**
- `.env`: `MODEL_API_KEY` (Meta), `SUBQ_*`, two random seeds (`ORCHESTRATOR_SEED_PHRASE`,
  `TWIN_BUILDER_SEED_PHRASE`).
- Be signed in to agentverse.ai and asi1.ai in the browser, ready for the Inspector step.

---

## Briefs (paste as each subagent's prompt, together with the verified facts it needs)

**A1 brief:** "You are building the Fetch.ai agent shell for Doppel in /Users/lishanishat/doppel.
Do NOT read CLAUDE.md or WORKSPLIT.md.
(1) Set up Python 3.12: `python3 -m pip install --user uv` (or the pipx/official installer),
`uv python install 3.12`, `uv venv -p 3.12 .venv`, then install `uagents==0.22.8
uagents-core==0.3.8 python-dotenv requests hypothesis openai`. Append those to requirements.txt.
(2) Write agents/messages.py, agents/config.py (dotenv; seeds `ORCHESTRATOR_SEED_PHRASE`,
`TWIN_BUILDER_SEED_PHRASE`; addresses via Identity.from_seed), agents/orchestrator.py (port 8003)
and agents/twin_builder.py (port 8004) exactly following [orchestrator flow + twin builder +
verified Fetch facts]. Import A2's modules (agents.commands, agents.pipeline, agents.formatting),
which are being written in parallel. If they're missing when you test, create minimal temporary
stand-ins under agents/_standin/ only, never at A2's paths.
(3) Makefile targets `orchestrator`, `twin-builder`.
(4) Test: both agents start without errors under DOPPEL_STUBS=1 and log their addresses + Inspector
links. Don't commit. Report ≤150 words."

**A2 brief:** "Write pure-Python modules for Doppel in /Users/lishanishat/doppel, with NO uagents
import. Do NOT read CLAUDE.md or WORKSPLIT.md. Read contract/types.py and the
contract/fixtures/*.json files first. Implement agents/commands.py, agents/pipeline.py,
agents/formatting.py and agents/github_client.py exactly per [interfaces above]. Write pytest tests
in agents/tests/ covering: parsing every accepted input form; formatting of all four fixture
verdicts (print them in your report so the main session can eyeball them); pipeline.run under
DOPPEL_STUBS=1 with a fake GitHub client (monkeypatched); errors become UNPROVEN. Use only stdlib +
requests. Run the tests with python3. Don't commit. Report ≤150 words, plus the BLOCKED and
QUESTION texts."

**A3 brief:** "Build the twin generator for Doppel in /Users/lishanishat/doppel. Do NOT read
CLAUDE.md or WORKSPLIT.md. Read contract/types.py and twins/api.py.
(1) common/llm.py: `complete(provider: 'meta'|'subq', system, user) -> (text, model)` using the
OpenAI SDK. Meta: `base_url=https://api.meta.ai/v1`, key `MODEL_API_KEY`, model env `META_MODEL`
(default `muse-spark-1.3`). SubQ: `SUBQ_BASE_URL/SUBQ_API_KEY/SUBQ_MODEL`. Temperature 0,
3 retries with backoff, timeout 120 s.
(2) twins/prompts.py: Twin A = 'implement this function from the spec, normal approach'; Twin B =
'implement it the most literal, brute-force way (e.g. iterate day by day), no clever math'. Both
prompts contain only the raw spec text + signature, and ask for a single Python module in one code
block, stdlib only.
(3) twins/generate.py + the real branch of `twins.api.build_twins`: extract the code block, write
twins_cache/<fn>/twin_a.py and twin_b.py with a header comment (model, sha256 prompt hash, UTC
timestamp), plus manifest.json. Cache by prompt hash (an identical prompt reuses the files). If
SubQ fails, Twin B uses Meta and the manifest records the actual model. CLI:
`python -m twins.generate --spec demo_target/<fn>/spec.md --function <fn>`.
(4) bench/llm_artifacts/generate_blind_tests.py: from the spec only, Meta writes pytest tests that
import the function from a module path given as an argument.
(5) Test: make one real Meta call if MODEL_API_KEY is set (a one-line ping), else mock it. Don't
generate the real twins yet (the spec isn't ready). Don't commit. Report ≤150 words."

**A4 brief (Phase 2, fresh context):** "You are a coding agent asked to implement a GitHub issue.
Here is the issue text: <<spec.md contents>>. In /tmp/doppel-demo: create a Python package with
`billing.py` implementing the function, and `test_billing.py` with your own pytest tests; make your
tests pass. Then: `gh repo create lishanishat/doppel-demo --public`; push a `main` branch containing
only README.md; open issue #1 with the spec text; push your implementation on branch `ai-pr` and
open PR #2 (if numbering differs, report the actual number) whose body says 'Closes #1' and 'Written
by <your model id> from the issue text only'. Also copy billing.py and test_billing.py into
/Users/lishanishat/doppel/demo_target/prorate_refund/ai_pr/. Don't look at any other files in
/Users/lishanishat/doppel. Report ≤150 words with the PR URL."
(The main session confirms with Lisha before A4 creates the public repo.)
