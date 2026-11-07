"""Referee: drive pr/twin_a/twin_b with identical Hypothesis inputs, vote, shrink, confirm.

run(target, versions, seed, max_examples, time_budget_s) -> RefereeResult (dict):
  n_inputs, disagreements, confirmed[Counterexample], flaky, faults{name:int},
  samples[<=200 {"input", "outputs"}], timings{...}, plus optional "candidates", "stopped".
BuildError from Runner construction propagates to the caller (engine.api handles it).
"""
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor

from hypothesis import HealthCheck, given, seed as hyp_seed, settings

from engine import protocol
from engine.harness import Runner

K_MAX = 5              # distinct counterexamples (by vote pattern / partition)
SHRINK_ROUND_S = 6.0   # shrink time cap per counterexample
SHRINK_TOTAL_S = 15.0  # shrink time cap overall
N_SAMPLES = 200


def _clean(res):
    """Contract form: {"ok","value"} only; raised -> {"ok": False}."""
    if res.get("ok"):
        return {"ok": True, "value": res.get("value")}
    return {"ok": False}


def _groups(outputs):
    g = {}
    for n, r in outputs.items():
        g.setdefault(protocol.key(r), []).append(n)
    return sorted(g.values(), key=lambda x: (-len(x), x))


def vote(outputs):
    """-> (vote_str, majority_names): "3-0" | "2-1" | "1-1-1"; majority [] for a 3-way split."""
    gs = _groups(outputs)
    if len(gs) == 1:
        return "3-0", sorted(gs[0])
    if len(gs) == 2:
        return "2-1", sorted(gs[0])
    return "1-1-1", []


def _signature(outputs):
    """Partition of version names by identical result (distinct disagreement shapes)."""
    return tuple(tuple(sorted(g)) for g in sorted(_groups(outputs)))


def _pr_outvoted(sig):
    """True if the partition is twins-together vs PR alone (a 2-1 the PR loses)."""
    return len(sig) == 2 and ("pr",) in sig


class _Disagree(Exception):
    pass


class _Ctx:
    def __init__(self, runners, seed, max_examples, deadline, pool):
        self.runners, self.pool = runners, pool
        self.seed, self.max_examples, self.deadline = seed, max_examples, deadline
        self.rng = random.Random(seed)
        self.cache = {}
        self.seen = set()
        self.n_inputs = 0
        self.disagreements = 0
        self.faults = {r.name: 0 for r in runners}
        self.n_calls = 0
        self.call_time = 0.0
        self.dis_samples, self.ok_samples, self.ok_seen = [], [], 0
        self.excluded = set()
        self.locked = None
        self.best = None
        self.shrink_deadline = 0.0
        self.shrink_spent = 0.0

    def call_all(self, kwargs):
        t = time.perf_counter()
        futs = [self.pool.submit(r.call, kwargs) for r in self.runners]
        outs = {}
        for r, f in zip(self.runners, futs):
            outs[r.name] = f.result()
        self.n_calls += 1
        self.call_time += time.perf_counter() - t
        return outs

    def evaluate(self, kwargs):
        k = json.dumps(kwargs, sort_keys=True, default=str)
        if k in self.cache:
            return k, self.cache[k]
        outs = self.call_all(kwargs)
        for n, r in outs.items():
            if "error" in r:
                self.faults[n] += 1
        self.cache[k] = outs
        return k, outs

    def _sample(self, kwargs, outs, dis):
        item = {"input": json.loads(json.dumps(kwargs, default=str)),
                "outputs": {n: _clean(r) for n, r in outs.items()}}
        if dis:
            if len(self.dis_samples) < 40:
                self.dis_samples.append(item)
            return
        self.ok_seen += 1
        if len(self.ok_samples) < N_SAMPLES - 40:
            self.ok_samples.append(item)
        else:
            j = self.rng.randrange(self.ok_seen)
            if j < len(self.ok_samples):
                self.ok_samples[j] = item

    def step(self, kwargs):
        now = time.monotonic()
        if self.locked is None:
            if now >= self.deadline or len(self.seen) >= self.max_examples and \
                    json.dumps(kwargs, sort_keys=True, default=str) not in self.seen:
                return
        elif now >= self.shrink_deadline:
            return
        k, outs = self.evaluate(kwargs)
        faulty = any("error" in r for r in outs.values())
        first = k not in self.seen
        if self.locked is None and first:
            self.seen.add(k)
            self.n_inputs += 1
            dis = (not faulty) and len(_groups(outs)) > 1
            if dis:
                self.disagreements += 1
            if not faulty:
                self._sample(kwargs, outs, dis)
        if faulty or len(_groups(outs)) == 1:
            return
        sig = _signature(outs)
        if self.locked is None:
            if sig in self.excluded:
                return
            self.locked = sig
            self.shrink_deadline = min(self.deadline, now + SHRINK_ROUND_S,
                                       now + max(0.0, SHRINK_TOTAL_S - self.shrink_spent))
        elif sig != self.locked:
            return
        self.best = (json.loads(json.dumps(kwargs, default=str)), outs)
        raise _Disagree()


