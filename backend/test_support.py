"""
Shared helpers for the HTTP test scripts.

Importing this keeps the login dance in one place. Every mutating endpoint
is protected since B12, so a test that POSTs without a token gets a 401 and
fails for the wrong reason - which is a confusing way to discover that the
API changed.
"""

import json
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000/api/v1"

# Shared so a test file can either use these helpers directly or pass its own
# list; either way the summary is printed from one place.
FAILURES = []

# Development credentials set by scripts/reset_user_passwords.py.
OWNER = ("owner", "Owner@2026")
MANAGER = ("manager", "Manager@2026")
STAFF = ("staff", "Staff@2026")


class Resp:
    def __init__(self, status, body, raw=b"", headers=None):
        self.status_code = status
        self._body = body
        self.raw = raw
        self.headers = headers or {}

    def json(self):
        return self._body


def _headers(raw):
    """
    Normalise response headers to lowercase keys.

    urllib hands back an email.message.Message whose keys arrive exactly as
    the server sent them; looking up 'Content-Type' can therefore miss
    while 'content-type' hits. Lowercasing once here keeps every caller from
    having to guess.
    """
    try:
        return {k.lower(): v for k, v in raw.items()}
    except AttributeError:
        return {}


def request(method, path, body=None, token=None, raw_body=None,
            content_type="application/json"):
    """Issue a request and decode the response, never raising on 4xx/5xx."""
    url = BASE + path
    data = None
    headers = {}
    if raw_body is not None:
        data = raw_body
        headers["Content-Type"] = content_type
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            payload = r.read()
            return Resp(
                r.status,
                json.loads(payload) if payload and _is_json(r.headers) else None,
                payload,
                _headers(r.headers),
            )
    except urllib.error.HTTPError as e:
        payload = e.read()
        try:
            parsed = json.loads(payload) if payload else None
        except ValueError:
            parsed = None
        return Resp(e.code, parsed, payload, _headers(e.headers or {}))


def _is_json(headers):
    ctype = headers.get("Content-Type", "") if headers else ""
    return "json" in ctype.lower()


def login(credentials=OWNER):
    """Log in and return (access_token, refresh_token). Raises on failure."""
    username, password = credentials
    r = request("POST", "/auth/login",
                {"username": username, "password": password})
    if r.status_code != 200:
        raise SystemExit(
            f"Login failed for {username}: HTTP {r.status_code} {r.json()}"
        )
    return r.json()["access_token"], r.json()["refresh_token"]


# ---------------------------------------------------------------------------
# Convenience wrappers. `token` defaults to None so read-only tests need no
# setup, and a protected call simply fails loudly.
# ---------------------------------------------------------------------------
def get(path, token=None):
    return request("GET", path, token=token)


def post(path, body, token=None):
    return request("POST", path, body, token=token)


def put(path, body, token=None):
    return request("PUT", path, body, token=token)


def delete(path, token=None):
    return request("DELETE", path, token=token)


def check(label, got, want, failures=None):
    """Compare and report. `failures` defaults to this module's list."""
    if failures is None:
        failures = FAILURES
    ok_ = got == want
    print(f"  [{'OK ' if ok_ else 'FAIL'}] {label}: {got}"
          + ("" if ok_ else f"  (expected {want})"))
    if not ok_:
        failures.append(label)
    return ok_


def ok(label, cond, detail="", failures=None):
    if failures is None:
        failures = FAILURES
    good = bool(cond)
    print(f"  [{'OK ' if good else 'FAIL'}] {label}"
          + (f": {detail}" if detail else ""))
    if not good:
        failures.append(label)
    return good


def report() -> int:
    """Print the summary and return a process exit code."""
    print("\n" + "=" * 78)
    if FAILURES:
        print(f"FAILED {len(FAILURES)}:")
        for item in FAILURES:
            print(f"  - {item}")
        return 1
    print("ALL TESTS PASSED")
    print("=" * 78)
    return 0


def section(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)
