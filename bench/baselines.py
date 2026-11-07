"""Baselines: run a directory of test files against a mutant. caught = any test fails.

Contract for test files: see docs/BENCH.md. Tests do `from solution import prorate_refund`; the loader
writes the mutant module as `solution.py` into a temp dir and runs pytest there (subprocess).
"""
from __future__ import annotations

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


def run_tests(code: str, test_files: list[Path], timeout_s: float = 60.0) -> dict:
    """-> {"caught": bool, "status": "failed"|"passed"|"error"|"timeout", "detail": str}"""
    with tempfile.TemporaryDirectory(prefix="doppel_bl_") as d:
        dd = Path(d)
        (dd / "solution.py").write_text(code)
        for i, f in enumerate(test_files):
            shutil.copy(f, dd / f"test_{i}_{f.stem.removeprefix('test_')}.py")
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
