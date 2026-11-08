"""Parse a 'verify custom' chat message into a CustomRequest. Pure Python."""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass

_MENTION_RE = re.compile(r"^\s*(?:@\S+\s*)+")
_VERB_RE = re.compile(r"^\s*verify\s+custom\b[:\-]?", re.I)
_SPEC_RE = re.compile(r"^\s*spec\s*:\s*", re.I)
_BLOCK_RE = re.compile(r"```[ \t]*(?:python|py)[ \t]*\r?\n(.*?)```", re.S | re.I)


@dataclass
class CustomRequest:
    spec_text: str
    code: str
    function_name: str
    signature: str


def strip_mentions(text: str) -> str:
    return _MENTION_RE.sub("", text or "", count=1)


def parse_custom(text: str) -> CustomRequest:
    body = strip_mentions(text)
    body = _VERB_RE.sub("", body, count=1)
    m = _BLOCK_RE.search(body)
    if not m:
        raise ValueError(
            "I couldn't find your code. Put the Python function in a ```python fenced block."
        )
    code = m.group(1).strip("\n")
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Your code has a syntax error (line {e.lineno}): {e.msg}.")
    fn = next(
        (n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))),
        None,
    )
    if fn is None:
        raise ValueError("I couldn't find a function. Include a top-level `def` in the code block.")
    lines = code.splitlines()
    signature = lines[fn.lineno - 1].strip()
    spec = (body[: m.start()] + "\n" + body[m.end():]).strip()
    spec = _SPEC_RE.sub("", spec, count=1).strip()
    if not spec:
        raise ValueError("I need a description of what the function should do. Add `spec: ...` before the code.")
    return CustomRequest(spec_text=spec, code=code, function_name=fn.name, signature=signature)
