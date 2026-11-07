"""Env + identity config for the Fetch agents."""
import os

from dotenv import load_dotenv
from uagents_core.identity import Identity

load_dotenv()

ORCHESTRATOR_SEED = os.environ.get("ORCHESTRATOR_SEED_PHRASE", "")
TWIN_BUILDER_SEED = os.environ.get("TWIN_BUILDER_SEED_PHRASE", "")
CODER_SEED = os.environ.get("CODER_SEED_PHRASE", "")

ORCHESTRATOR_PORT = 8003
TWIN_BUILDER_PORT = 8004
CODER_PORT = 8005


def address_from_seed(seed: str) -> str:
    return Identity.from_seed(seed=seed, index=0).address


def require_seed(name: str, value: str) -> str:
    if not value:
        raise SystemExit(f"{name} is not set (put it in .env)")
    return value


def orchestrator_address() -> str:
    return address_from_seed(require_seed("ORCHESTRATOR_SEED_PHRASE", ORCHESTRATOR_SEED))


def twin_builder_address() -> str:
    return address_from_seed(require_seed("TWIN_BUILDER_SEED_PHRASE", TWIN_BUILDER_SEED))


def twin_timeout_s() -> float:
    return float(os.environ.get("TWIN_TIMEOUT_S", "45"))


def max_examples() -> int:
    return int(os.environ.get("MAX_EXAMPLES", "300"))


def twins_in_process() -> bool:
    return os.environ.get("TWINS_IN_PROCESS", "0") == "1"
