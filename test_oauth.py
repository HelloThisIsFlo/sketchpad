#!/usr/bin/env -S uv run python
"""End-to-end OAuth 2.1 flow test for the Sketchpad MCP server.

Exercises: discovery, 401 check, DCR, authorization, token exchange,
refresh, and MCP tool calls via JSON-RPC over Streamable HTTP.

Prerequisites: Start the MCP server and cloudflared tunnel before running.
See docs/local-development.md for setup instructions.

Usage: uv run python test_oauth.py
       ./test_oauth.py          (if executable)
"""

import base64
import hashlib
import http.server
import json
import os
import secrets
import sys
import threading
import time
import urllib.parse
import webbrowser

import httpx
from dotenv import dotenv_values

# -- Configuration -----------------------------------------------------------

SERVER_PORT = 8000
CALLBACK_PORT = 9999
AUTH_TIMEOUT = 120
NO_REFRESH_PROVIDERS = {"github"}


# -- Test results tracker ----------------------------------------------------


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def pass_(self, desc: str):
        print(f"  PASS: {desc}")
        self.passed += 1

    def fail(self, desc: str):
        print(f"  FAIL: {desc}")
        self.failed += 1

    def skip(self, desc: str):
        print(f"  SKIP: {desc}")
        self.skipped += 1

    def check(self, desc: str, actual, expected):
        if actual == expected:
            self.pass_(desc)
        else:
            self.fail(f"{desc} (got {actual!r}, expected {expected!r})")

    def check_not_empty(self, desc: str, value):
        if value and value != "null":
            self.pass_(desc)
        else:
            self.fail(f"{desc} (value is empty or null)")

    def summary(self) -> int:
        """Print summary and return exit code (0=all passed, 1=failures)."""
        print()
        print("=== Results ===")
        print(f"{self.passed} passed, {self.failed} failed, {self.skipped} skipped")
        print()
        if self.failed > 0:
            print("SOME CHECKS FAILED")
            return 1
        print("ALL CHECKS PASSED")
        return 0


# -- SSE / MCP helpers -------------------------------------------------------


def parse_sse(text: str):
    """Extract the first JSON object from an SSE or plain-JSON response."""
    # If it parses directly as JSON, return it (non-SSE response)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Otherwise, look for SSE data: lines
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[len("data:") :].strip()
            if payload:
                try:
                    return json.loads(payload)
                except json.JSONDecodeError:
                    continue
    raise ValueError(f"No JSON found in response:\n{text[:500]}")


def mcp_request(
    client: httpx.Client,
    url: str,
    payload: dict,
    token: str,
    session_id: str | None = None,
) -> tuple[dict, str | None]:
    """POST a JSON-RPC request to /mcp with correct headers.

    Returns (parsed_json, session_id). The session_id may be updated
    from the Mcp-Session-Id response header.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    resp = client.post(url, json=payload, headers=headers)
    resp.raise_for_status()

    new_session_id = resp.headers.get("mcp-session-id", session_id)
    body = parse_sse(resp.text)
    return body, new_session_id


def wait_for_url(url: str, timeout: float = 10, interval: float = 0.5) -> bool:
    """Poll a URL until it returns 2xx. Returns True if reachable."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            r = httpx.get(url, timeout=3, follow_redirects=True)
            if r.is_success:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(interval)
    return False


# -- OAuth callback server ---------------------------------------------------


