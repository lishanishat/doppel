"""LLM-free test-input generator driven by type hints and parameter names."""
from __future__ import annotations

import ast
import calendar
import json
import random
from typing import Any

_MISSING = object()

DATE_EDGES = ["2024-02-29", "2023-02-28", "2024-01-31", "2024-12-31", "2025-01-01",
              "2023-12-31", "2024-03-01", "2000-02-29", "2024-04-30", "2024-06-30"]
STR_EDGES = ["", " ", "a", "Zoë", "日本語", "hello world", "x" * 200, "O'Brien", "UPPER", "tab\there"]
PRICE_EDGES = ["0", "0.00", "0.01", "0.5", "1", "9.99", "10.00", "99.95", "100", "1234.56", "0.005", "1000000.00"]
INT_EDGES = [0, 1, 2, 3, 5, 10, 100, 255, 1000]
GENERIC_INT_EDGES = [0, 1, -1, 2, 10, 100, -100, 2**31 - 1]
FLOAT_EDGES = [0.0, 1.0, -1.0, 0.5, 0.1, 100.0, 1e-9, 1e6, -0.5]


def _rand_date(rng: random.Random) -> str:
    y = rng.randint(1999, 2030)
    m = rng.randint(1, 12)
    d = rng.choice([1, calendar.monthrange(y, m)[1], rng.randint(1, 28)])
    return f"{y:04d}-{m:02d}-{d:02d}"


def _rand_price(rng: random.Random) -> str:
    places = rng.choice([0, 1, 2, 2, 2])
    v = rng.choice([rng.uniform(0, 100), rng.uniform(0, 5000)])
    return f"{v:.{places}f}"


def _rand_str(rng: random.Random) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz ABCZé日_-"
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 12)))


def _ann_name(ann: ast.AST | None) -> str:
    return ast.unparse(ann).replace(" ", "") if ann is not None else ""


def _gen_from_ann(ann: ast.AST | None, name: str, rng: random.Random, depth: int = 0) -> Any:
    low = name.lower()
    text = _ann_name(ann)
    base = text.split("[")[0].split(".")[-1].lower()

    # Optional / Union
    if base == "optional" and isinstance(ann, ast.Subscript):
        if rng.random() < 0.2:
            return None
        return _gen_from_ann(ann.slice, name, rng, depth)
    if base == "union" and isinstance(ann, ast.Subscript):
        parts = ann.slice.elts if isinstance(ann.slice, ast.Tuple) else [ann.slice]
        return _gen_from_ann(rng.choice(parts), name, rng, depth)
    if isinstance(ann, ast.BinOp) and isinstance(ann.op, ast.BitOr):
        return _gen_from_ann(rng.choice([ann.left, ann.right]), name, rng, depth)
    if text == "None":
        return None

    if base == "bool":
        return rng.random() < 0.5
    if base == "int":
        if any(k in low for k in ("n", "count", "size", "k")) and low in ("n", "k") or \
                any(k in low for k in ("count", "size", "num", "len")):
            return rng.choice(INT_EDGES + [rng.randint(0, 50)])
        return rng.choice(GENERIC_INT_EDGES + [rng.randint(-1000, 1000)])
    if base == "float":
        if any(k in low for k in ("price", "amount", "cost", "rate", "total")):
            return round(rng.choice([0.0, 0.01, 9.99, 100.0, rng.uniform(0, 1000)]), 2)
        return rng.choice(FLOAT_EDGES + [round(rng.uniform(-100, 100), 3)])
    if base == "str":
        return _gen_str(low, rng)
    if base in ("list", "set", "sequence", "frozenset", "iterable"):
        inner = ann.slice if isinstance(ann, ast.Subscript) else None
        return [_gen_from_ann(inner, name, rng, depth + 1) for _ in range(rng.choice([0, 1, 2, 3, 5]))] \
            if depth < 3 else []
    if base == "tuple":
        if isinstance(ann, ast.Subscript):
            elts = ann.slice.elts if isinstance(ann.slice, ast.Tuple) else [ann.slice]
            if len(elts) == 2 and isinstance(elts[1], ast.Constant) and elts[1].value is Ellipsis:
                return [_gen_from_ann(elts[0], name, rng, depth + 1) for _ in range(rng.randint(0, 4))]
            return [_gen_from_ann(e, name, rng, depth + 1) for e in elts]
        return [rng.randint(0, 10) for _ in range(rng.randint(0, 3))]
    if base == "dict":
        vt = None
        if isinstance(ann, ast.Subscript) and isinstance(ann.slice, ast.Tuple) and len(ann.slice.elts) == 2:
            vt = ann.slice.elts[1]
        return {_rand_key(rng): _gen_from_ann(vt, name, rng, depth + 1)
                for _ in range(rng.randint(0, 3))} if depth < 3 else {}
    if base in ("any", "object", ""):
        return _gen_untyped(low, rng)
    return _gen_untyped(low, rng)