def _explore_round(strategy, ctx, max_examples):
    @hyp_seed(ctx.seed)
    @settings(deadline=None, database=None, max_examples=max_examples,
              suppress_health_check=list(HealthCheck), derandomize=False)
    @given(strategy)
    def test(kwargs):
        ctx.step(kwargs)

    try:
        test()
    except Exception:
        pass  # _Disagree / Flaky / ExceptionGroup: result is in ctx.best


def _confirm(runners, kwargs, sig):
    """Two passes, each on freshly restarted runners. -> (vote_str, majority, outputs) or None."""
    passes = []
    for _ in range(2):
        for r in runners:
            r.restart()
        outs = {r.name: r.call(kwargs) for r in runners}
        if any("error" in o for o in outs.values()):
            return None
        passes.append(outs)
    a, b = passes
    if _signature(a) != sig or _signature(b) != sig:
        return None
    if any(protocol.key(a[n]) != protocol.key(b[n]) for n in a):
        return None
    v, maj = vote(a)
    return v, maj, a


def run(target, versions, seed=0, max_examples=2000, time_budget_s=60):
    t0 = time.monotonic()
    p0 = time.perf_counter()
    strategy = target.strategy
    if callable(strategy):
        strategy = strategy()
    runners = []
    try:
        for v in versions:
            runners.append(Runner(v["name"], v["code"], v["entrypoint"]))
        reserve = min(8.0, 0.25 * time_budget_s)
        deadline = t0 + max(0.0, time_budget_s - reserve)
        with ThreadPoolExecutor(max_workers=len(runners)) as pool:
            ctx = _Ctx(runners, seed, max_examples, deadline, pool)
            candidates, pre = [], {}
            explore_s = shrink_s = early_confirm_s = 0.0
            for _ in range(K_MAX):
                ts = time.perf_counter()
                ctx.locked, ctx.best = None, None
                _explore_round(strategy, ctx, max_examples)
                dt = time.perf_counter() - ts
                if ctx.best is None:
                    explore_s += dt
                    break
                shrink_s += min(dt, ctx.shrink_spent + SHRINK_ROUND_S)
                ctx.shrink_spent += min(dt, SHRINK_ROUND_S)
                candidates.append((ctx.best, ctx.locked))
                ctx.excluded.add(ctx.locked)
                if _pr_outvoted(ctx.locked):
                    # BLOCKED outranks every other verdict: confirm now and stop exploring if it holds
                    tc = time.perf_counter()
                    res = _confirm(runners, ctx.best[0], ctx.locked)
                    early_confirm_s += time.perf_counter() - tc
                    pre[len(candidates) - 1] = res
                    if res is not None:
                        break
                if time.monotonic() >= deadline or ctx.shrink_spent >= SHRINK_TOTAL_S:
                    break
            tc = time.perf_counter()
            confirmed, flaky = [], 0
            for i, ((kwargs, _outs), sig) in enumerate(candidates):
                res = pre[i] if i in pre else _confirm(runners, kwargs, sig)
                if res is None:
                    flaky += 1
                    continue
                v, maj, outs = res
                confirmed.append({"input": kwargs,
                                  "outputs": {n: _clean(o) for n, o in outs.items()},
                                  "vote": v, "majority": maj})
            confirm_s = time.perf_counter() - tc + early_confirm_s
    finally:
        for r in runners:
            try:
                r.close()
            except Exception:
                pass
    total = time.perf_counter() - p0
    samples = (ctx.dis_samples + ctx.ok_samples)[:N_SAMPLES]
    return {
        "n_inputs": ctx.n_inputs,
        "disagreements": ctx.disagreements,
        "confirmed": confirmed,
        "flaky": flaky,
        "faults": ctx.faults,
        "samples": samples,
        "candidates": len(candidates),
        "timings": {"total_s": round(total, 3), "explore_plus_shrink_s": round(total - confirm_s, 3),
                    "confirm_s": round(confirm_s, 3), "calls": ctx.n_calls,
                    "calls_per_s": round(ctx.n_calls / ctx.call_time, 1) if ctx.call_time else 0.0},
    }