class CallbackServer:
    """Threaded HTTP server that listens for the OAuth redirect callback."""

    def __init__(self, port: int, expected_state: str):
        self.port = port
        self.expected_state = expected_state
        self.auth_code: str | None = None
        self.error: str | None = None
        self._server: http.server.HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()

    def start(self):
        parent = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                params = urllib.parse.parse_qs(parsed.query)

                if parsed.path != "/callback":
                    self.send_response(404)
                    self.end_headers()
                    return

                error = params.get("error", [None])[0]
                if error:
                    desc = params.get("error_description", [""])[0]
                    parent.error = f"{error}: {desc}"
                    self._respond(400, "Authorization Failed", parent.error)
                    return

                state = params.get("state", [None])[0]
                if state != parent.expected_state:
                    parent.error = (
                        f"State mismatch: expected {parent.expected_state}, got {state}"
                    )
                    self._respond(400, "Authorization Failed", parent.error)
                    return

                code = params.get("code", [None])[0]
                if not code:
                    parent.error = "No authorization code received"
                    self._respond(400, "Authorization Failed", parent.error)
                    return

                parent.auth_code = code
                self._respond(
                    200,
                    "Authorization Successful",
                    "You can close this tab and return to the terminal.",
                )

            def _respond(self, status: int, title: str, message: str):
                color = "#16a34a" if status == 200 else "#dc2626"
                bg = "#f0fdf4" if status == 200 else "#fef2f2"
                html = (
                    f"<!DOCTYPE html><html><head><title>{title}</title></head>"
                    f'<body style="font-family:system-ui,sans-serif;display:flex;'
                    f"justify-content:center;align-items:center;height:100vh;margin:0;"
                    f'background:{bg}"><div style="text-align:center">'
                    f'<h1 style="color:{color}">{title}</h1>'
                    f"<p>{message}</p></div></body></html>"
                )
                self.send_response(status)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(html.encode())

            def log_message(self, format, *args):
                pass  # Suppress request logging

        self._server = http.server.HTTPServer(("127.0.0.1", self.port), Handler)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5)

    def _serve(self):
        self._ready.set()
        self._server.handle_request()  # Serve exactly one request

    def wait_for_code(self, timeout: float = AUTH_TIMEOUT) -> str | None:
        """Block until auth code is received or timeout expires."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.auth_code or self.error:
                break
            time.sleep(0.5)
        return self.auth_code

    def shutdown(self):
        if self._server:
            self._server.server_close()


# -- PKCE helpers ------------------------------------------------------------


def generate_pkce() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge (S256)."""
    verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


# -- Main flow ---------------------------------------------------------------


