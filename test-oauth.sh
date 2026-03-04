#!/usr/bin/env bash
# =============================================================================
# End-to-end OAuth flow test for the Sketchpad MCP server.
#
# This is the PRIMARY test client per project decision. It exercises the full
# OAuth 2.1 flow: discovery, 401 check, DCR, authorization (manual), token
# exchange, refresh, and MCP tool calls via JSON-RPC over Streamable HTTP.
#
# Usage: ./test-oauth.sh [SERVER_URL]
# Defaults to http://localhost:8000 if not provided.
#
# Requirements: curl, jq, openssl
# =============================================================================

set -euo pipefail

SERVER="${1:-http://localhost:8000}"
PASS_COUNT=0
FAIL_COUNT=0

pass() {
    echo "  PASS: $1"
    PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
    echo "  FAIL: $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
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

# ============================================================================
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
echo "Fetching /.well-known/oauth-protected-resource ..."
PR_META=$(curl -sf "$SERVER/.well-known/oauth-protected-resource")
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

CLIENT_RESPONSE=$(curl -sf -X POST "$SERVER/register" \
    -H "Content-Type: application/json" \
    -d '{
        "client_name": "test-oauth-script",
        "redirect_uris": ["http://localhost:9999/callback"],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none"
    }')
echo "$CLIENT_RESPONSE" | jq .

CLIENT_ID=$(echo "$CLIENT_RESPONSE" | jq -r '.client_id // empty')
check_not_empty "client_id returned" "$CLIENT_ID"
echo "Got client_id: $CLIENT_ID"

# ============================================================================
echo ""
echo "=== Step 4: Authorization (manual -- requires browser) ==="

# Generate PKCE code_verifier (43-128 chars, URL-safe)
CODE_VERIFIER=$(openssl rand -base64 32 | tr -d '=/+' | head -c 43)

# Generate code_challenge = base64url(SHA256(code_verifier))
CODE_CHALLENGE=$(printf '%s' "$CODE_VERIFIER" \
    | openssl dgst -sha256 -binary \
    | base64 \
    | tr '+/' '-_' \
    | tr -d '=')

STATE=$(openssl rand -hex 16)

REDIRECT_URI="http://localhost:9999/callback"
AUTH_URL="${SERVER}/authorize?response_type=code&client_id=${CLIENT_ID}&redirect_uri=${REDIRECT_URI}&code_challenge=${CODE_CHALLENGE}&code_challenge_method=S256&state=${STATE}"

echo "Open this URL in your browser:"
echo ""
echo "  $AUTH_URL"
echo ""
echo "After GitHub login, you'll be redirected to localhost:9999/callback."
echo "The redirect will fail (nothing is listening), but the URL bar will contain"
echo "the authorization code. Copy the 'code' parameter value and paste it here."
echo ""
echo -n "Authorization code: "
read -r AUTH_CODE

if [ -z "$AUTH_CODE" ]; then
    fail "No authorization code provided"
    echo ""
    echo "=== Results: $PASS_COUNT passed, $FAIL_COUNT failed ==="
    exit 1
fi
pass "Authorization code received"

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
check_not_empty "refresh_token received" "$REFRESH_TOKEN"
check_not_empty "expires_in present" "$EXPIRES_IN"

# ============================================================================
echo ""
echo "=== Step 6: Refresh Token ==="

REFRESH_RESPONSE=$(curl -sf -X POST "$SERVER/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=refresh_token&refresh_token=${REFRESH_TOKEN}&client_id=${CLIENT_ID}")
echo "$REFRESH_RESPONSE" | jq .

NEW_ACCESS_TOKEN=$(echo "$REFRESH_RESPONSE" | jq -r '.access_token // empty')
check_not_empty "new access_token from refresh" "$NEW_ACCESS_TOKEN"

# Use the refreshed token for subsequent requests
ACCESS_TOKEN="$NEW_ACCESS_TOKEN"

# ============================================================================
echo ""
echo "=== Step 7: MCP Tool Calls ==="

# Step 7a: Initialize the MCP session
echo "Sending initialize request..."
INIT_RESPONSE=$(curl -sf -D /tmp/mcp-init-headers.txt -X POST "$SERVER/mcp" \
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
SESSION_ID=$(grep -i "mcp-session-id" /tmp/mcp-init-headers.txt 2>/dev/null \
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
echo "$PASS_COUNT passed, $FAIL_COUNT failed"
echo ""

if [ "$FAIL_COUNT" -gt 0 ]; then
    echo "SOME CHECKS FAILED"
    exit 1
else
    echo "ALL CHECKS PASSED"
    exit 0
fi
