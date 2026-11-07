import json
from pathlib import Path

import pytest

from agents import commands, formatting, pipeline
from agents.commands import Command, parse

FIX = Path(__file__).resolve().parents[2] / "contract" / "fixtures"


def fx(name):
    return json.loads((FIX / f"{name}.json").read_text())


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("DOPPEL_STUBS", "1")
    monkeypatch.setenv("DEMO_REPO", "o/demo")


@pytest.mark.parametrize("text", ["verify pr #2", "Verify PR 2", "VERIFY PR #2"])
def test_verify_pr(text):
    c = parse(text)
    assert (c.kind, c.pr_number, c.repo) == ("verify_pr", 2, "o/demo")


def test_verify_url():
    c = parse("verify https://github.com/o/r/pull/7 prorate_refund")
    assert (c.kind, c.repo, c.pr_number, c.function_name) == ("verify_url", "o/r", 7, "prorate_refund")
    assert parse("Verify https://github.com/o/r/pull/7").function_name is None


@pytest.mark.parametrize("text", ["verify mutant #17", "mutant 17", "Mutant #17"])
def test_mutant(text):
    c = parse(text)
    assert (c.kind, c.mutant_id) == ("verify_mutant", 17)


@pytest.mark.parametrize("text,exp", [
    ("answer 1", "pr"), ("answer 2", "twin_a"), ("answer 3", "twin_b"),
    ("answer A", "pr"), ("Answer B", "twin_a"), ("answer c", "twin_b"),
    ("pr", "pr"), ("twin a", "twin_a"), ("Twin B", "twin_b"), ("answer twin b", "twin_b"),
])
def test_answers(text, exp):
    c = parse(text)
    assert (c.kind, c.answer) == ("answer", exp)


@pytest.mark.parametrize("text", ["", "hello", "verify", "answer 9", "verify pr", "what is this?", None])
def test_help(text):
    assert parse(text).kind == "help"


@pytest.mark.parametrize("name", ["blocked", "question", "verified", "unproven"])
def test_formatting_fixtures(name):
    ev = fx(name)
    t = formatting.verdict_text(ev, "https://github.com/o/r/pull/2#review")
    assert ev["verdict"] in t and len(t) < 1200
    print("\n---", name, "\n" + t)


def test_blocked_content():
    t = formatting.verdict_text(fx("blocked"), "http://rev")
    assert "✗ Submitted code (the PR): 0.00" in t and "✓ Rebuild 1: 1.03" in t and "vote 2-1" in t and "http://rev" in t


def test_question_content():
    t = formatting.verdict_text(fx("question"))
    for s in ["1. Submitted code (the PR)", "2. Rebuild 1", "3. Rebuild 2", "answer 1", "answer 3", "does that day count"]:
        assert s in t


def test_misc_text():
    assert "verify pr" in formatting.help_text()
    assert "boom" in formatting.error_text("boom")


def make_prep(**kw):
    d = dict(spec_text="s", function_name="prorate_refund", signature="def prorate_refund()",
             pr={"name": "pr", "code": "x", "entrypoint": "prorate_refund", "model": "m", "prompt_hash": None},
             pr_ref="o/demo#2", repo="o/demo", pr_number=2)
    d.update(kw)
    return pipeline.Prepared(**d)


TWINS = [{"name": "twin_a", "code": "", "entrypoint": "f", "model": "m", "prompt_hash": "h"},
         {"name": "twin_b", "code": "", "entrypoint": "f", "model": "m", "prompt_hash": "h"}]


@pytest.mark.parametrize("verdict,event", [("blocked", "REQUEST_CHANGES"), ("verified", "COMMENT"),
                                           ("question", "COMMENT")])
def test_run_posts_review(monkeypatch, verdict, event):
    monkeypatch.setenv("DOPPEL_STUB_VERDICT", verdict)
    calls = []
    monkeypatch.setattr(pipeline.github_client, "post_review",
                        lambda r, n, b, e: calls.append((r, n, e)) or "http://rev")
    ev, text = pipeline.run(make_prep(), TWINS, 100)
    assert ev["verdict"] == verdict.upper() and "http://rev" in text
    assert calls == [("o/demo", 2, event)]


def test_run_mutant_no_review(monkeypatch):
    monkeypatch.setattr(pipeline.github_client, "post_review",
                        lambda *a: pytest.fail("should not post"))
    ev, text = pipeline.run(make_prep(repo=None, pr_number=None, pr_ref="mutant#17"), TWINS, 100)
    assert ev["verdict"] == "BLOCKED"


def test_run_review_failure_still_returns(monkeypatch):
    def boom(*a):
        raise RuntimeError("nope")
    monkeypatch.setattr(pipeline.github_client, "post_review", boom)
    ev, text = pipeline.run(make_prep(), TWINS, 100)
    assert "BLOCKED" in text


