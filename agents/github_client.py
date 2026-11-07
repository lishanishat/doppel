"""Minimal GitHub REST client (requests). Token: GITHUB_TOKEN, else `gh auth token`."""
from __future__ import annotations

import base64
import os
import re
import subprocess
import time

import requests

API = "https://api.github.com"
_token_cache: str | None = None


def _error_cls():
    from agents.pipeline import UserFacingError
    return UserFacingError


def _token() -> str | None:
    global _token_cache
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        return tok
    if _token_cache is None:
        try:
            out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=10)
            _token_cache = out.stdout.strip() if out.returncode == 0 else ""
        except Exception:
            _token_cache = ""
    return _token_cache or None


def _headers() -> dict:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    tok = _token()
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def _friendly_404(path: str) -> str:
    m = re.match(r"/repos/([^/]+/[^/]+)/(pulls|issues)/(\d+)", path)
    if m:
        kind = "PR" if m.group(2) == "pulls" else "Issue"
        return f"{kind} #{m.group(3)} was not found in {m.group(1)} on GitHub."
    return f"Not found on GitHub: {path}"


def _request(method: str, path: str, **kw) -> requests.Response:
    last: Exception | None = None
    for attempt in range(3):
        try:
            r = requests.request(method, API + path, headers=_headers(), timeout=20, **kw)
            if r.status_code == 404:
                raise _error_cls()(_friendly_404(path))
            if r.status_code >= 500 or r.status_code == 429:
                last = RuntimeError(f"GitHub HTTP {r.status_code}")
            else:
                if r.status_code >= 400:
                    raise _error_cls()(f"GitHub error {r.status_code}: {r.text[:200]}")
                return r
        except requests.RequestException as e:
            last = e
        time.sleep(0.5 * (2 ** attempt))
    raise _error_cls()(f"Could not reach GitHub: {last}")


def get_pr(repo: str, n: int) -> dict:
    pr = _request("GET", f"/repos/{repo}/pulls/{n}").json()
    files_meta = _request("GET", f"/repos/{repo}/pulls/{n}/files", params={"per_page": 100}).json()
    sha = pr["head"]["sha"]
    files = []
    for f in files_meta:
        if not f["filename"].endswith(".py") or f.get("status") == "removed":
            continue
        c = _request("GET", f"/repos/{repo}/contents/{f['filename']}", params={"ref": sha}).json()
        content = base64.b64decode(c.get("content", "")).decode("utf-8", "replace")
        files.append({"path": f["filename"], "content": content})
    return {"body": pr.get("body") or "", "head_sha": sha, "files": files}


def get_issue(repo: str, n: int) -> dict:
    i = _request("GET", f"/repos/{repo}/issues/{n}").json()
    return {"title": i.get("title", ""), "body": i.get("body") or ""}


def post_review(repo: str, n: int, body: str, event: str) -> str:
    r = _request("POST", f"/repos/{repo}/pulls/{n}/reviews", json={"body": body, "event": event}).json()
    return r.get("html_url", f"https://github.com/{repo}/pull/{n}")
