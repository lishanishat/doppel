import json
import os

os.environ["DOPPEL_STUBS"] = "0"

from bench import api, baselines, mutate  # noqa: E402
from bench.mutate import ROOT  # noqa: E402

REF = (ROOT / "demo_target/prorate_refund/reference.py").read_text()


def test_deterministic_and_split():
    a = mutate.generate(REF, 0)
    b = mutate.generate(REF, 0)
    assert [m["code"] for m in a] == [m["code"] for m in b]
    assert all((m["split"] == "dev") == (m["id"] % 3 == 0) for m in a)
    assert all(m["code"] != REF for m in a)


def test_api_heldout_excludes_equivalent():
    ms = {m["id"]: m for m in json.loads((mutate.CACHE_DIR / "prorate_refund.json").read_text())}
    ids = api.list_mutants("heldout")
    assert ids and all(ms[i]["split"] == "heldout" and not ms[i]["likely_equivalent"] for i in ids)
    m = api.get_mutant(ids[0])
    assert set(["id", "split", "operator", "description", "code", "entrypoint"]) <= set(m)


def test_baseline_runner(tmp_path):
    t = tmp_path / "test_x.py"
    t.write_text("from solution import prorate_refund\n"
                 "def test_a():\n assert prorate_refund('30.00','2026-01-01','2026-01-31','2026-01-16')=='14.00'\n")
    assert baselines.run_tests(REF, [t])["status"] == "passed"
    bad = REF.replace("ROUND_HALF_UP", "ROUND_UP", 1).replace("(cancel - start).days + 1", "(cancel - start).days")
    assert baselines.run_tests(bad, [t])["caught"]
