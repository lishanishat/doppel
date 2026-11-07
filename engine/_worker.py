"""Sandbox-free worker loop: self-contained (runs under `python -I`, no engine imports).

Protocol on the ORIGINAL stdout fd (kept private); fd 1 / sys.stdout are redirected to stderr so
user-code prints cannot corrupt it. First stdin line: {"code":..,"entrypoint":..} ->
{"ready":true} | {"error":"build","msg":..}. Then {"kwargs":{..}} -> {"ok":true,"value":..}|{"ok":false}.
"""
import json
import os
import sys
from datetime import date
from decimal import Decimal


def _default(o):
    if isinstance(o, Decimal):
        return format(o, "f")
    if isinstance(o, date):
        return o.isoformat()
    return repr(o)


def main():
    out = os.fdopen(os.dup(1), "w", buffering=1, encoding="utf-8")
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    inp = open(os.dup(0), "r", encoding="utf-8")
    sys.stdin = open(os.devnull)

    def send(obj):
        out.write(json.dumps(obj, default=_default) + "\n")
        out.flush()

    try:
        init = json.loads(inp.readline())
        ns = {"__name__": "doppel_target"}
        exec(compile(init["code"], "<target>", "exec"), ns)
        fn = ns[init["entrypoint"]]
        if not callable(fn):
            raise TypeError("entrypoint is not callable")
    except BaseException as e:  # noqa: BLE001
        send({"error": "build", "msg": f"{type(e).__name__}: {e}"})
        return
    send({"ready": True})
    for line in inp:
        line = line.strip()
        if not line:
            continue
        try:
            kwargs = json.loads(line)["kwargs"]
        except Exception as e:  # noqa: BLE001
            send({"ok": False, "error": f"bad request: {e}"})
            continue
        try:
            res = {"ok": True, "value": fn(**kwargs)}
            json.dumps(res, default=_default)
        except BaseException:  # noqa: BLE001
            res = {"ok": False}
        send(res)


if __name__ == "__main__":
    main()
