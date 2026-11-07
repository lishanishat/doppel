"""Plain-text chat replies. Pure Python."""
from __future__ import annotations

import json

_ORDER = ["pr", "twin_a", "twin_b"]
_LABEL = {"pr": "Submitted code (the PR)", "twin_a": "Rebuild 1", "twin_b": "Rebuild 2"}
_VENDOR = {"meta": "Meta", "gemini": "Google", "openai": "OpenAI", "subq": "SubQ"}


def _pretty_model(m) -> str:
    if not m or not isinstance(m, str) or "/" not in m:
        return ""
    vendor, name = m.split("/", 1)
    return f"{_VENDOR.get(vendor, vendor)} {name}"


def labels(models: dict | None = None) -> dict:
    """Display names; rebuilds show the model that wrote them when known, e.g. 'Rebuild 1 (Meta muse-spark-1.3)'."""
    out = dict(_LABEL)
    for name in ("twin_a", "twin_b"):
        pm = _pretty_model((models or {}).get(name))
        if pm:
            out[name] = f"{_LABEL[name]} ({pm})"
    return out
_ICON = {"BLOCKED": "⛔", "QUESTION": "❓", "UNPROVEN": "⚠️", "VERIFIED": "✅"}


def help_text() -> str:
    return (
        "**Doppel** verifies AI-written code. It rebuilds the function twice from the spec alone, with two "
        "different AI models, runs the submitted code and both rebuilds on hundreds of generated inputs, and fixed "
        "rules (not an AI) decide: VERIFIED, BLOCKED (with the exact input where they disagree) or UNPROVEN.\n\n"
        "Try:\n"
        "- verify pr #2\n"
        "- verify https://github.com/owner/repo/pull/7 prorate_refund\n"
        "- verify mutant #17\n"
        "- answer 1 / 2 / 3 (after a question)"
    )


def quick_ack_text(cmd) -> str:
    """Instant acknowledgement, sent before any network work. Starts with "Got it." (Coder keys on it)."""
    if getattr(cmd, "kind", "") == "verify_mutant":
        what = f"mutant #{cmd.mutant_id}"
    elif getattr(cmd, "pr_number", None):
        what = f"PR #{cmd.pr_number}"
    else:
        what = "that PR"
    return (f"Got it. Verifying {what}: I'll fetch the code and its spec, rebuild the function twice from the spec "
            f"with two different AI models, and run all three on hundreds of inputs. Verdict in a moment.")


def ack_text(prep, max_examples: int) -> str:
    return (
        f"Got it. Verifying {prep.function_name} from {prep.pr_ref}. "
        f"Two independent rebuilds are written from the spec, then I'll compare all three on "
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


def verdict_text(evidence: dict, review_url: str | None = None, models: dict | None = None) -> str:
    """Markdown with blank-line paragraphs and bullet lists: ASI:One collapses single newlines."""
    v = evidence.get("verdict", "UNPROVEN")
    icon = _ICON.get(v, "")
    lab = labels(models)
    n = evidence.get("n_inputs", 0)
    ce = evidence.get("counterexample")
    q = evidence.get("question")
    if v == "VERIFIED":
        ma, mb = _pretty_model((models or {}).get("twin_a")), _pretty_model((models or {}).get("twin_b"))
        who = f", one written by {ma} and one by {mb}," if ma and mb else ""
        parts = [f"{icon} **VERIFIED on {n} inputs**: the submitted code agrees with two independent rebuilds of the "
                 f"spec{who} on every one of the {n} generated inputs, and every spec rule holds. This is evidence on "
                 "the inputs tested, not a proof of correctness."]
    elif v == "BLOCKED" and ce:
        parts = [f"{icon} **BLOCKED**: the submitted code disagrees with two independent rebuilds of the same spec.",
                 f"I rebuilt this function twice from the spec alone, with two different AI models, and ran all three "
                 f"on {n} generated inputs. They disagree on this input:"]
    else:
        parts = [f"{icon} **{v}**: {evidence.get('reason', '')}"]

    if v == "BLOCKED" and ce:
        parts.append(f"**Input:** {_input_line(ce['input'])}")
        maj = set(ce.get("majority") or [])
        rows = []
        for name in _ORDER:
            if name in ce["outputs"]:
                rows.append(f"- {'✓' if name in maj else '✗'} {lab[name]}: {_val(ce['outputs'][name])}")
        parts.append("\n".join(rows))
        parts.append(f"{len(maj)} of 3 agree, so the submitted code is outvoted (vote {ce.get('vote', '')}).")
    elif v == "QUESTION" and q:
        parts.append(f"**{q['text']}**")
        parts.append(f"Input: {_input_line(q['input'])}")
        parts.append("\n".join(f"{i}. {lab[name]} says {_val(q['options'][name])}"
                              for i, name in enumerate(_ORDER, 1) if name in q["options"]))
        parts.append("Reply answer 1, answer 2 or answer 3.")

    if review_url:
        parts.append(f"Review: {review_url}")
    return "\n\n".join(parts)
