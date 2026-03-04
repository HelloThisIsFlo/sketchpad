---
phase: 02-mcp-server-oauth
verified: 2026-03-04T03:00:00Z
status: gaps_found
score: 3/5 success criteria verified
re_verification: false
gaps:
  - truth: "GET /.well-known/oauth-protected-resource returns JSON with resource and authorization_servers"
    status: failed
    reason: "Endpoint returns 404 at runtime with FastMCP 3.1.0 + GitHubProvider. Confirmed in 02-03-SUMMARY.md as known issue. OAuthProvider.get_routes() only registers the endpoint when _resource_url is non-None, which requires configure_with_mcp_path() to have been called with a non-None path. Whether this is called correctly at runtime is unconfirmed."
    artifacts:
      - path: "src/sketchpad/server.py"
        issue: "No application-level workaround for the missing /.well-known/oauth-protected-resource endpoint"
    missing:
      - "Investigate whether FastMCP calls configure_with_mcp_path('/mcp') correctly when mcp.run(transport='http') is invoked, or add a manual route registration for the protected resource metadata endpoint"
  - truth: "Full OAuth flow completes: authorize -> GitHub login -> callback -> token"
    status: failed
    reason: "Steps 4-7 of test-oauth.sh (authorization URL, GitHub login, token exchange, refresh, MCP tool calls) were NOT executed. 02-03-SUMMARY.md explicitly states 'Full OAuth browser flow (Steps 4-7 of test-oauth.sh) requires manual GitHub login -- deferred to user's discretion.' AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07 are unverified at runtime."
    artifacts: []
    missing:
      - "User must execute test-oauth.sh Steps 4-7 against a running server with a real GitHub OAuth App to confirm AUTH-02 through AUTH-07"
  - truth: "MCP tool calls work with a valid token: tools/list returns read_file and write_file, write_file writes, read_file confirms write"
    status: failed
    reason: "Steps 7a-7e of test-oauth.sh (initialize, tools/list, read_file, write_file, read_file again) were NOT executed because they require a valid Bearer token from Step 5. Since Steps 4-7 were deferred, MCP-01 through MCP-05 and TOOL-01 through TOOL-02 are unverified at runtime. The code is structurally correct and the tools are wired, but runtime validation did not happen."
    artifacts: []
    missing:
      - "User must execute test-oauth.sh Steps 7a-7e after completing the OAuth flow to confirm MCP protocol and tool behavior at runtime"
human_verification:
  - test: "Run test-oauth.sh against a live server (Steps 4-7)"
    expected: "Steps 4-7 all show PASS: GitHub OAuth redirect works, token exchange returns access_token and refresh_token, tools/list returns read_file and write_file, write_file writes content, read_file confirms written content"
    why_human: "Requires browser interaction with GitHub OAuth login page, which cannot be automated"
  - test: "Confirm /.well-known/oauth-protected-resource endpoint status"
    expected: "curl http://localhost:8000/.well-known/oauth-protected-resource returns 200 with JSON containing resource and authorization_servers fields"
    why_human: "Runtime endpoint registration depends on FastMCP internals (configure_with_mcp_path call chain); code inspection alone is insufficient to confirm 200 vs 404"
---

# Phase 2: MCP Server + OAuth Verification Report

