"""Plain-text chat replies. Pure Python."""
from __future__ import annotations

import json

_ORDER = ["pr", "twin_a", "twin_b"]
_LABEL = {"pr": "PR", "twin_a": "Twin A", "twin_b": "Twin B"}
_ICON = {"BLOCKED": "⛔", "QUESTION": "❓", "UNPROVEN": "⚠️", "VERIFIED": "✅"}


def help_text() -> str:
    return (
        "**Doppel** checks a PR against two independent re-implementations of its spec.\n\n"
        "Try:\n"
        "- verify pr #2\n"
        "- verify https://github.com/owner/repo/pull/7 prorate_refund\n"
        "- verify mutant #17\n"
        "- answer 1 / 2 / 3 (after a question)"
    )


def ack_text(prep, max_examples: int) -> str:
    return (
        f"Got it. Verifying {prep.function_name} from {prep.pr_ref}. "
        f"Two independent twins are writing it from the spec, then I'll compare all three on "
        f"up to {max_examples} inputs. Verdict in a moment."
    )


def error_text(msg: str) -> str:
    return f"⚠️ {msg}\n\nSend help to see what I understand."


def _val(o) -> str:
    if not isinstance(o, dict):
        return str(o)
    if o.get("ok"):
        return str(o.get("value"))
    return "error"


def _input_line(inp: dict) -> str:
    return ", ".join(f"{k}={v}" for k, v in (inp or {}).items())


def verdict_text(evidence: dict, review_url: str | None = None) -> str:
    """Markdown with blank-line paragraphs and bullet lists: ASI:One collapses single newlines."""
    v = evidence.get("verdict", "UNPROVEN")
    icon = _ICON.get(v, "")
    if v == "VERIFIED":
        parts = [f"{icon} **VERIFIED on {evidence.get('n_inputs', 0)} inputs**: all three versions agree and every "
                 "active rule holds. This is evidence on the inputs tested, not a proof of correctness."]
    else:
        parts = [f"{icon} **{v}**: {evidence.get('reason', '')}"]

    ce = evidence.get("counterexample")
    q = evidence.get("question")
    if v == "BLOCKED" and ce:
        parts.append(f"**Counterexample:** {_input_line(ce['input'])}")
        maj = set(ce.get("majority") or [])
        rows = []
        for name in _ORDER:
            if name in ce["outputs"]:
                rows.append(f"- {'✓' if name in maj else '✗'} {_LABEL[name]}: {_val(ce['outputs'][name])}")
        parts.append("\n".join(rows))
        parts.append(f"Vote: {ce.get('vote', '')}")
    elif v == "QUESTION" and q:
        parts.append(f"**{q['text']}**")
        parts.append(f"Input: {_input_line(q['input'])}")
        parts.append("\n".join(f"{i}. {_LABEL[name]} says {_val(q['options'][name])}"
                              for i, name in enumerate(_ORDER, 1) if name in q["options"]))
        parts.append("Reply answer 1, answer 2 or answer 3.")

    if review_url:
        parts.append(f"Review: {review_url}")
    return "\n\n".join(parts)
