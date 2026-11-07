from agents.coder_logic import classify


def test_ack_is_running():
    assert classify("Got it. Verifying mutant #2...") == "running"
    assert classify("  Got it") == "running"


def test_verdict():
    assert classify("❌ **BLOCKED** foo") == "verdict"
    assert classify("") == "verdict"