**Phase Goal:** A locally running FastMCP server correctly implements the full OAuth 2.1 protocol and file tools — every endpoint responds correctly when hit with curl or MCP Inspector before any Kubernetes complexity is involved
**Verified:** 2026-03-04T03:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /.well-known/oauth-authorization-server returns JSON with authorization_endpoint, token_endpoint, registration_endpoint | VERIFIED | 02-03-SUMMARY: "discovery endpoints return valid JSON"; curl run manually in Plan 03 Task 1 |
| 2 | GET /.well-known/oauth-protected-resource returns JSON with resource and authorization_servers | FAILED | 02-03-SUMMARY explicitly: "returns 404 in FastMCP 3.1.0 -- this endpoint is not registered by GitHubProvider" |
| 3 | POST /mcp without a token returns HTTP 401 with WWW-Authenticate header | VERIFIED | 02-03-SUMMARY: "POST /mcp without token returns 401 (unauthenticated check confirmed)"; test-oauth.sh Step 2 confirmed |
| 4 | POST /register with valid client metadata returns a client_id | VERIFIED | 02-03-SUMMARY: "DCR registration returns client_id via cloudflared tunnel"; test-oauth.sh Step 3 confirmed |
| 5 | Full OAuth flow completes: authorize -> GitHub login -> callback -> token exchange -> refresh | FAILED | 02-03-SUMMARY: "Full OAuth browser flow (Steps 4-7 of test-oauth.sh) requires manual GitHub login -- deferred to user's discretion" |
| 6 | MCP tool calls work with a valid token: tools/list, read_file, write_file round-trip | FAILED | Not executed — depends on completing OAuth flow (Step 5), which was deferred |
| 7 | Docker image builds successfully | VERIFIED (claimed) | 02-03-SUMMARY: "Docker image builds successfully (sketchpad-test:latest)" — verified by the execution agent; commit c00f735 exists |
| 8 | Server starts without errors when all env vars are set | VERIFIED | 02-03-SUMMARY: "Server starts locally with .env loading and all discovery endpoints return valid JSON" |

**Score:** 3/5 success criteria from ROADMAP.md verified (see below)

### ROADMAP Success Criteria Cross-Check

