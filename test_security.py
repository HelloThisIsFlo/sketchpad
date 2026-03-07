#!/usr/bin/env -S uv run python
"""Security tests for the Sketchpad MCP server.

Verifies Origin validation middleware and token authentication against
the live deployment. All tests are non-interactive (no browser needed).

Usage: uv run python test_security.py
       ./test_security.py          (if executable)
"""

import sys

import httpx

# -- Configuration -----------------------------------------------------------

SERVER_URL = "https://sketchpad.kempenich.ai"

JSONRPC_BODY = {"jsonrpc": "2.0", "method": "initialize", "id": 0}
JSONRPC_HEADERS = {"Content-Type": "application/json"}


# -- Test results tracker (same pattern as test_oauth.py) --------------------


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def pass_(self, desc: str):
        print(f"  PASS: {desc}")
        self.passed += 1

    def fail(self, desc: str):
        print(f"  FAIL: {desc}")
        self.failed += 1

    def check(self, desc: str, actual, expected):
        if actual == expected:
            self.pass_(desc)
        else:
            self.fail(f"{desc} (got {actual!r}, expected {expected!r})")

    def summary(self) -> int:
        """Print summary and return exit code (0=all passed, 1=failures)."""
        print()
        print("=== Results ===")
        print(f"{self.passed} passed, {self.failed} failed")
        print()
        if self.failed > 0:
            print("SOME CHECKS FAILED")
            return 1
        print("ALL CHECKS PASSED")
        return 0


# -- Test functions ----------------------------------------------------------


def test_bad_origin(T: TestResults, client: httpx.Client):
    """POST /mcp with a disallowed Origin header -- expect 403."""
    print()
    print("=== Test: Bad Origin ===")
    resp = client.post(
        f"{SERVER_URL}/mcp",
        json=JSONRPC_BODY,
        headers={**JSONRPC_HEADERS, "Origin": "https://evil.com"},
    )
    T.check("bad Origin returns 403", resp.status_code, 403)
    body = resp.json()
    T.check("error is origin_not_allowed", body.get("error"), "origin_not_allowed")


def test_no_origin(T: TestResults, client: httpx.Client):
    """POST /mcp with no Origin header -- expect 401 (passes Origin check, hits auth)."""
    print()
    print("=== Test: No Origin ===")
    resp = client.post(
        f"{SERVER_URL}/mcp",
        json=JSONRPC_BODY,
        headers=JSONRPC_HEADERS,
    )
    T.check("no Origin returns 401 (not 403)", resp.status_code, 401)


def test_no_token(T: TestResults, client: httpx.Client):
    """POST /mcp without Authorization -- expect 401 with WWW-Authenticate."""
    print()
    print("=== Test: No Token ===")
    resp = client.post(
        f"{SERVER_URL}/mcp",
        json=JSONRPC_BODY,
        headers=JSONRPC_HEADERS,
    )
    T.check("no token returns 401", resp.status_code, 401)
    # Case-insensitive header check
    has_www_auth = any(k.lower() == "www-authenticate" for k in resp.headers.keys())
    if has_www_auth:
        T.pass_("WWW-Authenticate header present")
    else:
        T.fail("WWW-Authenticate header missing")


def test_discovery_open(T: TestResults, client: httpx.Client):
    """Discovery endpoints remain open regardless of Origin."""
    print()
    print("=== Test: Discovery Endpoints Open ===")
    resp1 = client.get(f"{SERVER_URL}/.well-known/oauth-authorization-server")
    T.check("oauth-authorization-server returns 200", resp1.status_code, 200)

    resp2 = client.get(f"{SERVER_URL}/.well-known/oauth-protected-resource/mcp")
    T.check("oauth-protected-resource returns 200", resp2.status_code, 200)


def test_health_unaffected(T: TestResults, client: httpx.Client):
    """GET /health with evil Origin -- should still return 200."""
    print()
    print("=== Test: Health Unaffected by Origin ===")
    resp = client.get(
        f"{SERVER_URL}/health",
        headers={"Origin": "https://evil.com"},
    )
    T.check("health returns 200 despite bad Origin", resp.status_code, 200)


# -- Main --------------------------------------------------------------------


def main():
    T = TestResults()
    client = httpx.Client(timeout=30, follow_redirects=False)

    try:
        test_bad_origin(T, client)
        test_no_origin(T, client)
        test_no_token(T, client)
        test_discovery_open(T, client)
        test_health_unaffected(T, client)
    finally:
        client.close()

    sys.exit(T.summary())


if __name__ == "__main__":
    main()
