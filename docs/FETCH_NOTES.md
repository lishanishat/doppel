# Fetch / ASI:One findings (measured, 1:25 pm Nov 7)

## Working (verified in a real ASI:One chat)
- Orchestrator registered on Agentverse via a local **mailbox**; replies to chat in ASI:One.
- Opening the agent via **Agent Profile -> Chat with Agent** prefills the agent address in the box and sets
  the **To:** chip. Messages sent *without* addressing the agent go to the user's personal ASI:One AI
  instead (it answered "That command is for Doppel..."). Rehearse the demo from the prefilled box.
- ASI:One prepends `@agent1q...` (the agent address) to the message text. The parser strips leading
  mentions (fixed in commit "Strip leading @mention...").
- Replies to `verify pr #2` and `verify mutant #17` arrive within about a minute. Errors come back as clean
  messages, never crashes.

## Measured (real engine, DOPPEL_STUBS=0, 2:25 pm)
- **A second (follow-up) message works.** One command produced an acknowledgement ("Got it. Verifying ...")
  and then the verdict as a separate message.
- `verify pr #2` end to end: acknowledgement after about 5-10 s (GitHub fetches happen before it), then
  VERIFIED on 285 inputs; the verdict itself takes under 1 s with cached twins. A GitHub review is posted and
  ASI:One renders a link card for it.
- Not yet measured: how long ASI:One waits before giving up on a slow reply (runs are far shorter than that).

## Gotchas
- `docs.google.com` Fetch docs and Meta cookbook aside, Meta's model is a reasoning model: tiny `max_tokens`
  can return empty content. `common/llm.py` sets no `max_tokens`.
- Almanac contract registration warns about insufficient funds; harmless for mailbox chat.

## Latency

Measured against lishanishat/doppel-demo PR #2 (read-only; post_review never called), cold process:
- `gh auth token` 0.13 s (now cached per process, thread-safe); GET PR 0.55 s; GET PR files 0.46 s; GET linked issue 0.47 s (plus one contents GET per .py file).
- `pipeline.prepare()` before: about 2.03 s (sequential, 3 runs). After (PR + files list concurrent, file contents concurrent): about 1.3 s (1.25-1.35 s, 3 runs).
- The Orchestrator now sends the "Got it." acknowledgement before prepare(), so time-to-ack is the message round trip only, not the GitHub time. The detailed function name / input count appear in the verdict. (Earlier 5-10 s was observed live; those runs were not re-measured here.)
- The verify path makes no LLM calls: pipeline/github_client/engine contain no model client; twins come from `twins_cache` (an LLM is only called on a cache miss in twins/generate.py). Per-run LLM cost on the cached path: 0 tokens.
