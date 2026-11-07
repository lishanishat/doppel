"""Prompts for the twins. Each contains only the raw spec text and the signature."""
from __future__ import annotations

_COMMON_TAIL = (
    "Return a single Python module in exactly one ```python code block, standard library only, "
    "defining the function with the given signature. No explanation outside the code block."
)

SYSTEM_A = "You are a careful Python engineer. Implement functions exactly as specified. " + _COMMON_TAIL
SYSTEM_B = (
    "You are a careful Python engineer who writes the most literal, brute-force implementation "
    "possible: iterate step by step (e.g. day by day), no clever math or closed-form shortcuts. "
    + _COMMON_TAIL
)


def user_prompt(spec_text: str, signature: str) -> str:
    return f"Specification:\n\n{spec_text}\n\nFunction signature:\n\n{signature}\n"


def twin_a_prompt(spec_text: str, signature: str) -> tuple[str, str]:
    return SYSTEM_A, user_prompt(spec_text, signature) + "\nImplement this function from the spec, using a normal approach.\n"


def twin_b_prompt(spec_text: str, signature: str) -> tuple[str, str]:
    return SYSTEM_B, user_prompt(spec_text, signature) + "\nImplement it the most literal, brute-force way (e.g. iterate day by day), with no clever math.\n"
