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
    assert "✗ PR: `0.00`" in t and "✓ Twin A: `1.03`" in t and "Vote: 2-1" in t and "http://rev" in t


def test_question_content():
    t = formatting.verdict_text(fx("question"))
    for s in ["1. PR", "2. Twin A", "3. Twin B", "answer 1", "answer 3", "does that day count"]:
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
    assert "Twin A" in pipeline.answer("q-1", "twin_a")


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
