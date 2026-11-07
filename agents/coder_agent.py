"""Coder agent: submits "its work" to the Doppel orchestrator and logs the exchange."""
import asyncio
import os
import time
from datetime import datetime, timezone
from uuid import uuid4

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    TextContent,
    chat_protocol_spec,
)

from agents import config

agent = Agent(
    name="doppel-coder",
    seed=config.require_seed("CODER_SEED_PHRASE", config.CODER_SEED),
    port=config.CODER_PORT,
    mailbox=True,
    publish_agent_details=True,
)
chat_proto = Protocol(spec=chat_protocol_spec)

STATE: dict = {"t0": None, "done": False}


def classify(text: str) -> str:
    """'running' for the orchestrator's acknowledgement ("Got it..."), else 'verdict'."""
    return "running" if (text or "").strip().startswith("Got it") else "verdict"


def _text(msg: ChatMessage) -> str:
    return " ".join(c.text for c in msg.content if isinstance(c, TextContent)).strip()


@chat_proto.on_message(ChatMessage)
async def _on_chat(ctx: Context, sender: str, msg: ChatMessage):
    try:
        await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(tz=timezone.utc), acknowledged_msg_id=msg.msg_id))
    except Exception as e:
        ctx.logger.error(f"ack failed: {e!r}")
    try:
        text = _text(msg)
        if classify(text) == "running":
            ctx.logger.info(f"[coder] verification running: {text[:80]}")
        else:
            first = text.splitlines()[0] if text else ""
            ctx.logger.info(f"[coder] verdict: {first}")
            if not STATE["done"] and STATE["t0"] is not None:
                STATE["done"] = True
                ctx.logger.info(f"[coder] reply received, done (took {time.monotonic() - STATE['t0']:.1f} s)")
    except Exception as e:
        ctx.logger.error(f"chat handler failed: {e!r}")


@chat_proto.on_message(ChatAcknowledgement)
async def _on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


@agent.on_event("startup")
async def _startup(ctx: Context):
    ctx.logger.info(f"Coder address: {agent.address}")
    ctx.logger.info(f"Inspector: https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A{config.CODER_PORT}&address={agent.address}")
    try:
        await asyncio.sleep(10)
        text = os.environ.get("CODER_SUBMIT_TEXT", "verify pr #3")
        ctx.logger.info(f"[coder] submitting my PR to doppel-orchestrator: {text}")
        STATE["t0"] = time.monotonic()
        msg = ChatMessage(timestamp=datetime.now(tz=timezone.utc), msg_id=uuid4(), content=[TextContent(type="text", text=text)])
        await ctx.send(config.orchestrator_address(), msg)
    except Exception as e:
        ctx.logger.error(f"submit failed: {e!r}")


agent.include(chat_proto, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