| # | Success Criterion | Status | Notes |
|---|-------------------|--------|-------|
| 1 | `curl /.well-known/oauth-authorization-server` returns JSON with authorization_endpoint, token_endpoint, registration_endpoint | VERIFIED | Confirmed at runtime via cloudflared tunnel |
| 2 | `curl /.well-known/oauth-protected-resource` returns JSON referencing the authorization server | FAILED | Returns 404 — known issue in 02-03-SUMMARY |
| 3 | POST /mcp without token returns HTTP 401 with WWW-Authenticate: Bearer resource_metadata= header | VERIFIED | Confirmed at runtime |
| 4 | POST /register returns a client_id | VERIFIED | Confirmed at runtime |
| 5 | tools/list returns read_file and write_file; calling each returns expected results | FAILED | Not executed — OAuth flow steps 4-7 were deferred |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sketchpad/config.py` | Lazy get_config() with @lru_cache | VERIFIED | 21 lines, implements pattern exactly as designed; `uv run python -c "from sketchpad.config import get_config"` succeeds |
| `src/sketchpad/server.py` | create_app() factory with GitHubProvider + FileTreeStore | VERIFIED | 61 lines, full implementation; imports succeed without env vars |
| `src/sketchpad/tools.py` | read_file and write_file via @mcp.tool | VERIFIED | 51 lines, both tools implemented with all specified behaviors (welcome message, size warning, append mode) |
| `src/sketchpad/__main__.py` | Entry point calling create_app() | VERIFIED | 11 lines; loads .env via dotenv then calls create_app() |
| `src/sketchpad/__init__.py` | Empty package init | VERIFIED | Exists |
| `pyproject.toml` | uv project with fastmcp dependency | VERIFIED | Contains fastmcp>=3.0.2 and hatchling build-system |
| `.env.example` | Template with GITHUB_CLIENT_ID and all vars | VERIFIED | Documents all 8 env vars with generation instructions |
| `Dockerfile` | Multi-stage uv build, CMD runs python -m sketchpad | VERIFIED | Two-stage build with uv sync; CMD ["python", "-m", "sketchpad"] |
| `test-oauth.sh` | Executable, 7-step OAuth flow test | VERIFIED | Executable; covers Steps 1-7 including all assertions |
| `docs/mcp-inspector.md` | MCP Inspector guided exploration | VERIFIED | 82 lines; covers 7 "fun things to try" |
| `uv.lock` | Locked dependency tree | VERIFIED | 1130 lines; fastmcp 3.1.0 resolved |
| `requirements.txt` | Should NOT exist (deleted) | VERIFIED ABSENT | Confirmed absent |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/sketchpad/server.py` | `src/sketchpad/config.py` | `from sketchpad.config import get_config` | WIRED | Line 13 of server.py; called inside create_app() at line 23 |
| `src/sketchpad/server.py` | `src/sketchpad/tools.py` | `register_tools(mcp)` | WIRED | Line 14 import, line 53 call |
| `src/sketchpad/tools.py` | `src/sketchpad/config.py` | `from sketchpad.config import get_config` | WIRED | Line 3; called inside each tool function |
| `src/sketchpad/__main__.py` | `src/sketchpad/server.py` | `from sketchpad.server import create_app` | WIRED | Line 8; app = create_app() at line 10 |
| `Dockerfile` | `pyproject.toml` / `uv.lock` | `uv sync --locked` | WIRED | Lines 27 and 32; bind-mount pattern for layer caching |
| `Dockerfile` | `src/sketchpad/__main__.py` | `CMD ["python", "-m", "sketchpad"]` | WIRED | Line 49 |
| `test-oauth.sh` | `http://localhost:8000` | curl calls to server endpoints | WIRED | Line 17 `SERVER="${1:-http://localhost:8000}"`, line 55 curl to oauth-authorization-server |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DISC-01 | 02-01-PLAN.md | /.well-known/oauth-authorization-server returns JSON | SATISFIED | Verified at runtime in 02-03 |
| DISC-02 | 02-01-PLAN.md | /.well-known/oauth-protected-resource returns JSON | BLOCKED | Returns 404 at runtime — 02-03-SUMMARY known issue |
| DISC-03 | 02-01-PLAN.md | POST /mcp without token returns 401 with WWW-Authenticate | SATISFIED | Verified at runtime in 02-03 |
| AUTH-01 | 02-01-PLAN.md | POST /register returns client_id (DCR) | SATISFIED | Verified at runtime in 02-03 |
| AUTH-02 | 02-01-PLAN.md | /authorize redirects to GitHub OAuth | NEEDS HUMAN | Browser-only; deferred in 02-03 |
| AUTH-03 | 02-01-PLAN.md | GitHub callback exchanges code, redirects with auth code | NEEDS HUMAN | Browser-only; deferred in 02-03 |
| AUTH-04 | 02-01-PLAN.md | /token with PKCE verification returns access_token | NEEDS HUMAN | Not executed; depends on AUTH-02/AUTH-03 |
| AUTH-05 | 02-01-PLAN.md | /token response includes refresh_token | NEEDS HUMAN | Not executed |
| AUTH-06 | 02-01-PLAN.md | /token with grant_type=refresh_token issues new tokens | NEEDS HUMAN | Not executed |
| AUTH-07 | 02-01-PLAN.md | access tokens have expires_in field (expiration configured) | NEEDS HUMAN | Not executed |
| MCP-01 | 02-01-PLAN.md | POST /mcp accepts Streamable HTTP requests | NEEDS HUMAN | Structurally correct; runtime tool call not executed |
| MCP-02 | 02-01-PLAN.md | initialize response includes tools capability | NEEDS HUMAN | Not executed |
| MCP-03 | 02-01-PLAN.md | tools/list returns read_file and write_file definitions | NEEDS HUMAN | Not executed |
| MCP-04 | 02-01-PLAN.md | tools/call dispatches to correct handler | NEEDS HUMAN | Not executed |
| MCP-05 | 02-01-PLAN.md | Bearer token validated on every MCP request; 401 for missing | SATISFIED | 401 path verified at runtime (Step 2); valid-token path not executed |
| TOOL-01 | 02-01-PLAN.md | read_file returns sketchpad contents or welcome message | NEEDS HUMAN | Not executed at runtime |
| TOOL-02 | 02-01-PLAN.md | write_file replaces sketchpad file contents | NEEDS HUMAN | Not executed at runtime |

