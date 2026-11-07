"""Agent-to-agent messages between the Orchestrator and the Twin builder."""
from uagents import Model


class TwinRequest(Model):
    session_id: str
    spec_text: str
    function_name: str
    signature: str


class TwinResponse(Model):
    session_id: str
    versions_json: str  # JSON list of contract Version dicts
    error: str = ""
