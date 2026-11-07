"""Seeded AST mutation of a reference function -> list[contract.types.Mutant].

Operators: flip_comparison, swap_arith, off_by_one_const, remove_check, swap_rounding.
Ids are deterministic for a given (reference_code, seed). Split rule, fixed before any tuning:
    id % 3 == 0 -> "dev", else "heldout".
Likely-equivalent detection: mutant agrees with the reference on every one of N fuzzed schema inputs.
"""
from __future__ import annotations

import ast
import copy
import json
import random
import signal
from pathlib import Path

from contract.types import Mutant

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "bench" / "mutants"

_CMP_FLIPS = {ast.Lt: [ast.LtE], ast.LtE: [ast.Lt], ast.Gt: [ast.GtE], ast.GtE: [ast.Gt],
              ast.Eq: [ast.NotEq], ast.NotEq: [ast.Eq]}
_ARITH_SWAPS = {ast.Add: [ast.Sub], ast.Sub: [ast.Add], ast.Mult: [ast.Div], ast.Div: [ast.Mult]}
_ROUNDINGS = ["ROUND_HALF_DOWN", "ROUND_DOWN", "ROUND_UP"]
_SYM = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!=",
        ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}


def _sym(op) -> str:
    return _SYM[type(op)]


def _sites(tree: ast.AST):
    """Yield (operator, node_path_index, variant_index, description). Sites enumerated by ast.walk order."""
    out = []
    for i, node in enumerate(ast.walk(tree)):
        ln = getattr(node, "lineno", 0)
        if isinstance(node, ast.Compare):
            for j, op in enumerate(node.ops):
                for k, new in enumerate(_CMP_FLIPS.get(type(op), [])):
                    out.append(("flip_comparison", i, (j, k),
                                f"line {ln}: '{_sym(op)}' -> '{_sym(new())}'"))
        elif isinstance(node, ast.BinOp) and type(node.op) in _ARITH_SWAPS:
            for k, new in enumerate(_ARITH_SWAPS[type(node.op)]):
                out.append(("swap_arith", i, k, f"line {ln}: '{_sym(node.op)}' -> '{_sym(new())}'"))
        elif isinstance(node, ast.Constant) and type(node.value) is int and not isinstance(node.value, bool):
            for k, d in enumerate((1, -1)):
                out.append(("off_by_one_const", i, k, f"line {ln}: constant {node.value} -> {node.value + d}"))
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Decimal"
              and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)
              and node.args[0].value.isdigit()):
            v = node.args[0].value
            out.append(("off_by_one_const", i, 0, f"line {ln}: Decimal('{v}') -> Decimal('{int(v) + 1}')"))
        elif isinstance(node, ast.If) and any(isinstance(s, ast.Raise) for s in node.body):
            out.append(("remove_check", i, 0,
                        f"line {ln}: removed check 'if {ast.unparse(node.test)}: raise ...'"))
        elif isinstance(node, ast.Name) and node.id == "ROUND_HALF_UP":
            for k, r in enumerate(_ROUNDINGS):
                out.append(("swap_rounding", i, k, f"line {ln}: ROUND_HALF_UP -> {r}"))
        elif isinstance(node, ast.alias) and node.name == "ROUND_HALF_UP":
            pass
    return out


def _apply(tree: ast.Module, site) -> ast.Module:
    operator, idx, variant, _ = site
    tree = copy.deepcopy(tree)
    nodes = list(ast.walk(tree))
    target = nodes[idx]
    if operator == "flip_comparison":
        j, k = variant
        target.ops[j] = _CMP_FLIPS[type(target.ops[j])][k]()
    elif operator == "swap_arith":
        target.op = _ARITH_SWAPS[type(target.op)][variant]()
    elif operator == "off_by_one_const":
        if isinstance(target, ast.Constant):
            target.value = target.value + (1, -1)[variant]
        else:
            c = target.args[0]
            c.value = str(int(c.value) + 1)
    elif operator == "remove_check":
        for parent in nodes:
            for field, val in ast.iter_fields(parent):
                if isinstance(val, list) and target in val:
                    pos = val.index(target)
                    val[pos:pos + 1] = []
                    if not val:
                        val.append(ast.Pass())
    elif operator == "swap_rounding":
        target.id = _ROUNDINGS[variant]
    return ast.fix_missing_locations(tree)


