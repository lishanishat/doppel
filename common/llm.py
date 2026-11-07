"""Thin OpenAI-SDK client for the Meta Model API and SubQ Snap (OpenAI-compatible, assumed)."""
from __future__ import annotations

import os
import time
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:  # dotenv optional
    pass

META_BASE_URL = "https://api.meta.ai/v1"
DEFAULT_META_MODEL = "muse-spark-1.3"
TIMEOUT_S = float(os.environ.get("LLM_TIMEOUT_S", "120"))
RETRIES = 3


def _client(provider: str):
    from openai import OpenAI

    if provider == "meta":
        key = os.environ.get("MODEL_API_KEY")
        if not key:
            raise RuntimeError("MODEL_API_KEY is not set")
        model = os.environ.get("META_MODEL", DEFAULT_META_MODEL)
        return OpenAI(base_url=META_BASE_URL, api_key=key, timeout=TIMEOUT_S, max_retries=0), model
    if provider == "meta2":  # a different Meta model line, for Twin B when no other vendor is available
        key = os.environ.get("MODEL_API_KEY")
        if not key:
            raise RuntimeError("MODEL_API_KEY is not set")
        model = os.environ.get("META_ALT_MODEL", "muse-wonder-1.0")
        return OpenAI(base_url=META_BASE_URL, api_key=key, timeout=TIMEOUT_S, max_retries=0), model
    if provider == "subq":
        key, url, model = (os.environ.get(k) for k in ("SUBQ_API_KEY", "SUBQ_BASE_URL", "SUBQ_MODEL"))
        if not (key and url and model):
            raise RuntimeError("SUBQ_API_KEY / SUBQ_BASE_URL / SUBQ_MODEL not all set")
        return OpenAI(base_url=url, api_key=key, timeout=TIMEOUT_S, max_retries=0), model
    if provider == "openai":
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        return OpenAI(api_key=key, timeout=TIMEOUT_S, max_retries=0), model
    if provider == "gemini":  # Google's OpenAI-compatible endpoint (unverified until a key is tested)
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        model = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
        return OpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/", api_key=key,
                      timeout=TIMEOUT_S, max_retries=0), model
    raise ValueError(f"unknown provider {provider!r}")


def complete(provider: str, system: str, user: str, temperature: float = 0.0) -> tuple[str, str]:
    """Return (text, model) where model is e.g. 'meta/muse-spark-1.3'. Raises after 3 attempts."""
    client, model = _client(provider)
    last: Exception | None = None
    for attempt in range(RETRIES):
        try:
            resp = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            )
            text = resp.choices[0].message.content or ""
            if not text.strip():
                raise RuntimeError("empty completion")
            return text, f"{provider.replace('meta2', 'meta')}/{model}"
        except Exception as e:  # noqa: BLE001
            last = e
            if attempt < RETRIES - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"{provider} completion failed after {RETRIES} attempts: {last}") from last
