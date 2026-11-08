import asyncio
import sys
import types
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from uagents_core.contrib.protocols.chat import ChatMessage, EndSessionContent, TextContent


def _setup(monkeypatch, gen):
    monkeypatch.setenv("ORCHESTRATOR_SEED_PHRASE", "test seed phrase for custom flow")
    monkeypatch.setenv("TWINS_IN_PROCESS", "1")
    from agents import commands, formatting, orchestrator, pipeline
    import twins.api

    events = []

    class Ctx:
        class logger:
            error = warning = info = staticmethod(lambda *a, **k: None)

        async def send(self, to, m):
            if isinstance(m, ChatMessage):
                t = " ".join(c.text for c in m.content if isinstance(c, TextContent))
                events.append(("send", t, any(isinstance(c, EndSessionContent) for c in m.content)))

    monkeypatch.setattr(commands, "parse", lambda text: SimpleNamespace(kind="verify_custom", raw=text))
    prep = SimpleNamespace(spec_text="spec", function_name="f", signature="def f(a)", pr={"name": "pr", "code": "def f(a): return a", "entrypoint": "f", "model": "user-submitted", "prompt_hash": None})
    monkeypatch.setattr(pipeline, "prepare_custom", lambda cmd: prep, raising=False)
    mod = types.ModuleType("engine.inputgen")
    mod.generate_inputs = gen
    monkeypatch.setitem(sys.modules, "engine.inputgen", mod)
    import engine
    monkeypatch.setattr(engine, "inputgen", mod, raising=False)
    monkeypatch.setattr(twins.api, "build_twins", lambda *a: ["twin"], raising=False)
    monkeypatch.setattr(formatting, "custom_ack_text", lambda fn: f"Got it. {fn}", raising=False)
    monkeypatch.setattr(formatting, "progress_text", lambda s, t, m: m, raising=False)

    def run_custom(p, twins, inputs, n):
        events.append(("run", inputs, False))
        return {"verdict": "OK"}, "VERDICT"

    monkeypatch.setattr(pipeline, "run_custom", run_custom, raising=False)
    msg = ChatMessage(timestamp=datetime.now(tz=timezone.utc), msg_id=uuid4(),
                      content=[TextContent(type="text", text="verify custom\nspec: x\n```python\ndef f(a): return a\n```")])
    asyncio.run(orchestrator._on_chat(Ctx(), "user", msg))
    return events


def test_custom_flow_happy(monkeypatch):
    ev = _setup(monkeypatch, lambda *a, **k: [{"a": 1}, {"a": 2}])
    texts = [e for e in ev if e[0] == "send"]
    assert texts[0][1] == "Got it. f" and not texts[0][2]
    assert len(texts) == 2  # only the acknowledgement and the verdict: intermediate messages trigger ASI:One 429 rate limits
    assert ("run", [{"a": 1}, {"a": 2}], False) in ev
    assert texts[-1][1] == "VERDICT" and texts[-1][2]
    assert sum(t[2] for t in texts) == 1


def test_custom_flow_failure_is_error_text(monkeypatch):
    def boom(*a, **k):
        raise ValueError("no function named f")

    ev = _setup(monkeypatch, boom)
    texts = [e for e in ev if e[0] == "send"]
    assert texts[0][1].startswith("Got it.")
    assert "no function named f" in texts[-1][1] and texts[-1][2]
    assert not any(e[0] == "run" for e in ev)