def test_run_exception_becomes_unproven(monkeypatch):
    import engine.api
    def boom(req):
        raise ValueError("engine exploded")
    monkeypatch.setattr(engine.api, "verify", boom)
    ev, text = pipeline.run(make_prep(), TWINS, 100)
    assert ev["verdict"] == "UNPROVEN" and "engine exploded" in text


def test_answer_stub():
    assert "Rebuild 1" in pipeline.answer("q-1", "twin_a")


def test_prepare_pr(monkeypatch):
    monkeypatch.setattr(pipeline.github_client, "get_pr", lambda r, n: {
        "body": "Closes #1", "head_sha": "abc", "files": [
            {"path": "test_billing.py", "content": "def prorate_refund(): pass"},
            {"path": "billing.py", "content": "def prorate_refund(a):\n    return a\n"}]})
    monkeypatch.setattr(pipeline.github_client, "get_issue", lambda r, n: {
        "title": "t", "body": "Spec\n```\ndef prorate_refund(price) -> str\n```"})
    p = pipeline.prepare(Command("verify_pr", repo="o/demo", pr_number=2))
    assert p.pr["code"].startswith("def prorate_refund(a)") and p.pr_ref == "o/demo#2"
    assert p.signature == "def prorate_refund(price) -> str"


def test_prepare_pr_no_issue(monkeypatch):
    monkeypatch.delenv("DEMO_SPEC_ISSUE", raising=False)
    monkeypatch.setattr(pipeline.github_client, "get_pr", lambda r, n: {
        "body": "hi", "head_sha": "a", "files": [{"path": "b.py", "content": "def prorate_refund(): pass"}]})
    with pytest.raises(pipeline.UserFacingError):
        pipeline.prepare(Command("verify_pr", repo="o/demo", pr_number=2))


def test_prepare_mutant(monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, "ROOT", tmp_path)
    with pytest.raises(pipeline.UserFacingError, match="spec not ready yet"):
        pipeline.prepare(Command("verify_mutant", mutant_id=17))
    (tmp_path / "demo_target" / "prorate_refund").mkdir(parents=True)
    (tmp_path / "demo_target" / "prorate_refund" / "spec.md").write_text("def prorate_refund(x)\n")
    p = pipeline.prepare(Command("verify_mutant", mutant_id=17))
    assert p.pr_ref == "mutant#17" and p.pr_number is None


def test_parse_strips_leading_mention():
    from agents.commands import parse
    addr = "@agent1qw3l50t8rpzg9dfhpfnyrkpcceuxrmpxd6qtue2rfr86ddh5yg6jkvuue9m"
    assert parse(f"{addr} verify pr #2").kind == "verify_pr"
    assert parse(f"{addr} verify pr #2").pr_number == 2
    assert parse(f"@doppel-orchestrator verify mutant #17").mutant_id == 17
    assert parse(f"{addr} answer 2").kind == "answer"
    assert parse(f"{addr}").kind == "help"


def test_ack_sent_before_prepare(monkeypatch):
    """The 'Got it.' ack must go out before the slow GitHub prepare() runs; no second ack after."""
    import asyncio
    monkeypatch.setenv("ORCHESTRATOR_SEED_PHRASE", "test seed phrase for ordering test")
    monkeypatch.setenv("TWINS_IN_PROCESS", "1")
    from agents import orchestrator, pipeline
    from uagents_core.contrib.protocols.chat import ChatMessage, TextContent
    from datetime import datetime, timezone
    from uuid import uuid4
    events = []

    class Ctx:
        class logger:
            error = warning = info = staticmethod(lambda *a, **k: None)
        async def send(self, to, m):
            t = " ".join(c.text for c in getattr(m, "content", []) if isinstance(c, TextContent))
            events.append(("send", t))

    def fake_prepare(cmd):
        events.append(("prepare", ""))
        raise pipeline.UserFacingError("boom")

    monkeypatch.setattr(pipeline, "prepare", fake_prepare)
    msg = ChatMessage(timestamp=datetime.now(tz=timezone.utc), msg_id=uuid4(),
                      content=[TextContent(type="text", text="verify pr #2")])
    asyncio.run(orchestrator._on_chat(Ctx(), "user", msg))
    kinds = [k for k, _ in events]
    assert kinds.index("prepare") > 1  # ChatAck, then quick ack, both before prepare
    texts = [t for k, t in events if k == "send" and t]
    assert texts[0].startswith("Got it.") and sum(t.startswith("Got it.") for t in texts) == 1


def test_rebuild_labels_show_vendor_and_model():
    import json
    from agents.formatting import verdict_text
    ev = json.load(open("contract/fixtures/blocked.json"))
    t = verdict_text(ev, None, {"twin_a": "meta/muse-spark-1.3", "twin_b": "gemini/gemini-3-flash-preview"})
    assert "Rebuild 1 (Meta muse-spark-1.3)" in t and "Rebuild 2 (Google gemini-3-flash-preview)" in t
    assert "twin_a" not in t and "outvoted" in t
