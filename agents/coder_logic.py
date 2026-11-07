"""Pure helpers for the Coder agent (no uagents / env access, so tests import it anywhere)."""


def classify(text: str) -> str:
    """'running' for the orchestrator's acknowledgement ("Got it..."), else 'verdict'."""
    return "running" if (text or "").strip().startswith("Got it") else "verdict"
