"""Orchestrator agent: ASI:One chat -> parse -> prepare -> twins -> verify -> verdict."""
import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone
from uuid import uuid4

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

from agents import commands, config, formatting, pipeline
from agents.messages import TwinRequest, TwinResponse

agent = Agent(
    name="doppel-orchestrator",
    seed=config.require_seed("ORCHESTRATOR_SEED_PHRASE", config.ORCHESTRATOR_SEED),
    port=config.ORCHESTRATOR_PORT,
    mailbox=True,
    publish_agent_details=True,
)
chat_proto = Protocol(spec=chat_protocol_spec)

# session_id -> {"sender", "prep", "deadline"}
PENDING: dict[str, dict] = {}
# user sender address -> last question id
LAST_QUESTION: dict[str, str] = {}


def _msg(text: str, end: bool) -> ChatMessage:
    content = [TextContent(type="text", text=text)]
    if end:
        content.append(EndSessionContent(type="end-session"))
    return ChatMessage(timestamp=datetime.now(tz=timezone.utc), msg_id=uuid4(), content=content)


async def _finish(ctx: Context, session_id: str, twins: list):
    """Run the verification for a pending session and reply with the verdict."""
    entry = PENDING.pop(session_id, None)
    if entry is None:
        return  # already handled (response vs timeout race)
    sender, prep = entry["sender"], entry["prep"]
    try:
        delay = float(os.environ.get("DEBUG_DELAY_S", "0"))  # test-only: simulate a slow verification
        if delay:
            await asyncio.sleep(delay)
        if entry.get("custom"):
            await ctx.send(sender, _msg(_fmt("progress_text", 3, 3, "Step 3/3: comparing all three versions", default="Step 3/3: comparing all three versions"), end=False))
            evidence, text = await asyncio.to_thread(
                pipeline.run_custom, prep, twins, entry.get("inputs"), config.max_examples()
            )
        else:
            evidence, text = await asyncio.to_thread(pipeline.run, prep, twins, config.max_examples())
        q = evidence.get("question") if isinstance(evidence, dict) else None
        if evidence.get("verdict") == "QUESTION" and q:
            LAST_QUESTION[sender] = q["id"]
    except Exception as e:
        ctx.logger.error(f"run failed: {e!r}")
        text = formatting.error_text(str(e) or repr(e))
    msg = _msg(text, end=True)
    try:
        if os.environ.get("DOPPEL_CARDS") == "1" and isinstance(evidence, dict):
            from agents.cards import verdict_card

            m = re.search(r"^Review: (\S+)", text, re.M)
            card = verdict_card(evidence, m.group(1) if m else None)
            if card is not None:
                msg.content.insert(1, card)  # after TextContent, before EndSessionContent
    except Exception as e:
        ctx.logger.warning(f"card skipped: {e!r}")
    await ctx.send(sender, msg)


async def _build_in_process(prep) -> list:
    from twins.api import build_twins

    return await asyncio.to_thread(build_twins, prep.spec_text, prep.function_name, prep.signature)


CUSTOM_TWIN_TIMEOUT_S = 420.0


def _guess_fn(cmd) -> str:
    m = re.search(r"^\s*def\s+(\w+)", getattr(cmd, "raw", None) or "", re.M)
    return m.group(1) if m else "your function"


def _fmt(name: str, *args, default: str = "") -> str:
    fn = getattr(formatting, name, None)
    return fn(*args) if fn else default


async def _custom_flow(ctx: Context, sender: str, cmd):
    """verify custom: ack -> generate inputs -> twins -> engine -> verdict. Never raises."""
    session_id = None
    try:
        await ctx.send(sender, _msg(_fmt("custom_ack_text", _guess_fn(cmd), default="Got it. Verifying your new function, about 3-5 minutes."), end=False))
        prepare = getattr(pipeline, "prepare_custom", None)
        if prepare is None:
            raise RuntimeError("custom mode is not available yet")
        try:
            prep = await asyncio.to_thread(prepare, cmd)
        except pipeline.UserFacingError as e:
            await ctx.send(sender, _msg(formatting.error_text(str(e)), end=True))
            return
        from engine import inputgen

        inputs = await asyncio.to_thread(inputgen.generate_inputs, prep.spec_text, prep.pr.code, prep.function_name)
        await ctx.send(sender, _msg(_fmt("progress_text", 1, 3, f"Step 1/3 done: {len(inputs)} test inputs", default=f"Step 1/3 done: {len(inputs)} test inputs"), end=False))
        await ctx.send(sender, _msg(_fmt("progress_text", 2, 3, "Step 2/3: two AI models are rebuilding your function from the spec", default="Step 2/3: two AI models are rebuilding your function from the spec"), end=False))
        session_id = str(uuid4())
        PENDING[session_id] = {
            "sender": sender,
            "prep": prep,
            "inputs": inputs,
            "custom": True,
            "deadline": time.monotonic() + CUSTOM_TWIN_TIMEOUT_S,
        }
        if config.twins_in_process():
            twins = await _build_in_process(prep)
            await _finish(ctx, session_id, twins)
        else:
            await ctx.send(
                config.twin_builder_address(),
                TwinRequest(
                    session_id=session_id,
                    spec_text=prep.spec_text,
                    function_name=prep.function_name,
                    signature=prep.signature,
                ),
            )
    except Exception as e:
        ctx.logger.error(f"custom flow failed: {e!r}")
        if session_id:
            PENDING.pop(session_id, None)
        try:
            await ctx.send(sender, _msg(formatting.error_text(str(e) or repr(e)), end=True))
        except Exception:
            pass


