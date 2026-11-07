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
    v = evidence.get("verdict", "UNPROVEN")
    if v == "VERIFIED":
        lines = [f"{_ICON.get(v, '')} **VERIFIED on {evidence.get('n_inputs', 0)} inputs**: all three versions agree "
                 "and every active rule holds. This is evidence on the inputs tested, not a proof of correctness."]
    else:
        lines = [f"{_ICON.get(v, '')} **{v}**: {evidence.get('reason', '')}"]

    ce = evidence.get("counterexample")
    q = evidence.get("question")
    if v == "BLOCKED" and ce:
        lines.append(f"Input: {_input_line(ce['input'])}")
        maj = set(ce.get("majority") or [])
        for name in _ORDER:
            if name in ce["outputs"]:
                mark = "✓" if name in maj else "✗"
                lines.append(f"{mark} {_LABEL[name]}: {_val(ce['outputs'][name])}")
        lines.append(f"Vote: {ce.get('vote', '')}")
    elif v == "QUESTION" and q:
        lines.append(f"**{q['text']}**")
        lines.append(f"Input: {_input_line(q['input'])}")
        for i, name in enumerate(_ORDER, 1):
            if name in q["options"]:
                lines.append(f"{i}. {_LABEL[name]} says {_val(q['options'][name])}")
        lines.append("Reply answer 1, answer 2 or answer 3.")

    if review_url:
        lines.append(f"Review: {review_url}")
    if v in ("BLOCKED", "UNPROVEN") and evidence.get("repro_cmd"):
        lines.append(f"Repro: {evidence['repro_cmd']}")
    return "\n".join(lines)
