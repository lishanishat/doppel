"""Twin builder agent: builds Twin A / Twin B from the spec and returns them as JSON."""
import asyncio
import json
from datetime import datetime, timezone
from uuid import uuid4

from uagents import Agent, Context

from agents import config
from agents.messages import TwinRequest, TwinResponse

agent = Agent(
    name="doppel-twin-builder",
    seed=config.require_seed("TWIN_BUILDER_SEED_PHRASE", config.TWIN_BUILDER_SEED),
    port=config.TWIN_BUILDER_PORT,
    mailbox=True,
    publish_agent_details=True,
)


@agent.on_event("startup")
async def _startup(ctx: Context):
    ctx.logger.info(f"Twin builder address: {agent.address}")
    ctx.logger.info(f"Inspector: https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A{config.TWIN_BUILDER_PORT}&address={agent.address}")


@agent.on_message(TwinRequest)
async def _on_request(ctx: Context, sender: str, msg: TwinRequest):
    try:
        from twins.api import build_twins

        versions = await asyncio.to_thread(build_twins, msg.spec_text, msg.function_name, msg.signature)
        resp = TwinResponse(session_id=msg.session_id, versions_json=json.dumps(versions))
    except Exception as e:  # never crash
        ctx.logger.error(f"build_twins failed: {e!r}")
        resp = TwinResponse(session_id=msg.session_id, versions_json="[]", error=str(e) or repr(e))
    await ctx.send(sender, resp)


if __name__ == "__main__":
    agent.run()