def main():
    T = TestResults()

    # ================================================================
    # Preflight
    # ================================================================
    print("=== Preflight Checks ===")
    print()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, ".env")
    if not os.path.isfile(env_path):
        print(f"FATAL: .env file not found at {env_path}")
        print("Copy .env.example to .env and fill in the values.")
        sys.exit(1)

    env = dotenv_values(env_path)
    provider = env.get("OAUTH_PROVIDER", "github").lower()
    print(f"  OAUTH_PROVIDER: {provider}")

    # Check required keys
    required = ["JWT_SIGNING_KEY", "STORAGE_ENCRYPTION_KEY"]
    if provider == "github":
        required += ["GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET"]
    missing = [k for k in required if not env.get(k)]
    if missing:
        print(f"FATAL: Missing required .env variables: {', '.join(missing)}")
        sys.exit(1)
    print("  .env secrets: present -- OK")

    server_url = env.get("SERVER_URL", "")
    if not server_url or server_url.startswith("http://localhost"):
        print(
            "FATAL: SERVER_URL in .env must be set to your tunnel URL (not localhost)."
        )
        sys.exit(1)
    print(f"  SERVER_URL: {server_url} -- OK")

    print()

    # ================================================================
    # Setup — interactive prompts
    # ================================================================
    print("=== Setup ===")
    print()

    print("  Start the MCP server in another terminal:")
    print("    uv run python -m sketchpad")
    print()
    input("  Press Enter when the server is running...")

    local_discovery = (
        f"http://localhost:{SERVER_PORT}/.well-known/oauth-authorization-server"
    )
    while True:
        if wait_for_url(local_discovery, timeout=3):
            print(f"  Server on localhost:{SERVER_PORT} -- OK")
            break
        print(f"  Server not reachable on localhost:{SERVER_PORT}.")
        input("  Press Enter to retry, or Ctrl-C to abort...")

    print()
    print("  Start the tunnel in another terminal:")
    print("    cloudflared tunnel run")
    print()
    input("  Press Enter when the tunnel is running...")

    tunnel_discovery = f"{server_url}/.well-known/oauth-authorization-server"
    while True:
        if wait_for_url(tunnel_discovery, timeout=5):
            print(f"  Tunnel at {server_url} -- OK")
            break
        print(f"  Tunnel not reachable at {server_url}.")
        input("  Press Enter to retry, or Ctrl-C to abort...")

    print()
    print("  Setup complete! Server and tunnel are both reachable.")
    input("  Press Enter to run the tests...")

    # Shared HTTP client for all requests
    client = httpx.Client(timeout=30, follow_redirects=False)

    try:
        # ================================================================
        # Step 1: Discovery
        # ================================================================
        print()
        print("=== Step 1: Discovery ===")
        print(f"Target server: {server_url}")
        print()

        print("Fetching /.well-known/oauth-authorization-server ...")
        as_meta = client.get(
            f"{server_url}/.well-known/oauth-authorization-server"
        ).json()
        print(json.dumps(as_meta, indent=2))

        auth_endpoint = as_meta.get("authorization_endpoint", "")
        token_endpoint = as_meta.get("token_endpoint", "")
        reg_endpoint = as_meta.get("registration_endpoint", "")

        T.check_not_empty("authorization_endpoint present", auth_endpoint)
        T.check_not_empty("token_endpoint present", token_endpoint)
        T.check_not_empty("registration_endpoint present", reg_endpoint)

        print()
        print(
            "Fetching /.well-known/oauth-protected-resource/mcp (RFC 9728 path-aware) ..."
        )
        pr_resp = client.get(f"{server_url}/.well-known/oauth-protected-resource/mcp")
        if pr_resp.status_code != 200:
            print(f"  FAIL: returned {pr_resp.status_code}")
            print(
                "        (RFC 9728 Section 3.1: path-aware URL includes the MCP resource path)"
            )
            print()
            print("=== ABORTED: DISC-02 is a required endpoint ===")
            sys.exit(1)
        pr_meta = pr_resp.json()
        print(json.dumps(pr_meta, indent=2))

        resource = pr_meta.get("resource", "")
        T.check_not_empty("resource field present", resource)

        # ================================================================
        # Step 2: Unauthenticated request (expect 401)
        # ================================================================
        print()
        print("=== Step 2: Unauthenticated Request (expect 401) ===")

        unauth_resp = client.post(
            f"{server_url}/mcp",
            json={"jsonrpc": "2.0", "method": "initialize", "id": 0},
            headers={"Content-Type": "application/json"},
        )
        print(f"POST /mcp without token: HTTP {unauth_resp.status_code}")
        T.check("401 for unauthenticated request", unauth_resp.status_code, 401)

        www_auth = unauth_resp.headers.get("www-authenticate", "")
        if www_auth:
            print(f"  WWW-Authenticate: {www_auth}")
        else:
            print("  (no WWW-Authenticate header found)")

        # ================================================================
        # Step 3: Dynamic Client Registration
        # ================================================================
        print()
        print("=== Step 3: Dynamic Client Registration ===")

        redirect_uri = f"http://localhost:{CALLBACK_PORT}/callback"
        dcr_resp = client.post(
            f"{server_url}/register",
            json={
                "client_name": "test-oauth-script",
                "redirect_uris": [redirect_uri],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
            },
        )
        dcr_resp.raise_for_status()
        dcr_data = dcr_resp.json()
        print(json.dumps(dcr_data, indent=2))

        client_id = dcr_data.get("client_id", "")
        T.check_not_empty("client_id returned", client_id)
        print(f"Got client_id: {client_id}")

        # ================================================================
        # Step 4: Authorization (browser-based)
        # ================================================================
        print()
        print("=== Step 4: Authorization (browser-based) ===")

        code_verifier, code_challenge = generate_pkce()
        state = secrets.token_hex(16)

        auth_url = (
            f"{server_url}/authorize?"
            f"response_type=code&client_id={client_id}"
            f"&redirect_uri={urllib.parse.quote(redirect_uri, safe='')}"
            f"&code_challenge={code_challenge}"
            f"&code_challenge_method=S256&state={state}"
        )

        callback = CallbackServer(CALLBACK_PORT, state)
        callback.start()
        print(f"  Callback listener started on port {CALLBACK_PORT}")

        print()
        print("Opening browser for authorization...")
        print(f"  URL: {auth_url}")
        print()
        webbrowser.open(auth_url)

        print(f"Waiting for authorization (up to {AUTH_TIMEOUT}s)...")
        auth_code = callback.wait_for_code(AUTH_TIMEOUT)
        callback.shutdown()

        if callback.error:
            T.fail(f"Authorization error: {callback.error}")
            sys.exit(T.summary())

        if not auth_code:
            T.fail(f"Authorization timed out after {AUTH_TIMEOUT}s")
            sys.exit(T.summary())

        T.pass_("Authorization code received via callback")

        # ================================================================
        # Step 5: Token Exchange
        # ================================================================
        print()
        print("=== Step 5: Token Exchange ===")

        token_resp = client.post(
            f"{server_url}/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        print(json.dumps(token_data, indent=2))

        access_token = token_data.get("access_token", "")
        refresh_token = token_data.get("refresh_token", "")
        expires_in = token_data.get("expires_in", "")

        T.check_not_empty("access_token received", access_token)
        if refresh_token:
            T.pass_("refresh_token received")
        elif provider in NO_REFRESH_PROVIDERS:
            T.skip(f"no refresh_token ({provider} doesn't issue them)")
        else:
            T.fail(f"refresh_token missing ({provider} should issue one)")
        T.check_not_empty("expires_in present", str(expires_in))

        # ================================================================
        # Step 6: Refresh Token
        # ================================================================
        print()
        print("=== Step 6: Refresh Token ===")

        if refresh_token:
            refresh_resp = client.post(
                f"{server_url}/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": client_id,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            refresh_resp.raise_for_status()
            refresh_data = refresh_resp.json()
            print(json.dumps(refresh_data, indent=2))

            new_access_token = refresh_data.get("access_token", "")
            T.check_not_empty("new access_token from refresh", new_access_token)
            access_token = new_access_token  # Use refreshed token going forward
        else:
            T.skip(f"token refresh (no refresh_token available from {provider})")

        # ================================================================
        # Step 7: MCP Tool Calls
        # ================================================================
        print()
        print("=== Step 7: MCP Tool Calls ===")

        mcp_url = f"{server_url}/mcp"
        session_id = None

        # 7a: Initialize
        print("Sending initialize request...")
        init_body, session_id = mcp_request(
            client,
            mcp_url,
            {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test-oauth-script", "version": "1.0.0"},
                },
                "id": 1,
            },
            access_token,
            session_id,
        )
        print(json.dumps(init_body, indent=2))

        proto_version = (init_body.get("result") or {}).get("protocolVersion", "")
        T.check_not_empty("initialize returned protocolVersion", proto_version)
        if session_id:
            print(f"Got Mcp-Session-Id: {session_id}")

        # Send initialized notification (fire-and-forget)
        print()
        print("Sending initialized notification...")
        try:
            mcp_request(
                client,
                mcp_url,
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                },
                access_token,
                session_id,
            )
        except Exception:
            pass  # Notifications may return empty or 202

        # 7b: tools/list
        print()
        print("Calling tools/list...")
        tools_body, session_id = mcp_request(
            client,
            mcp_url,
            {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 2,
            },
            access_token,
            session_id,
        )
        print(json.dumps(tools_body, indent=2))

        tools = (tools_body.get("result") or {}).get("tools", [])
        T.check("tools/list returns 2 tools", len(tools), 2)

        tool_names = {t["name"] for t in tools}
        T.check_not_empty(
            "read_file tool present", "read_file" if "read_file" in tool_names else ""
        )
        T.check_not_empty(
            "write_file tool present",
            "write_file" if "write_file" in tool_names else "",
        )

        # 7c: read_file
        print()
        print("Calling read_file...")
        read_body, session_id = mcp_request(
            client,
            mcp_url,
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "read_file", "arguments": {}},
                "id": 3,
            },
            access_token,
            session_id,
        )
        print(json.dumps(read_body, indent=2))

        read_content = ""
        result_content = (read_body.get("result") or {}).get("content", [])
        if result_content:
            read_content = result_content[0].get("text", "")
        T.check_not_empty("read_file returned content", read_content)

        # 7d: write_file
        print()
        print("Calling write_file...")
        write_body, session_id = mcp_request(
            client,
            mcp_url,
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "write_file",
                    "arguments": {"content": "Hello from test_oauth.py!"},
                },
                "id": 4,
            },
            access_token,
            session_id,
        )
        print(json.dumps(write_body, indent=2))

        write_content = ""
        result_content = (write_body.get("result") or {}).get("content", [])
        if result_content:
            write_content = result_content[0].get("text", "")
        T.check_not_empty("write_file returned confirmation", write_content)

        # 7e: Read back written content
        print()
        print("Calling read_file again (verify written content)...")
        readback_body, session_id = mcp_request(
            client,
            mcp_url,
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "read_file", "arguments": {}},
                "id": 5,
            },
            access_token,
            session_id,
        )
        print(json.dumps(readback_body, indent=2))

        readback_content = ""
        result_content = (readback_body.get("result") or {}).get("content", [])
        if result_content:
            readback_content = result_content[0].get("text", "")
        T.check(
            "read_file returns written content",
            readback_content,
            "Hello from test_oauth.py!",
        )

    finally:
        client.close()

    sys.exit(T.summary())


if __name__ == "__main__":
    main()
