"""Chaos injection for the recovery demo: make one version hard-kill its own process mid-run.

`python -m engine.cli verify ... --chaos twin_b` wraps that version's source so the worker process dies
abruptly (os._exit, no cleanup) on its 25th call. The Referee must then return UNPROVEN with a plain-English
reason, never VERIFIED or BLOCKED on partial evidence.
"""


def inject_kill(code: str, entry: str, after: int = 25) -> str:
    return code + f'''

# --- chaos injection (engine.chaos): hard-kill this process on call #{after}
_chaos_orig, _chaos_n = {entry}, 0


def {entry}(*a, **k):
    global _chaos_n
    _chaos_n += 1
    if _chaos_n == {after}:
        import os
        os._exit(137)
    return _chaos_orig(*a, **k)
'''
