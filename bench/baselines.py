"""Baselines: run a directory of test files against a mutant. caught = any test fails.

Contract for test files: see docs/BENCH.md. Tests do `from solution import prorate_refund`; the loader
writes the mutant module as `solution.py` into a temp dir and runs pytest there (subprocess).
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PR_TEST_DIR = ROOT / "demo_target" / "prorate_refund" / "ai_pr"
LLM_TEST_DIR = ROOT / "bench" / "llm_artifacts"


def find_tests(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    files = set(directory.rglob("test_*.py")) | set(directory.rglob("*_test.py"))
    return sorted(files)


_RESULT_RE = re.compile(r"^(PASSED|FAILED|ERROR)\s+(\S+)", re.M)
_valid_cache: dict = {}


def _node_results(code: str, test_files: list[Path], timeout_s: float) -> tuple[dict, int]:
    """Run the tests on `code`; return ({test id: PASSED|FAILED|ERROR}, pytest returncode)."""
    with tempfile.TemporaryDirectory(prefix="doppel_bl_") as d:
        dd = Path(d)
        _stage(dd, code, test_files)
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-rA", "--tb=no", "-p", "no:cacheprovider",
                            "--no-header", "."], cwd=dd, capture_output=True, text=True, timeout=timeout_s)
        return {m.group(2): m.group(1) for m in _RESULT_RE.finditer(p.stdout)}, p.returncode


def valid_test_ids(valid_on: str, test_files: list[Path], timeout_s: float = 60.0) -> set:
    """Ids of the tests that PASS on the known-correct code. Only these can count as catching a bug."""
    key = (tuple(str(f) for f in test_files), hash(valid_on))
    if key not in _valid_cache:
        res, _ = _node_results(valid_on, test_files, timeout_s)
        _valid_cache[key] = {k for k, v in res.items() if v == "PASSED"}
    return _valid_cache[key]


def _stage(dd: Path, code: str, test_files: list[Path]) -> None:
    (dd / "solution.py").write_text(code)
    for i, f in enumerate(test_files):
        shutil.copy(f, dd / f"test_{i}_{f.stem.removeprefix('test_')}.py")
        # Tests written by the PR's author import the function from the author's own module name
        # (e.g. `from billing import ...`). Save the code under that name too, leaving the tests unedited.
        for mod in re.findall(r"^\s*from\s+([A-Za-z_]\w*)\s+import", f.read_text(), re.M):
            if mod not in sys.stdlib_module_names and mod not in ("pytest", "hypothesis", "solution"):
                (dd / f"{mod}.py").write_text(code)


def run_tests(code: str, test_files: list[Path], timeout_s: float = 60.0, valid_on: str | None = None) -> dict:
    """-> {"caught": bool, "status": "failed"|"passed"|"error"|"timeout", "detail": str}

    With `valid_on` (the correct reference code), only tests that pass on it can count as catching a bug.
    """
    if valid_on is not None:
        valid = valid_test_ids(valid_on, test_files, timeout_s)
        try:
            res, rc = _node_results(code, test_files, timeout_s)
        except subprocess.TimeoutExpired:
            return {"caught": True, "status": "timeout", "detail": "tests timed out (counted as failure)"}
        failed_valid = sorted(k for k, v in res.items() if v == "FAILED" and k in valid)
        if failed_valid:
            return {"caught": True, "status": "failed", "detail": f"{len(failed_valid)} valid test(s) failed (of {len(valid)})"}
        if rc not in (0, 1) and not res:
            return {"caught": False, "status": "error", "detail": "collection error"}
        return {"caught": False, "status": "passed", "detail": f"no valid test failed (of {len(valid)}; tests failing on the reference are excluded)"}
    with tempfile.TemporaryDirectory(prefix="doppel_bl_") as d:
        dd = Path(d)
        _stage(dd, code, test_files)
        try:
            p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
                                "--no-header", "--tb=line", "."], cwd=dd, capture_output=True, text=True,
                               timeout=timeout_s)
        except subprocess.TimeoutExpired:
            return {"caught": True, "status": "timeout", "detail": "tests timed out (counted as failure)"}
        tail = (p.stdout + p.stderr).strip().splitlines()[-1:] or [""]
        # pytest exit codes: 0 pass, 1 tests failed, 2+ collection/usage error, 5 no tests collected
        if p.returncode == 0:
            return {"caught": False, "status": "passed", "detail": tail[0]}
        if p.returncode == 1:
            return {"caught": True, "status": "failed", "detail": tail[0]}
        return {"caught": False, "status": "error", "detail": tail[0]}


def available(directory: Path) -> bool:
    return bool(find_tests(directory))