@chat_proto.on_message(ChatMessage)
async def _on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(), acknowledged_msg_id=msg.msg_id))
    try:
        text = " ".join(c.text for c in msg.content if isinstance(c, TextContent)).strip()
        cmd = commands.parse(text)

        if cmd.kind == "help":
            await ctx.send(sender, _msg(formatting.help_text(), end=True))
            return

        if cmd.kind == "answer":
            qid = LAST_QUESTION.get(sender)
            if not qid:
                await ctx.send(sender, _msg(formatting.error_text("No open question to answer."), end=True))
                return
            reply = await asyncio.to_thread(pipeline.answer, qid, cmd.answer)
            LAST_QUESTION.pop(sender, None)
            await ctx.send(sender, _msg(reply, end=True))
            return

        if cmd.kind == "verify_custom":
            await _custom_flow(ctx, sender, cmd)
            return

        # Immediate ack BEFORE the slow GitHub fetches (must start with "Got it." - Coder classifies on it).
        await ctx.send(sender, _msg(formatting.quick_ack_text(cmd), end=False))
        try:
            prep = await asyncio.to_thread(pipeline.prepare, cmd)
        except pipeline.UserFacingError as e:
            await ctx.send(sender, _msg(formatting.error_text(str(e)), end=True))
            return

        session_id = str(uuid4())
        PENDING[session_id] = {
            "sender": sender,
            "prep": prep,
            "deadline": time.monotonic() + config.twin_timeout_s(),
        }
        if config.twins_in_process():
            twins = await _build_in_process(prep)
            await _finish(ctx, session_id, twins)
        else:
            await ctx.send(
                config.twin_builder_address(),
                TwinRequest(
                    session_id=session_id,
                    spec_text=prep.spec_text,
                    function_name=prep.function_name,
                    signature=prep.signature,
                ),
            )
    except Exception as e:
        ctx.logger.error(f"chat handler failed: {e!r}")
        try:
            await ctx.send(sender, _msg(formatting.error_text(str(e) or repr(e)), end=True))
        except Exception:
            pass


@chat_proto.on_message(ChatAcknowledgement)
async def _on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


@agent.on_message(TwinResponse)
async def _on_twins(ctx: Context, sender: str, msg: TwinResponse):
    try:
        if msg.session_id not in PENDING:
            return
        twins = json.loads(msg.versions_json or "[]")
        if msg.error or not twins:
            ctx.logger.warning(f"twin builder error ({msg.error!r}); building in-process")
            twins = await _build_in_process(PENDING[msg.session_id]["prep"])
        await _finish(ctx, msg.session_id, twins)
    except Exception as e:
        ctx.logger.error(f"twin response handler failed: {e!r}")
        entry = PENDING.pop(msg.session_id, None)
        if entry:
            await ctx.send(entry["sender"], _msg(formatting.error_text(str(e) or repr(e)), end=True))


@agent.on_interval(period=3.0)
async def _timeouts(ctx: Context):
    now = time.monotonic()
    for sid, entry in list(PENDING.items()):
        if entry["deadline"] > now:
            continue
        entry["deadline"] = float("inf")  # don't retrigger while building
        ctx.logger.warning(f"no TwinResponse for {sid}; building twins in-process")
        try:
            twins = await _build_in_process(entry["prep"])
            await _finish(ctx, sid, twins)
        except Exception as e:
            ctx.logger.error(f"in-process fallback failed: {e!r}")
            PENDING.pop(sid, None)
            await ctx.send(entry["sender"], _msg(formatting.error_text(str(e) or repr(e)), end=True))


@agent.on_event("startup")
async def _startup(ctx: Context):
    ctx.logger.info(f"Orchestrator address: {agent.address}")
    ctx.logger.info(f"Inspector: https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A{config.ORCHESTRATOR_PORT}&address={agent.address}")


agent.include(chat_proto, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
