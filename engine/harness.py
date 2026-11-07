"""Runner: one long-lived `python -I -u engine/_worker.py` per version; JSON lines; restart on fault."""
import json
import os
import select
import subprocess
import sys
import time
from pathlib import Path

from engine.protocol import encode_result

_WORKER = str(Path(__file__).resolve().parent / "_worker.py")


class BuildError(Exception):
    def __init__(self, name, msg):
        super().__init__(f"{name}: {msg}")
        self.name, self.msg = name, msg


class Runner:
    def __init__(self, name, code, entrypoint, timeout_s=2.0, build_timeout_s=10.0):
        self.name, self.code, self.entrypoint = name, code, entrypoint
        self.timeout_s, self.build_timeout_s = timeout_s, build_timeout_s
        self._proc = None
        self._buf = b""
        self._start()

    # -- process management
    def _start(self):
        self._buf = b""
        self._proc = subprocess.Popen(
            [sys.executable, "-I", "-u", _WORKER], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, bufsize=0, cwd=str(Path(_WORKER).parent.parent))
        try:
            self._send({"code": self.code, "entrypoint": self.entrypoint})
            msg = self._read(self.build_timeout_s)
        except Exception:
            self._kill()
            raise BuildError(self.name, "worker died during build")
        if msg is None:
            self._kill()
            raise BuildError(self.name, "timeout during build")
        if msg.get("error"):
            self._kill()
            raise BuildError(self.name, msg.get("msg", "build failed"))

    def _kill(self):
        p, self._proc = self._proc, None
        if p is not None:
            try:
                p.kill()
            except Exception:
                pass
            for f in (p.stdin, p.stdout):
                try:
                    f.close()
                except Exception:
                    pass
            try:
                p.wait(timeout=2)
            except Exception:
                pass

    def restart(self):
        self._kill()
        self._start()

    def close(self):
        self._kill()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def __del__(self):
        self._kill()

    # -- io
    def _send(self, obj):
        self._proc.stdin.write((json.dumps(obj) + "\n").encode())

    def _read(self, timeout):
        """Next JSON line, or None on timeout. Raises EOFError if the worker died."""
        deadline = time.monotonic() + timeout
        fd = self._proc.stdout.fileno()
        while b"\n" not in self._buf:
            left = deadline - time.monotonic()
            if left <= 0:
                return None
            if not select.select([fd], [], [], left)[0]:
                return None
            chunk = os.read(fd, 65536)
            if not chunk:
                raise EOFError("worker exited")
            self._buf += chunk
        line, self._buf = self._buf.split(b"\n", 1)
        return json.loads(line)

    def _fault(self, kind):
        try:
            self.restart()
        except BuildError:
            pass  # next call will report crash again
        return {"ok": False, "error": kind}

    def call(self, kwargs) -> dict:
        if self._proc is None or self._proc.poll() is not None:
            return self._fault("crash")
        try:
            self._send({"kwargs": kwargs})
            msg = self._read(self.timeout_s)
        except (EOFError, BrokenPipeError, OSError, ValueError):
            return self._fault("crash")
        if msg is None:
            return self._fault("timeout")
        if "error" in msg:  # worker-reported harness fault
            return {"ok": False, "error": msg["error"]}
        if not msg.get("ok"):
            return {"ok": False}
        return encode_result(msg.get("value"))
