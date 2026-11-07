import json
from pathlib import Path

from agents.cards import verdict_card

FX = Path(__file__).resolve().parents[2] / "contract" / "fixtures"


def _load(n):
    return json.loads((FX / n).read_text())


def test_blocked_card():
    c = verdict_card(_load("blocked.json"), "https://example.com/r")
    m = c.metadata
    assert m["card_kind"] == "custom" and m["card_protocol_version"] == "1"
    p = m["card_payload"]
    assert "BLOCKED" in p and "Twin A" in p and "2-1" in p and "2028-02-29" in p and "Open review" in p
    assert json.loads(p)["root"]["type"] == "section"


def test_verified_card():
    c = verdict_card(_load("verified.json"), None)
    p = c.metadata["card_payload"]
    assert "VERIFIED on 2000 inputs" in p and "button" not in p


def test_none_on_error():
    assert verdict_card({}, None) is None
    assert verdict_card(None, None) is None
