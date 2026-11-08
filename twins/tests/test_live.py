import threading
import time
from pathlib import Path

from common import llm
from twins import generate

ROOT = Path(__file__).resolve().parent.parent.parent


def test_parallel_any_function_and_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("TWIN_B_PROVIDERS", "gemini,meta2")
    seen, lock = [], threading.Lock()

    def complete(provider, system, user, temperature=0.0):
        with lock:
            seen.append(provider)
        time.sleep(0.3)
        if provider == "gemini":
            raise RuntimeError("no key")
        return "```python\ndef my_fn(x):\n    return x\n```", f"{provider}/m"

    monkeypatch.setattr(llm, "complete", complete)
    t0 = time.time()
    a, b = generate.generate_twins("spec", "my_fn", "def my_fn(x)", tmp_path)
    assert time.time() - t0 < 0.8  # parallel ~0.6s, serial ~0.9s
    assert "gemini" in seen and b["model"] == "meta2/m".replace("meta2", "meta")
    assert f"# model: {b['model']}" in (tmp_path / "my_fn" / "twin_b.py").read_text()
    assert (tmp_path / "my_fn" / "manifest.json").exists()


def test_prorate_cache_hit_no_network(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("network used")

    monkeypatch.setattr(llm, "complete", boom)
    spec = (ROOT / "demo_target/prorate_refund/spec.md").read_text()
    sig = next(l.strip() for l in spec.splitlines() if "def " in l)
    v = generate.generate_twins(spec, "prorate_refund", sig)
    assert [x["name"] for x in v] == ["twin_a", "twin_b"]
