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

## Still to measure
- Does ASI:One show a second (follow-up) message after the first "running..." reply?
- How long does ASI:One wait for a reply before giving up?

## Gotchas
- `docs.google.com` Fetch docs and Meta cookbook aside, Meta's model is a reasoning model: tiny `max_tokens`
  can return empty content. `common/llm.py` sets no `max_tokens`.
- Almanac contract registration warns about insufficient funds; harmless for mailbox chat.