**Note on DISC-02 vs. ROADMAP.md traceability:** REQUIREMENTS.md marks DISC-02 as [x] Complete (Phase 2, Complete). This contradicts the 02-03-SUMMARY.md runtime finding. The traceability table was updated by the execution agent, but the SUMMARY's own "Issues Encountered" section contradicts that status.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | - | No TODO/FIXME/placeholder comments in src/ | - | Clean |
| None found | - | No return null / Not implemented patterns in src/ | - | Clean |

No anti-patterns detected. All source files contain substantive implementations.

### Human Verification Required

#### 1. Complete OAuth Browser Flow (test-oauth.sh Steps 4-7)

**Test:** With the server running locally (`.env` populated with real GitHub OAuth credentials), start a cloudflared tunnel and run:
```bash
./test-oauth.sh https://<tunnel-url>
```
At Step 4, open the printed URL in a browser and complete GitHub login. Copy the authorization code from the redirect URL and paste it into the terminal. Let the script continue through Steps 5-7.

**Expected:**
- Step 4: GitHub OAuth login page appears; after login you are redirected to localhost:9999/callback with a `code` param in the URL
- Step 5: Token exchange PASS — access_token, refresh_token, and expires_in all present
- Step 6: Refresh token PASS — new access_token returned
- Step 7: initialize PASS, tools/list shows 2 tools (read_file, write_file), read_file PASS, write_file PASS, read_file confirms written content PASS

**Why human:** GitHub OAuth login requires browser interaction. Cannot be automated without a GitHub bot account.

#### 2. Confirm /.well-known/oauth-protected-resource Status

**Test:** With the server running locally, run:
```bash
curl -v http://localhost:8000/.well-known/oauth-protected-resource
```

**Expected:** HTTP 200 with JSON body containing `resource` and `authorization_servers` fields (satisfying DISC-02 / RFC 9728)

**Why human:** The 02-03-SUMMARY documents this as returning 404 at runtime. The code path in FastMCP that registers this route (`OAuthProvider.get_routes()` adding `create_protected_resource_routes` when `_resource_url` is non-None) should work if `configure_with_mcp_path()` is called with `/mcp` during server startup. This requires a live server to confirm whether the issue persists or was resolved in the installed version (fastmcp 3.1.0).

### Gaps Summary

Three truths are unverified, all rooted in two distinct issues:

**Gap 1 — DISC-02 protected resource endpoint (1 requirement: DISC-02)**

The `/.well-known/oauth-protected-resource` endpoint returned 404 during the one runtime test performed in Plan 03. This is documented as a known issue in the SUMMARY. The code in FastMCP's `OAuthProvider.get_routes()` does register the endpoint, but only when `_resource_url` is set, which depends on `configure_with_mcp_path()` being called with a non-None MCP path. This needs human confirmation against the running server.

**Gap 2 — OAuth browser flow and MCP tool calls not executed (11 requirements: AUTH-02 through AUTH-07, MCP-01 through MCP-05, TOOL-01, TOOL-02)**

The end-to-end OAuth browser flow (test-oauth.sh Steps 4-7) was explicitly deferred in Plan 03 to "user's discretion." These steps cover: GitHub redirect (AUTH-02), callback handling (AUTH-03), PKCE token exchange (AUTH-04), refresh token issuance (AUTH-05), refresh token grant (AUTH-06), token expiry (AUTH-07), MCP initialize/tools-list/tools-call under authentication (MCP-01 through MCP-05), and read_file/write_file at runtime (TOOL-01, TOOL-02).

The code for all of these is structurally correct and fully wired (verified at levels 1, 2, and 3). FastMCP's GitHubProvider is the primary implementor of AUTH-02/AUTH-03 and GitHubTokenVerifier handles AUTH-04 through AUTH-07. The gap is runtime validation, not implementation.

**Root cause grouping:** Both gaps require a running server with real GitHub credentials. They can be closed together by executing `./test-oauth.sh` against a live server and completing the GitHub OAuth browser flow.

---

_Verified: 2026-03-04T03:00:00Z_
_Verifier: Claude (gsd-verifier)_