def generate(reference_code: str, seed: int = 0, entrypoint: str = "prorate_refund") -> list[Mutant]:
    tree = ast.parse(reference_code)
    # ROUND_HALF_UP appears both as an import alias (ast.alias, not a Name) and as a Name use.
    # Add the replacement names to the import so mutants resolve them.
    sites = _sites(tree)
    rng = random.Random(seed)
    rng.shuffle(sites)  # seeded; ids then assigned in shuffled order
    mutants: list[Mutant] = []
    seen_code: set[str] = set()
    ref_norm = ast.unparse(tree)
    for site in sites:
        mt = _apply(tree, site)
        if site[0] == "swap_rounding":
            for node in ast.walk(mt):
                if isinstance(node, ast.ImportFrom) and node.module == "decimal":
                    have = {a.name for a in node.names}
                    if site[2] is not None and _ROUNDINGS[site[2]] not in have:
                        node.names.append(ast.alias(name=_ROUNDINGS[site[2]]))
        code = ast.unparse(mt)
        if code == ref_norm or code in seen_code:
            continue
        seen_code.add(code)
        mid = len(mutants) + 1
        mutants.append({"id": mid, "split": "dev" if mid % 3 == 0 else "heldout", "operator": site[0],
                        "description": site[3], "code": code + "\n", "entrypoint": entrypoint})
    return mutants


# ---------------------------------------------------------------- equivalence detection
class _Timeout(Exception):
    pass


def _alarm(_s, _f):
    raise _Timeout()


def _load(code: str, entrypoint: str):
    ns: dict = {"__name__": "mutant_mod"}
    exec(compile(code, "<mutant>", "exec"), ns)
    return ns[entrypoint]


def _call(fn, kwargs):
    signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, 1.0)
    try:
        return ("ok", fn(**kwargs))
    except _Timeout:
        return ("timeout", None)
    except Exception:
        return ("err", None)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def fuzz_inputs(fn_name: str = "prorate_refund", n: int = 3000, seed: int = 0) -> list[dict]:
    import importlib

    from hypothesis import HealthCheck, Phase, given, seed as hseed, settings
    from engine.target import strategy_for
    got: list[dict] = []

    @hseed(seed)
    @settings(max_examples=n, database=None, phases=[Phase.generate], deadline=None,
              suppress_health_check=list(HealthCheck))
    @given(strategy_for(fn_name))
    def collect(kw):
        got.append(kw)

    collect()
    return got


def mark_equivalent(mutants: list[Mutant], reference_code: str, entrypoint: str = "prorate_refund",
                    fn_name: str = "prorate_refund", n: int = 3000) -> list[dict]:
    inputs = fuzz_inputs(fn_name, n)
    ref = _load(reference_code, entrypoint)
    ref_out = [_call(ref, kw) for kw in inputs]
    out = []
    for m in mutants:
        fn = _load(m["code"], entrypoint)
        diff = 0
        for kw, r in zip(inputs, ref_out):
            if _call(fn, kw) != r:
                diff += 1
                break
        d = dict(m)
        d["likely_equivalent"] = diff == 0
        d["fuzz_inputs"] = len(inputs)
        out.append(d)
    return out


def build_cache(fn_name: str = "prorate_refund", seed: int = 0, n: int = 3000) -> list[dict]:
    ref_code = (ROOT / "demo_target" / fn_name / "reference.py").read_text()
    ms = mark_equivalent(generate(ref_code, seed, fn_name), ref_code, fn_name, fn_name, n)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{fn_name}.json").write_text(json.dumps(ms, indent=1))
    return ms


if __name__ == "__main__":
    ms = build_cache()
    eq = [m for m in ms if m["likely_equivalent"]]
    print(f"{len(ms)} mutants, {len(eq)} likely-equivalent")
