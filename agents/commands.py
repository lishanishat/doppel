"""Parse a chat message into a Command. Pure Python, no uagents."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Literal, Optional

Kind = Literal["verify_pr", "verify_url", "verify_mutant", "verify_custom", "answer", "help"]

_ANSWER_MAP = {
    "1": "pr", "a": "pr", "pr": "pr",
    "2": "twin_a", "b": "twin_a", "twin a": "twin_a", "twin_a": "twin_a", "twina": "twin_a",
    "3": "twin_b", "c": "twin_b", "twin b": "twin_b", "twin_b": "twin_b", "twinb": "twin_b",
}

_URL_RE = re.compile(r"https?://github\.com/([\w.-]+/[\w.-]+)/pull/(\d+)\S*", re.I)


@dataclass
class Command:
    kind: Kind
    repo: Optional[str] = None
    pr_number: Optional[int] = None
    function_name: Optional[str] = None
    mutant_id: Optional[int] = None
    answer: Optional[str] = None
    raw: Optional[str] = None


def _default_repo() -> str:
    return os.environ.get("DEMO_REPO", "lishanishat/doppel-demo")


def _norm_answer(s: str) -> Optional[str]:
    s = re.sub(r"\s+", " ", s.strip().lower().strip("`'\".!"))
    return _ANSWER_MAP.get(s)


_CUSTOM_RE = re.compile(r"^\s*(?:@\S+\s*)*verify\s+custom\b", re.I)


def parse(text: str) -> Command:
    if _CUSTOM_RE.match(text or ""):
        return Command("verify_custom", raw=text)
    t = re.sub(r"\s+", " ", (text or "").strip())
    # ASI:One prefixes messages with the agent's @mention/address; drop leading mentions.
    t = re.sub(r"^(?:@\S+\s*)+", "", t).strip()
    low = t.lower()

    m = _URL_RE.search(t)
    if m and low.startswith("verify"):
        rest = (t[: m.start()] + " " + t[m.end():]).strip()
        words = re.findall(r"[A-Za-z_]\w*", rest)
        fn = next((w for w in words if w.lower() != "verify"), None)
        return Command("verify_url", repo=m.group(1), pr_number=int(m.group(2)), function_name=fn)

    m = re.fullmatch(r"(?:verify )?mutant #?(\d+)", low)
    if m:
        return Command("verify_mutant", mutant_id=int(m.group(1)))

    m = re.fullmatch(r"verify pr #?(\d+)(?: (\w+))?", low)
    if m:
        fn = None
        if m.group(2):
            fn = re.search(r"(\w+)$", t).group(1)  # keep original case
        return Command("verify_pr", repo=_default_repo(), pr_number=int(m.group(1)), function_name=fn)

    m = re.fullmatch(r"answer:? (.+)", low)
    if m:
        a = _norm_answer(m.group(1))
        if a:
            return Command("answer", answer=a)
        return Command("help")

    if low in ("pr", "twin a", "twin b", "twin_a", "twin_b"):
        return Command("answer", answer=_norm_answer(low))

    return Command("help")
