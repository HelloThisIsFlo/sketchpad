# Phase 4: Hardening - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Origin validation middleware on the MCP endpoint and verification that token-based auth (from FastMCP/Phase 2) correctly rejects unauthenticated requests. The running server at `thehome-sketchpad.kempenich.dev` rejects malformed or potentially malicious requests while legitimate Claude AI traffic continues working.

</domain>

<decisions>
## Implementation Decisions

### Origin Allowlist Policy
- Allow requests with no Origin header — non-browser clients (curl, test-oauth.sh, Claude Code CLI) don't send it
- Reject requests with a mismatched Origin header (403 Forbidden)
- Implemented as Starlette middleware (not per-endpoint checks) — single enforcement point, can't accidentally miss a route

### Origin Allowlist Configuration
- Claude's Discretion — research what Origin Claude AI actually sends, configure accordingly
- Use configurable approach (env var or server config) so allowed origins can be adjusted without code changes

### Hardening Scope
- Origin validation applies to `/mcp` endpoint only
- Discovery endpoints (`/.well-known/*`) stay open — required by RFC 8414, clients need them to start OAuth
- `/register` (DCR) stays open — pre-auth by definition, new clients register before they have credentials
- `/authorize` and `/token` — Claude's discretion on whether to gate these (balance security vs OAuth flow breakage risk)
- SEC-02 (authenticated-only tool access) — verify FastMCP's built-in token validation works, do NOT add redundant middleware

### Error Response Behavior
- Descriptive error responses — include reason in body, e.g., `{"error": "origin_not_allowed", "detail": "Origin 'evil.com' is not in the allowlist"}`
- This is a personal learning project — debuggability over minimal info leakage
- Log every rejection with timestamp, Origin/IP, and reason (visible via `kubectl logs`)
- No CORS headers — Claude AI is not a browser, CORS adds unnecessary complexity
- 401 responses: Claude's discretion on WWW-Authenticate header conformance with MCP spec (already required by DISC-03 from Phase 2)

### Verification Approach
- All security tests hit the public URL (`https://thehome-sketchpad.kempenich.dev`), not localhost — tests the real path including Cloudflare Tunnel
- Test cases: bad Origin (expect 403), no Origin (expect pass), no token (expect 401), valid request (expect success)
- Full E2E retest after hardening: re-run Claude Code test skill AND phone test to prove hardening didn't break the happy path
- Test script organization and test skill updates: Claude's discretion

### Claude's Discretion
- Exact Origin allowlist values (research what Claude AI sends)
- Whether to gate `/authorize` and `/token` with Origin checks
- Test script organization (extend test-oauth.sh vs separate test-security.sh)
- Whether to add a security check step to the Claude Code test skill
- Middleware implementation details (Starlette middleware hook, error response format)
- WWW-Authenticate header details on 401 responses

</decisions>

<specifics>
## Specific Ideas

- "This project is for learning" — user explicitly wants the standard/recommended approach for all Origin validation details rather than making specific technical calls
- Strong preference for recommended options across the board — user trusts Claude's judgment on security implementation specifics
- Descriptive errors chosen specifically to aid learning and debugging, not for production minimalism

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — no code exists yet (Phases 1-3 not executed)

### Established Patterns
- From Phase 2 context: FastMCP with GitHubProvider handles token validation (MCP-05), FileTreeStore + FernetEncryptionWrapper for OAuth state
- From Phase 2 context: test-oauth.sh exercises full OAuth flow — security tests should extend or complement it
- From Phase 3 context: Layer-by-layer verification pattern, Claude Code test skill (`/test-sketchpad`) for interactive testing
- From Phase 3 context: "Try first, patch if broken" for FastMCP issues; escalate rather than maintain patches

### Integration Points
- FastMCP likely supports Starlette middleware for request interception — research needed
- Origin middleware must not interfere with FastMCP's own request handling (OAuth endpoints, SSE, etc.)
- Phase 3's test-oauth.sh accepts server URL parameter — security tests should follow the same pattern
- Public hostname: `thehome-sketchpad.kempenich.dev` (configured in Phase 1)

### Known Issues to Consider
- Cloudflare Tunnel may strip, modify, or add headers — verify Origin header passes through unchanged
- FastMCP's built-in token validation needs verification (SEC-02) — if it has gaps, Phase 4 addresses them

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-hardening*
*Context gathered: 2026-03-03*
