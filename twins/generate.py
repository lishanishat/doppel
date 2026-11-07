"""Generate Twin A (Meta) and Twin B (SubQ, falling back to Meta) from the raw spec only."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from common import llm
from contract.types import Version
from twins import prompts

CACHE_ROOT = Path(__file__).resolve().parent.parent / "twins_cache"
_BLOCK = re.compile(r"```(?:python|py)?[ \t]*\n(.*?)```", re.DOTALL | re.IGNORECASE)
_HDR = re.compile(r"^# prompt_sha256: (\w+)$", re.MULTILINE)
_HDR_MODEL = re.compile(r"^# model: (.+)$", re.MULTILINE)


def extract_code(text: str) -> str:
    blocks = _BLOCK.findall(text)
    if blocks:
        return max(blocks, key=len).strip("\n") + "\n"
    return text.strip("\n") + "\n"


def prompt_hash(system: str, user: str) -> str:
    return hashlib.sha256(f"{system}\n\x00\n{user}".encode()).hexdigest()


def header(model: str, phash: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"# model: {model}\n# prompt_sha256: {phash}\n# generated_utc: {ts}\n"


def _gen_one(name: str, fn: str, system: str, user: str, root: Path) -> Version:
    phash = prompt_hash(system, user)
    path = root / fn / f"{name}.py"
    if path.exists():
        src = path.read_text()
        m, mm = _HDR.search(src), _HDR_MODEL.search(src)
        if m and mm and m.group(1) == phash:
            return {"name": name, "code": src, "entrypoint": fn, "model": mm.group(1), "prompt_hash": phash}
    if name == "twin_a":
        text, model = llm.complete("meta", system, user)
    else:
        text = model = None
        for provider in ("gemini", "openai", "meta2"):  # prefer another vendor; else a different Meta model line  # a different model family from Twin A, if configured
            try:
                text, model = llm.complete(provider, system, user)
                break
            except Exception:  # noqa: BLE001  unconfigured/unavailable: try the next one
                continue
        if text is None:  # honest fallback: same family as Twin A (recorded in the header and manifest)
            text, model = llm.complete("meta", system, user, temperature=0.7)
    code = header(model, phash) + extract_code(text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code)
    return {"name": name, "code": code, "entrypoint": fn, "model": model, "prompt_hash": phash}


def generate_twins(spec_text: str, function_name: str, signature: str, cache_root: Path | None = None) -> list[Version]:
    root = Path(cache_root) if cache_root else CACHE_ROOT
    a = _gen_one("twin_a", function_name, *prompts.twin_a_prompt(spec_text, signature), root)
    b = _gen_one("twin_b", function_name, *prompts.twin_b_prompt(spec_text, signature), root)
    manifest = {v["name"]: {"model": v["model"], "prompt_hash": v["prompt_hash"]} for v in (a, b)}
    (root / function_name / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return [a, b]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--function", required=True)
    ap.add_argument("--signature", help="default: first line containing 'def ' in the spec")
    args = ap.parse_args()
    spec = Path(args.spec).read_text()
    sig = args.signature or next((l.strip() for l in spec.splitlines() if "def " in l), f"def {args.function}(...)")
    for v in generate_twins(spec, args.function, sig):
        print(v["name"], v["model"], v["prompt_hash"][:12])


if __name__ == "__main__":
    main()
