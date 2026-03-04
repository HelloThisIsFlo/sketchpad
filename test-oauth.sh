#!/usr/bin/env bash
# =============================================================================
# End-to-end OAuth flow test for the Sketchpad MCP server.
#
# This is the PRIMARY test client per project decision. It exercises the full
# OAuth 2.1 flow: discovery, 401 check, DCR, authorization, token exchange,
# refresh, and MCP tool calls via JSON-RPC over Streamable HTTP.
#
# Prerequisites: Start the MCP server and cloudflared tunnel before running.
# See docs/local-development.md for setup instructions.
#
# The only manual step during the test is completing GitHub login in the browser.
#
# Usage: ./test-oauth.sh
# Requirements: curl, jq, openssl
# =============================================================================

set -euo pipefail

# -- Configuration -----------------------------------------------------------
SERVER_PORT=8000
CALLBACK_PORT=9999
AUTH_TIMEOUT=120
TMPDIR_BASE="/tmp/sketchpad-oauth-test"

# -- State --------------------------------------------------------------------
PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0
PIDS=()

# -- Helpers ------------------------------------------------------------------
pass() {
    echo "  PASS: $1"
    PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
    echo "  FAIL: $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

skip() {
    echo "  SKIP: $1"
    SKIP_COUNT=$((SKIP_COUNT + 1))
}

check() {
    # Usage: check "description" "actual" "expected"
    if [ "$2" = "$3" ]; then
        pass "$1"
    else
        fail "$1 (got '$2', expected '$3')"
    fi
}

check_not_empty() {
    # Usage: check_not_empty "description" "value"
    if [ -n "$2" ] && [ "$2" != "null" ]; then
        pass "$1"
    else
        fail "$1 (value is empty or null)"
    fi
}

cleanup() {
    echo ""
    echo "--- Cleaning up ---"
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
        fi
    done
    rm -rf "$TMPDIR_BASE"
    echo "Done."
}
trap cleanup EXIT

# =============================================================================
echo "=== Preflight Checks ==="
echo ""

# -- Check dependencies ------------------------------------------------------
MISSING=()
for cmd in curl jq openssl; do
    if ! command -v "$cmd" &>/dev/null; then
        MISSING+=("$cmd")
    fi
done
if [ ${#MISSING[@]} -gt 0 ]; then
    echo "FATAL: Missing required commands: ${MISSING[*]}"
    echo "Install them before running this script."
    exit 1
fi
echo "  Dependencies: curl, jq, openssl -- OK"

# -- Validate .env ------------------------------------------------------------
ENV_FILE="$(cd "$(dirname "$0")" && pwd)/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "FATAL: .env file not found at $ENV_FILE"
    echo "Copy .env.example to .env and fill in the values."
    exit 1
fi

# -- Read OAUTH_PROVIDER from .env (default: github) --------------------------
OAUTH_PROVIDER=$(grep '^OAUTH_PROVIDER=' "$ENV_FILE" | tail -1 | cut -d= -f2- | tr -d "'" | tr -d '"')
OAUTH_PROVIDER="${OAUTH_PROVIDER:-github}"
OAUTH_PROVIDER=$(echo "$OAUTH_PROVIDER" | tr '[:upper:]' '[:lower:]')
echo "  OAUTH_PROVIDER: $OAUTH_PROVIDER"

# Providers known to NOT issue refresh tokens
NO_REFRESH_PROVIDERS="github"

# Check for required keys (common + provider-specific)
REQUIRED_KEYS="JWT_SIGNING_KEY STORAGE_ENCRYPTION_KEY"
if [ "$OAUTH_PROVIDER" = "github" ]; then
    REQUIRED_KEYS="$REQUIRED_KEYS GITHUB_CLIENT_ID GITHUB_CLIENT_SECRET"
fi
MISSING_KEYS=()
for key in $REQUIRED_KEYS; do
    if [ -z "${!key:-}" ] && ! grep -q "^${key}=" "$ENV_FILE"; then
        MISSING_KEYS+=("$key")
    fi
done
if [ ${#MISSING_KEYS[@]} -gt 0 ]; then
    echo "FATAL: Missing required .env variables: ${MISSING_KEYS[*]}"
    exit 1
fi
echo "  .env secrets: present -- OK"

# -- Read SERVER_URL from .env ------------------------------------------------
SERVER_URL_FROM_ENV=$(grep '^SERVER_URL=' "$ENV_FILE" | tail -1 | cut -d= -f2- | tr -d "'" | tr -d '"')

if [ -z "$SERVER_URL_FROM_ENV" ] || [[ "$SERVER_URL_FROM_ENV" == http://localhost* ]]; then
    echo "FATAL: SERVER_URL in .env must be set to your tunnel URL (not localhost)."
    echo "See docs/local-development.md for named tunnel setup."
    exit 1
fi
SERVER="$SERVER_URL_FROM_ENV"
echo "  SERVER_URL: $SERVER -- OK"

# -- Check callback port is free ----------------------------------------------
if lsof -iTCP:"$CALLBACK_PORT" -sTCP:LISTEN -t &>/dev/null; then
    echo "FATAL: Port $CALLBACK_PORT is already in use (needed for OAuth callback)."
    echo "Kill the process: lsof -iTCP:$CALLBACK_PORT -sTCP:LISTEN"
    exit 1
fi
echo "  Callback port $CALLBACK_PORT: free -- OK"

# -- Prepare temp dir ---------------------------------------------------------
rm -rf "$TMPDIR_BASE"
mkdir -p "$TMPDIR_BASE"

# =============================================================================
echo ""
echo "=== Setup ==="
echo ""

# -- Step 1: Server -----------------------------------------------------------
echo "  Start the MCP server in another terminal:"
echo "    uv run python -m sketchpad"
echo ""
read -rp "  Press Enter when the server is running..."

while true; do
    if curl -sf --max-time 3 "http://localhost:$SERVER_PORT/.well-known/oauth-authorization-server" >/dev/null 2>&1; then
        echo "  Server on localhost:$SERVER_PORT -- OK"
        break
    fi
    echo "  Server not reachable on localhost:$SERVER_PORT."
    read -rp "  Press Enter to retry, or Ctrl-C to abort..."
done

# -- Step 2: Tunnel -----------------------------------------------------------
echo ""
echo "  Start the tunnel in another terminal:"
echo "    cloudflared tunnel run"
echo ""
read -rp "  Press Enter when the tunnel is running..."

while true; do
    if curl -sf --max-time 5 "$SERVER/.well-known/oauth-authorization-server" >/dev/null 2>&1; then
        echo "  Tunnel at $SERVER -- OK"
        break
    fi
    echo "  Tunnel not reachable at $SERVER."
    read -rp "  Press Enter to retry, or Ctrl-C to abort..."
done

# -- Ready to go --------------------------------------------------------------
echo ""
echo "  Setup complete! Server and tunnel are both reachable."
read -rp "  Press Enter to run the tests..."

# ============================================================================
echo ""
echo "=== Step 1: Discovery ==="
echo "Target server: $SERVER"
echo ""

echo "Fetching /.well-known/oauth-authorization-server ..."
AS_META=$(curl -sf "$SERVER/.well-known/oauth-authorization-server")
echo "$AS_META" | jq .

AUTH_ENDPOINT=$(echo "$AS_META" | jq -r '.authorization_endpoint // empty')
TOKEN_ENDPOINT=$(echo "$AS_META" | jq -r '.token_endpoint // empty')
REG_ENDPOINT=$(echo "$AS_META" | jq -r '.registration_endpoint // empty')

check_not_empty "authorization_endpoint present" "$AUTH_ENDPOINT"
check_not_empty "token_endpoint present" "$TOKEN_ENDPOINT"
check_not_empty "registration_endpoint present" "$REG_ENDPOINT"

echo ""
echo "Fetching /.well-known/oauth-protected-resource/mcp (RFC 9728 path-aware) ..."
if ! PR_META=$(curl -sf "$SERVER/.well-known/oauth-protected-resource/mcp"); then
    echo "  FAIL: /.well-known/oauth-protected-resource/mcp returned non-200"
    echo "        (RFC 9728 Section 3.1: path-aware URL includes the MCP resource path)"
    echo ""
    echo "=== ABORTED: DISC-02 is a required endpoint ==="
    exit 1
fi
echo "$PR_META" | jq .

RESOURCE=$(echo "$PR_META" | jq -r '.resource // empty')
check_not_empty "resource field present" "$RESOURCE"

# ============================================================================
echo ""
echo "=== Step 2: Unauthenticated Request (expect 401) ==="

HTTP_CODE=$(curl -s -o /tmp/mcp-401-body.txt -w "%{http_code}" \
    -X POST "$SERVER/mcp" \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"initialize","id":0}')
echo "POST /mcp without token: HTTP $HTTP_CODE"
check "401 for unauthenticated request" "$HTTP_CODE" "401"

# Show WWW-Authenticate header
echo "Response headers:"
curl -s -D - -o /dev/null -X POST "$SERVER/mcp" \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"initialize","id":0}' 2>&1 \
    | grep -i "www-authenticate" || echo "  (no WWW-Authenticate header found)"

# ============================================================================
echo ""
echo "=== Step 3: Dynamic Client Registration ==="

REDIRECT_URI="http://localhost:${CALLBACK_PORT}/callback"

CLIENT_RESPONSE=$(curl -sf -X POST "$SERVER/register" \
    -H "Content-Type: application/json" \
    -d "{
        \"client_name\": \"test-oauth-script\",
        \"redirect_uris\": [\"${REDIRECT_URI}\"],
        \"grant_types\": [\"authorization_code\", \"refresh_token\"],
        \"response_types\": [\"code\"],
        \"token_endpoint_auth_method\": \"none\"
    }")
echo "$CLIENT_RESPONSE" | jq .

CLIENT_ID=$(echo "$CLIENT_RESPONSE" | jq -r '.client_id // empty')
check_not_empty "client_id returned" "$CLIENT_ID"
echo "Got client_id: $CLIENT_ID"

# ============================================================================
echo ""
echo "=== Step 4: Authorization (browser-based) ==="

# Generate PKCE code_verifier (43-128 chars, URL-safe)
CODE_VERIFIER=$(openssl rand -base64 32 | tr -d '=/+' | head -c 43)

# Generate code_challenge = base64url(SHA256(code_verifier))
CODE_CHALLENGE=$(printf '%s' "$CODE_VERIFIER" \
    | openssl dgst -sha256 -binary \
    | base64 \
    | tr '+/' '-_' \
    | tr -d '=')

STATE=$(openssl rand -hex 16)

AUTH_URL="${SERVER}/authorize?response_type=code&client_id=${CLIENT_ID}&redirect_uri=${REDIRECT_URI}&code_challenge=${CODE_CHALLENGE}&code_challenge_method=S256&state=${STATE}"

# -- Start callback listener --------------------------------------------------
AUTH_CODE_FILE="$TMPDIR_BASE/auth-code.txt"
LISTENER_READY_FILE="$TMPDIR_BASE/listener-ready.txt"

python3 -c "
import http.server, urllib.parse, sys, os

CODE_FILE = sys.argv[1]
READY_FILE = sys.argv[2]
EXPECTED_STATE = sys.argv[3]
PORT = int(sys.argv[4])

SUCCESS_HTML = '''<!DOCTYPE html>
<html>
<head><title>Authorization Successful</title></head>
<body style=\"font-family: system-ui, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #f0fdf4;\">
<div style=\"text-align: center;\">
<h1 style=\"color: #16a34a;\">Authorization Successful</h1>
<p>You can close this tab and return to the terminal.</p>
</div>
</body>
</html>'''

ERROR_HTML = '''<!DOCTYPE html>
<html>
<head><title>Authorization Failed</title></head>
<body style=\"font-family: system-ui, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #fef2f2;\">
<div style=\"text-align: center;\">
<h1 style=\"color: #dc2626;\">Authorization Failed</h1>
<p>%s</p>
</div>
</body>
</html>'''

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path != '/callback':
            self.send_response(404)
            self.end_headers()
            return

        code = params.get('code', [None])[0]
        state = params.get('state', [None])[0]
        error = params.get('error', [None])[0]

        if error:
            msg = f'OAuth error: {error} - {params.get(\"error_description\", [\"\"])[0]}'
            self.send_response(400)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write((ERROR_HTML % msg).encode())
            return

        if state != EXPECTED_STATE:
            msg = f'State mismatch (CSRF protection). Expected {EXPECTED_STATE}, got {state}'
            self.send_response(400)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write((ERROR_HTML % msg).encode())
            return

        if not code:
            msg = 'No authorization code received.'
            self.send_response(400)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write((ERROR_HTML % msg).encode())
            return

        # Write the code to file for the shell script to pick up
        with open(CODE_FILE, 'w') as f:
            f.write(code)

        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(SUCCESS_HTML.encode())

    def log_message(self, format, *args):
        pass  # Suppress request logging

server = http.server.HTTPServer(('127.0.0.1', PORT), Handler)

# Signal that we're ready
with open(READY_FILE, 'w') as f:
    f.write('ready')

# Serve exactly one valid callback request then exit
server.handle_request()
" "$AUTH_CODE_FILE" "$LISTENER_READY_FILE" "$STATE" "$CALLBACK_PORT" &
PIDS+=($!)
echo "  Callback listener PID: ${PIDS[-1]} (port $CALLBACK_PORT)"

# Wait for listener to be ready
ELAPSED=0
while [ $ELAPSED -lt 5 ]; do
    if [ -f "$LISTENER_READY_FILE" ]; then
        break
    fi
    sleep 0.2
    ELAPSED=$((ELAPSED + 1))
done

# -- Open browser -------------------------------------------------------------
echo ""
echo "Opening browser for GitHub authorization..."
echo "  URL: $AUTH_URL"
echo ""
open "$AUTH_URL"

# -- Wait for auth code -------------------------------------------------------
echo "Waiting for authorization (up to ${AUTH_TIMEOUT}s)..."
ELAPSED=0
while [ $ELAPSED -lt $AUTH_TIMEOUT ]; do
    if [ -f "$AUTH_CODE_FILE" ]; then
        break
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

if [ ! -f "$AUTH_CODE_FILE" ]; then
    fail "Authorization timed out after ${AUTH_TIMEOUT}s"
    echo ""
    echo "=== Results: $PASS_COUNT passed, $FAIL_COUNT failed ==="
    exit 1
fi

AUTH_CODE=$(cat "$AUTH_CODE_FILE")
if [ -z "$AUTH_CODE" ]; then
    fail "Authorization code file is empty"
    echo ""
    echo "=== Results: $PASS_COUNT passed, $FAIL_COUNT failed ==="
    exit 1
fi
pass "Authorization code received via callback"

# ============================================================================
echo ""
echo "=== Step 5: Token Exchange ==="

TOKEN_RESPONSE=$(curl -sf -X POST "$SERVER/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=authorization_code&code=${AUTH_CODE}&client_id=${CLIENT_ID}&redirect_uri=${REDIRECT_URI}&code_verifier=${CODE_VERIFIER}")
echo "$TOKEN_RESPONSE" | jq .

ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token // empty')
REFRESH_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.refresh_token // empty')
EXPIRES_IN=$(echo "$TOKEN_RESPONSE" | jq -r '.expires_in // empty')

check_not_empty "access_token received" "$ACCESS_TOKEN"
if [ -n "$REFRESH_TOKEN" ] && [ "$REFRESH_TOKEN" != "null" ]; then
    pass "refresh_token received"
elif echo "$NO_REFRESH_PROVIDERS" | grep -qw "$OAUTH_PROVIDER"; then
    skip "no refresh_token ($OAUTH_PROVIDER doesn't issue them)"
else
    fail "refresh_token missing ($OAUTH_PROVIDER should issue one)"
fi
check_not_empty "expires_in present" "$EXPIRES_IN"

# ============================================================================
echo ""
echo "=== Step 6: Refresh Token ==="

if [ -n "$REFRESH_TOKEN" ] && [ "$REFRESH_TOKEN" != "null" ]; then
    REFRESH_RESPONSE=$(curl -sf -X POST "$SERVER/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "grant_type=refresh_token&refresh_token=${REFRESH_TOKEN}&client_id=${CLIENT_ID}")
    echo "$REFRESH_RESPONSE" | jq .

    NEW_ACCESS_TOKEN=$(echo "$REFRESH_RESPONSE" | jq -r '.access_token // empty')
    check_not_empty "new access_token from refresh" "$NEW_ACCESS_TOKEN"

    # Use the refreshed token for subsequent requests
    ACCESS_TOKEN="$NEW_ACCESS_TOKEN"
else
    skip "token refresh (no refresh_token available from $OAUTH_PROVIDER)"
fi

# ============================================================================
echo ""
echo "=== Step 7: MCP Tool Calls ==="

# Step 7a: Initialize the MCP session
echo "Sending initialize request..."
INIT_RESPONSE=$(curl -sf -D "$TMPDIR_BASE/mcp-init-headers.txt" -X POST "$SERVER/mcp" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {
                "name": "test-oauth-script",
                "version": "1.0.0"
            }
        },
        "id": 1
    }')
echo "$INIT_RESPONSE" | jq .

# Extract session ID if present (Streamable HTTP may use Mcp-Session-Id)
SESSION_ID=$(grep -i "mcp-session-id" "$TMPDIR_BASE/mcp-init-headers.txt" 2>/dev/null \
    | sed 's/.*: //' | tr -d '\r\n' || true)

SESSION_HEADER=""
if [ -n "$SESSION_ID" ]; then
    echo "Got Mcp-Session-Id: $SESSION_ID"
    SESSION_HEADER="-H Mcp-Session-Id:${SESSION_ID}"
fi

INIT_RESULT=$(echo "$INIT_RESPONSE" | jq -r '.result.protocolVersion // empty')
check_not_empty "initialize returned protocolVersion" "$INIT_RESULT"

# Send initialized notification
echo ""
echo "Sending initialized notification..."
# shellcheck disable=SC2086
curl -sf -X POST "$SERVER/mcp" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    $SESSION_HEADER \
    -d '{
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }' || true

# Step 7b: tools/list
echo ""
echo "Calling tools/list..."
# shellcheck disable=SC2086
TOOLS_RESPONSE=$(curl -sf -X POST "$SERVER/mcp" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    $SESSION_HEADER \
    -d '{"jsonrpc":"2.0","method":"tools/list","id":2}')
echo "$TOOLS_RESPONSE" | jq .

TOOL_COUNT=$(echo "$TOOLS_RESPONSE" | jq '.result.tools | length')
check "tools/list returns 2 tools" "$TOOL_COUNT" "2"

# Verify tool names
READ_TOOL=$(echo "$TOOLS_RESPONSE" | jq -r '.result.tools[] | select(.name=="read_file") | .name // empty')
WRITE_TOOL=$(echo "$TOOLS_RESPONSE" | jq -r '.result.tools[] | select(.name=="write_file") | .name // empty')
check_not_empty "read_file tool present" "$READ_TOOL"
check_not_empty "write_file tool present" "$WRITE_TOOL"

# Step 7c: Call read_file (should return welcome message or existing content)
echo ""
echo "Calling read_file..."
# shellcheck disable=SC2086
READ_RESPONSE=$(curl -sf -X POST "$SERVER/mcp" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    $SESSION_HEADER \
    -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"read_file","arguments":{}},"id":3}')
echo "$READ_RESPONSE" | jq .

READ_CONTENT=$(echo "$READ_RESPONSE" | jq -r '.result.content[0].text // empty')
check_not_empty "read_file returned content" "$READ_CONTENT"

# Step 7d: Call write_file
echo ""
echo "Calling write_file..."
# shellcheck disable=SC2086
WRITE_RESPONSE=$(curl -sf -X POST "$SERVER/mcp" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    $SESSION_HEADER \
    -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"write_file","arguments":{"content":"Hello from test-oauth.sh!"}},"id":4}')
echo "$WRITE_RESPONSE" | jq .

WRITE_RESULT=$(echo "$WRITE_RESPONSE" | jq -r '.result.content[0].text // empty')
check_not_empty "write_file returned confirmation" "$WRITE_RESULT"

# Step 7e: Read back the written content
echo ""
echo "Calling read_file again (verify written content)..."
# shellcheck disable=SC2086
READ_BACK=$(curl -sf -X POST "$SERVER/mcp" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    $SESSION_HEADER \
    -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"read_file","arguments":{}},"id":5}')
echo "$READ_BACK" | jq .

READ_BACK_CONTENT=$(echo "$READ_BACK" | jq -r '.result.content[0].text // empty')
check "read_file returns written content" "$READ_BACK_CONTENT" "Hello from test-oauth.sh!"

# ============================================================================
echo ""
echo "=== Results ==="
echo "$PASS_COUNT passed, $FAIL_COUNT failed, $SKIP_COUNT skipped"
echo ""

if [ "$FAIL_COUNT" -gt 0 ]; then
    echo "SOME CHECKS FAILED"
    exit 1
else
    echo "ALL CHECKS PASSED"
    exit 0
fi
