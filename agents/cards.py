"""Optional ASI:One interactive card for the verdict (card_kind=custom).

Mechanism: a MetadataContent block in the ChatMessage with string metadata
card_protocol_version/requires_card_interaction/card_kind/card_payload
(+is_terminal). Invalid cards make ASI:One fall back to the text reply.
"""
import json


def _mark(o):
    if not isinstance(o, dict):
        return "?"
    if not o.get("ok"):
        return f"✗ error"
    return f"✓ {o.get('value')}"


def build_payload(evidence: dict, review_url: str | None) -> dict:
    verdict = str(evidence["verdict"])
    kids = []
    if verdict == "VERIFIED":
        kids.append({"type": "badge", "label": f"VERIFIED on {evidence.get('n_inputs')} inputs", "variant": "success"})
    else:
        kids.append({"type": "badge", "label": verdict, "variant": "warning"})
    if evidence.get("reason"):
        kids.append({"type": "text", "value": str(evidence["reason"]), "style": "muted"})
    ce = evidence.get("counterexample")
    if ce:
        kids.append({"type": "divider"})
        kids.append({"type": "text", "value": "Counterexample input", "style": "emphasis"})
        kids.append({"type": "text", "value": json.dumps(ce.get("input"), sort_keys=True)})
        outs = ce.get("outputs") or {}
        for key, label in (("pr", "PR"), ("twin_a", "Twin A"), ("twin_b", "Twin B")):
            kids.append({"type": "text", "value": f"{label}: {_mark(outs.get(key))}"})
        if ce.get("vote"):
            kids.append({"type": "text", "value": f"Vote: {ce['vote']}", "style": "emphasis"})
    if review_url:
        kids.append({"type": "button", "label": "Open review", "primary": True,
                     "action": {"selection": {"action": "open_review", "url": review_url}}})
    return {"root": {"type": "section", "title": f"Doppel verdict: {verdict}", "children": kids}}


def verdict_card(evidence: dict, review_url: str | None = None):
    """Return a MetadataContent card, or None on any problem."""
    try:
        from uagents_core.contrib.protocols.chat import MetadataContent

        payload = json.dumps(build_payload(evidence, review_url))
        if len(payload.encode()) > 60000:
            return None
        return MetadataContent(type="metadata", metadata={
            "card_protocol_version": "1",
            "requires_card_interaction": "true",
            "card_kind": "custom",
            "card_payload": payload,
            "is_terminal": "true",
        })
    except Exception:
        return None
