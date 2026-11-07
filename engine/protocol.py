"""Result normalization and comparison shared by harness/referee. Pure, stdlib only.

normalize rules: Decimal -> format(v, "f"); date/datetime -> isoformat; float -> repr string;
str -> .strip() (no numeric canonicalization: strings compared exactly); list/tuple/dict recursive;
bool/int/None unchanged; anything else -> repr.
"""
import json
from datetime import date, datetime
from decimal import Decimal


def normalize(v):
    if isinstance(v, bool) or v is None or isinstance(v, int):
        return v
    if isinstance(v, Decimal):
        return format(v, "f")
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, (list, tuple)):
        return [normalize(x) for x in v]
    if isinstance(v, dict):
        return {str(k): normalize(x) for k, x in v.items()}
    return repr(v)


def encode_result(value) -> dict:
    return {"ok": True, "value": normalize(value)}


def same(a: dict, b: dict) -> bool:
    """Both raised -> equal (values ignored); otherwise ok flags and values must match."""
    if not a.get("ok") and not b.get("ok"):
        return True
    return bool(a.get("ok")) == bool(b.get("ok")) and a.get("value") == b.get("value")


def key(result: dict) -> str:
    """Stable string for vote grouping (all raised results share one key)."""
    if not result.get("ok"):
        return json.dumps({"ok": False})
    return json.dumps({"ok": True, "value": result.get("value")}, sort_keys=True)