def _rand_key(rng: random.Random) -> str:
    return rng.choice(["a", "b", "c", "key", "x", "name", ""])


def _gen_str(low: str, rng: random.Random) -> str:
    if any(k in low for k in ("date", "day", "start", "end")):
        return rng.choice(DATE_EDGES) if rng.random() < 0.4 else _rand_date(rng)
    if any(k in low for k in ("price", "amount", "cost", "rate", "total")):
        return rng.choice(PRICE_EDGES) if rng.random() < 0.4 else _rand_price(rng)
    if any(k in low for k in ("name", "text", "word")) or low == "s":
        return rng.choice(STR_EDGES) if rng.random() < 0.5 else _rand_str(rng)
    return rng.choice(STR_EDGES) if rng.random() < 0.4 else _rand_str(rng)


def _gen_untyped(low: str, rng: random.Random) -> Any:
    if any(k in low for k in ("date", "day", "start", "end", "price", "amount", "cost",
                              "rate", "total", "name", "text", "word")) or low == "s":
        return _gen_str(low, rng)
    if low in ("n", "k") or any(k in low for k in ("count", "size", "num")):
        return rng.choice(INT_EDGES + [rng.randint(0, 20)])
    return rng.choice([rng.randint(0, 20), rng.choice(STR_EDGES[:6])])


def _default_value(node: ast.AST | None) -> Any:
    if node is None:
        return _MISSING
    try:
        v = ast.literal_eval(node)
        json.dumps(v)
        return v
    except Exception:
        return _MISSING


def typehint_inputs(code: str, function_name: str, n: int = 300) -> list[dict]:
    tree = ast.parse(code)
    fn = next((x for x in ast.walk(tree)
               if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) and x.name == function_name), None)
    if fn is None:
        raise ValueError(f"No function named {function_name!r} found in the code.")

    a = fn.args
    pos = a.posonlyargs + a.args
    defaults = [None] * (len(pos) - len(a.defaults)) + list(a.defaults)
    params = [(p, d) for p, d in zip(pos, defaults)]
    params += list(zip(a.kwonlyargs, a.kw_defaults))
    params = [(p, d) for p, d in params if p.arg not in ("self", "cls")]

    rng = random.Random(0)
    out: list[dict] = []
    seen: set[str] = set()

    def add(d: dict) -> None:
        key = json.dumps(d, sort_keys=True, default=str)
        if key not in seen:
            seen.add(key)
            out.append(d)

    attempts = 0
    while len(out) < n and attempts < n * 20:
        attempts += 1
        call = {}
        for p, d in params:
            dv = _default_value(d)
            if dv is not _MISSING and rng.random() < 0.3:
                call[p.arg] = dv
            else:
                call[p.arg] = _gen_from_ann(p.annotation, p.arg, rng)
        add(call)
    if not out:
        out.append({})
    return out
