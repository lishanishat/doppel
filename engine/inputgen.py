"""LLM-written test-input generator. Model code only ever runs in a subprocess."""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

MIN_VALID = 20
TIMEOUT_S = 20

SYSTEM = (
    "You write Python test-input generators. Reply with ONE python code block defining `def gen(rng):` "
    "that returns ONE dict of keyword arguments for the target function. Dict keys must be EXACTLY the "
    "parameter names. Values must be JSON-able (str, int, float, bool, None, list, dict). Use only the "
    "passed `rng` (a random.Random) plus the stdlib modules random, datetime, decimal, string; import them "
    "inside the file. Mix typical values with edge cases based on the spec: zero, empty, boundaries, "
    "negatives, very long values, leap days, month ends, and invalid-but-plausible values. "
    "Each call should vary; no I/O, no prints."
)


def _find_func(code: str, function_name: str) -> ast.FunctionDef:
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"code does not parse: {e}") from e
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return node
    raise ValueError(f"no function named {function_name} in the code")


def _params(fn: ast.FunctionDef) -> list[dict]:
    a = fn.args
    pos = a.posonlyargs + a.args
    defaults = [None] * (len(pos) - len(a.defaults)) + list(a.defaults)
    out = []
    for arg, d in list(zip(pos, defaults)) + list(zip(a.kwonlyargs, a.kw_defaults)):
        out.append({
            "name": arg.arg,
            "annotation": ast.unparse(arg.annotation) if arg.annotation else None,
            "default": ast.unparse(d) if d is not None else None,
        })
    return out


def _extract_code(text: str) -> str:
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


_RUNNER = """
import json, random, sys
ns = {}
exec(compile(open(sys.argv[1]).read(), "gen.py", "exec"), ns)
gen = ns["gen"]
rng = random.Random(0)
for _ in range(int(sys.argv[2])):
    try:
        print(json.dumps(gen(rng)), flush=True)
    except Exception:
        pass
"""


def _run_gen(gen_code: str, n: int) -> list[dict]:
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "gen.py").write_text(gen_code)
        (Path(d) / "run.py").write_text(_RUNNER)
        try:
            r = subprocess.run(
                [sys.executable, "-I", str(Path(d) / "run.py"), str(Path(d) / "gen.py"), str(n)],
                capture_output=True, text=True, timeout=TIMEOUT_S, cwd=d,
            )
            out = r.stdout
        except subprocess.TimeoutExpired as e:
            out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
    rows = []
    for line in out.splitlines():
        try:
            v = json.loads(line)
        except ValueError:
            continue
        if isinstance(v, dict):
            rows.append(v)
    return rows


def _validate(rows: list[dict], names: list[str]) -> list[dict]:
    seen, out = set(), []
    for r in rows:
        if set(r) != set(names):
            continue
        try:
            key = json.dumps(r, sort_keys=True)
        except (TypeError, ValueError):
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _fallback(code: str, function_name: str, n: int) -> list[dict]:
    from engine import inputgen_fallback  # lazy: built in parallel

    return inputgen_fallback.typehint_inputs(code, function_name, n)


def generate_inputs(spec_text: str, code: str, function_name: str, n: int = 300) -> list[dict]:
    fn = _find_func(code, function_name)
    params = _params(fn)
    names = [p["name"] for p in params]
    try:
        from common import llm

        user = (
            f"Target function signature and parameters:\n{json.dumps(params, indent=1)}\n\n"
            f"Function source:\n```python\n{code}\n```\n\nSpec:\n{spec_text}\n\n"
            f"Write gen(rng) returning one kwargs dict with keys exactly {names}."
        )
        text, _model = llm.complete("meta", SYSTEM, user)
        rows = _validate(_run_gen(_extract_code(text), n * 2), names)
        if len(rows) >= MIN_VALID:
            return rows[:n]
    except Exception:  # noqa: BLE001
        pass
    return _fallback(code, function_name, n)
