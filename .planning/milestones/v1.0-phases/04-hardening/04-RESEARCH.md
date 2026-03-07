# Phase 4: Hardening - Research

**Researched:** 2026-03-05
**Domain:** HTTP security middleware (Origin validation, token authentication verification)
**Confidence:** HIGH

## Summary

Phase 4 addresses two security requirements: Origin header validation (SEC-01) and verified token-gated tool access (SEC-02). The research reveals that the correct implementation approach is **Starlette ASGI middleware** for Origin validation, passed through FastMCP's existing `mcp.run(transport="http", middleware=[...])` pipeline. SEC-02 (token validation) is already implemented by FastMCP's built-in `RequireAuthMiddleware` which wraps the `/mcp` endpoint -- the phase task is to **verify** it works correctly, not to build it.

The MCP specification (2025-06-18 revision) explicitly requires: "Servers MUST validate the Origin header on all incoming connections to prevent DNS rebinding attacks." The Python SDK (v1.26.0, bundled with FastMCP 3.1.0) includes `TransportSecuritySettings` for this purpose, but FastMCP's `create_streamable_http_app()` does NOT pass these settings through to the underlying transport. This means Origin validation must be implemented as custom Starlette middleware. This is actually preferable because it gives full control over the response format (descriptive JSON errors as decided in CONTEXT.md).

**Primary recommendation:** Implement Origin validation as a Starlette `BaseHTTPMiddleware` subclass, inject it via `mcp.run(transport="http", middleware=[...])`, and verify SEC-02 through curl tests against the live deployment.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Allow requests with no Origin header -- non-browser clients (curl, test-oauth.sh, Claude Code CLI) don't send it
- Reject requests with a mismatched Origin header (403 Forbidden)
- Implemented as Starlette middleware (not per-endpoint checks) -- single enforcement point, can't accidentally miss a route
- Origin validation applies to `/mcp` endpoint only
- Discovery endpoints (`/.well-known/*`) stay open -- required by RFC 8414, clients need them to start OAuth
- `/register` (DCR) stays open -- pre-auth by definition, new clients register before they have credentials
- SEC-02 (authenticated-only tool access) -- verify FastMCP's built-in token validation works, do NOT add redundant middleware
- Descriptive error responses -- include reason in body, e.g., `{"error": "origin_not_allowed", "detail": "Origin 'evil.com' is not in the allowlist"}`
- This is a personal learning project -- debuggability over minimal info leakage
- Log every rejection with timestamp, Origin/IP, and reason (visible via `kubectl logs`)
- No CORS headers -- Claude AI is not a browser, CORS adds unnecessary complexity
- All security tests hit the public URL (`https://sketchpad.kempenich.ai`), not localhost -- tests the real path including Cloudflare Tunnel
- Test cases: bad Origin (expect 403), no Origin (expect pass), no token (expect 401), valid request (expect success)
- Full E2E retest after hardening: re-run Claude Code test skill AND phone test to prove hardening didn't break the happy path

### Claude's Discretion
- Exact Origin allowlist values (research what Claude AI sends)
- Whether to gate `/authorize` and `/token` with Origin checks
- Test script organization (extend test-oauth.sh vs separate test-security.sh)
- Whether to add a security check step to the Claude Code test skill
- Middleware implementation details (Starlette middleware hook, error response format)
- WWW-Authenticate header details on 401 responses

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SEC-01 | Server validates Origin header on incoming requests (DNS rebinding protection) | Starlette `BaseHTTPMiddleware` injected via `mcp.run(middleware=[...])`. Origin allowlist configurable via `ALLOWED_ORIGINS` env var. Absent Origin allowed; mismatched Origin returns 403. Applies to `/mcp` only. |
| SEC-02 | Only authenticated requests can access MCP tools (no anonymous tool calls) | Already implemented by FastMCP's `RequireAuthMiddleware` which wraps the `/mcp` route when `auth=` is provided. Returns 401 with `WWW-Authenticate: Bearer` header. Phase 4 task is verification only. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastMCP | 3.1.0 | MCP server framework (already installed) | Powers the entire server; middleware injection via `mcp.run()` kwargs |
| Starlette | (bundled) | ASGI framework underneath FastMCP | `BaseHTTPMiddleware` is the standard pattern for HTTP-level request interception |
| MCP Python SDK | 1.26.0 | Underlying MCP protocol implementation | Includes `TransportSecuritySettings` reference implementation (not used directly, but informs our middleware design) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | (already installed) | HTTP client for security tests | Used by test_oauth.py, extend for security tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom Starlette middleware | MCP SDK `TransportSecuritySettings` | SDK version not passed through by FastMCP 3.1.0's `create_streamable_http_app()` -- would require patching FastMCP internals |
| Custom Starlette middleware | FastMCP native middleware (`add_middleware`) | Native middleware operates at MCP protocol level (after HTTP parsing), not at HTTP level -- Origin validation must happen before any route processing |
| Starlette `BaseHTTPMiddleware` | Pure ASGI middleware | BaseHTTPMiddleware is simpler to write and debug; pure ASGI is only needed for streaming edge cases we don't have |

**No new dependencies needed.** All required libraries are already installed.

## Architecture Patterns

### Recommended Project Structure
```
src/sketchpad/
    __init__.py
    __main__.py           # Entry point -- passes middleware to mcp.run()
    config.py             # Add ALLOWED_ORIGINS config
    server.py             # create_app() returns FastMCP instance
    middleware.py          # NEW: OriginValidationMiddleware
    tools.py              # Unchanged
```

### Pattern 1: Origin Validation Middleware (Starlette BaseHTTPMiddleware)
**What:** A Starlette middleware that checks the Origin header on requests to `/mcp` and returns 403 for mismatched origins, passes through requests with no Origin header.
**When to use:** SEC-01 -- Origin validation on all MCP endpoint requests.

```python
# Source: Starlette docs + MCP spec transport security requirements
import json
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

class OriginValidationMiddleware(BaseHTTPMiddleware):
    """Validate Origin header on /mcp requests per MCP spec.

    - No Origin header: ALLOW (non-browser clients like curl, CLI)
    - Origin in allowlist: ALLOW
    - Origin not in allowlist: REJECT with 403
    """

    def __init__(self, app, allowed_origins: list[str], protected_paths: list[str] | None = None):
        super().__init__(app)
        self.allowed_origins = set(allowed_origins)
        self.protected_paths = set(protected_paths or ["/mcp"])

    async def dispatch(self, request: Request, call_next):
        # Only validate Origin on protected paths
        if request.url.path not in self.protected_paths:
            return await call_next(request)

        origin = request.headers.get("origin")

        # No Origin header = non-browser client, allow
        if origin is None:
            return await call_next(request)

        # Check allowlist
        if origin in self.allowed_origins:
            return await call_next(request)

        # Reject with descriptive error
        client_ip = request.client.host if request.client else "unknown"
        logger.warning(
            "Origin rejected: origin=%s ip=%s path=%s",
            origin, client_ip, request.url.path,
        )
        return JSONResponse(
            status_code=403,
            content={
                "error": "origin_not_allowed",
                "detail": f"Origin '{origin}' is not in the allowlist",
            },
        )
```

### Pattern 2: Middleware Injection via mcp.run()
**What:** Pass Starlette middleware to FastMCP through the `mcp.run()` kwargs, which forwards to `http_app()`.
**When to use:** To add middleware without changing the server startup pattern.

```python
# Source: FastMCP source code analysis (server/mixins/transport.py)
from starlette.middleware import Middleware

# In __main__.py:
app = create_app()
middleware = [
    Middleware(
        OriginValidationMiddleware,
        allowed_origins=get_config()["ALLOWED_ORIGINS"],
    ),
]
app.run(transport="http", host="0.0.0.0", port=8000, middleware=middleware)
```

**Key insight from source code analysis:** `mcp.run(transport="http", **kwargs)` passes kwargs through to `run_http_async()`, which passes `middleware` to `http_app()`, which passes it to `create_streamable_http_app()`, which passes it to `create_base_app()`. The middleware is injected into the Starlette app at construction time. This is verified from reading the FastMCP 3.1.0 source code.

### Pattern 3: Configurable Origin Allowlist
**What:** Store allowed origins in environment variable for deployment flexibility.
**When to use:** Always -- allows changing origins without code changes.

```python
# In config.py:
"ALLOWED_ORIGINS": [
    o.strip() for o in
    os.environ.get("ALLOWED_ORIGINS", "https://claude.ai,https://www.claude.ai").split(",")
    if o.strip()
],
```

### Anti-Patterns to Avoid
- **Adding redundant token validation middleware:** FastMCP already wraps `/mcp` with `RequireAuthMiddleware`. Adding another layer would duplicate logic and risk conflicting error responses.
- **Using CORS middleware:** The user explicitly decided no CORS headers. Claude AI is not a browser. CORSMiddleware would add `Access-Control-*` headers that serve no purpose and might confuse debugging.
- **Checking Origin on all endpoints:** Discovery endpoints (`/.well-known/*`) and `/register` must stay open per RFC 8414 and DCR requirements. Only `/mcp` needs Origin checks.
- **Blocking requests with no Origin:** Non-browser clients (curl, Claude Code CLI, test scripts) do not send Origin headers. Blocking them would break legitimate usage.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token validation on /mcp | Custom auth middleware | FastMCP's built-in `RequireAuthMiddleware` | Already wraps `/mcp` when `auth=` is provided; returns 401 with proper `WWW-Authenticate` header including `resource_metadata` URL |
| JWT verification | Custom JWT decode/verify | FastMCP GitHubProvider's internal JWT validation | Handles signing key, expiry, claims automatically |
| CORS headers | Custom CORS middleware | Nothing (don't add CORS) | Claude AI is not a browser; no CORS needed |
| DNS rebinding host validation | Custom Host header check | Not needed for remote deployment | DNS rebinding is a localhost attack vector; this server runs behind Cloudflare Tunnel with a fixed public hostname |

**Key insight:** This phase is primarily about adding ONE new middleware (Origin validation) and VERIFYING one existing feature (token validation). The temptation to over-engineer should be resisted.

## Common Pitfalls

### Pitfall 1: Cloudflare Tunnel Header Stripping
**What goes wrong:** Cloudflare Tunnel might strip or modify the Origin header before it reaches the server, causing validation to fail on legitimate requests or pass on illegitimate ones.
**Why it happens:** Cloudflare proxies add/modify various headers (CF-Connecting-IP, X-Forwarded-For, etc.) but behavior with Origin is not well-documented.
**How to avoid:** Test Origin validation through the tunnel first (not just localhost). If Origin is stripped by Cloudflare, the "no Origin = allow" policy handles it gracefully. Log all Origin values to understand what actually arrives.
**Warning signs:** Requests that should have an Origin header arrive without one; requests show unexpected Origin values.

### Pitfall 2: Middleware Ordering with Auth
**What goes wrong:** Origin middleware runs AFTER auth middleware, meaning unauthenticated requests with bad Origin get a 401 (auth error) instead of 403 (origin error).
**Why it happens:** Starlette processes middleware in reverse order of the list (first in list = outermost wrapper). If Origin middleware is added after auth middleware, auth runs first.
**How to avoid:** Place Origin middleware FIRST in the middleware list so it wraps the outermost layer and runs before auth. In `create_streamable_http_app`, user middleware is appended AFTER auth middleware. This means user middleware actually runs INSIDE auth middleware. However, since auth is applied per-route (via `RequireAuthMiddleware` wrapping the endpoint, not as Starlette-level middleware), our Starlette-level Origin middleware will run BEFORE the route-level auth check. This is the correct ordering.
**Warning signs:** Bad-Origin requests return 401 instead of 403.

### Pitfall 3: Breaking Health Endpoint
**What goes wrong:** Origin validation middleware accidentally blocks the `/health` endpoint, causing K8s liveness/readiness probes to fail and pods to restart.
**Why it happens:** Middleware applied too broadly, checking Origin on all paths instead of just `/mcp`.
**How to avoid:** The middleware explicitly checks `request.url.path` and only validates Origin for paths in `protected_paths` (default: `["/mcp"]`). The `/health` endpoint is a custom route and not in the protected list.
**Warning signs:** Pod restart loop after deployment; `kubectl logs` shows 403 responses to health checks.

### Pitfall 4: Forgetting to Add Origin Config to K8s
**What goes wrong:** Server deployed with `ALLOWED_ORIGINS` env var missing from the K8s deployment manifest, causing it to fall back to default or crash.
**Why it happens:** Config added to `.env` for local dev but not to `k8s/deployment.yaml`.
**How to avoid:** Add `ALLOWED_ORIGINS` to the deployment manifest's `env` section. Since this is not a secret, it can be an inline value (not a Secret reference).
**Warning signs:** Server starts but rejects all requests with Origin headers, or server fails to start if the config is required.

### Pitfall 5: Claude AI Origin Unknown
**What goes wrong:** We configure the allowlist with wrong Origin values for Claude AI, and legitimate Claude AI requests get rejected.
**Why it happens:** Claude AI's actual Origin header is not well-documented. It may be `https://claude.ai`, `https://www.claude.ai`, or something else entirely. Mobile app clients may not send Origin at all.
**How to avoid:** Deploy with a broad initial allowlist (`https://claude.ai,https://www.claude.ai`), log all incoming Origin values, then narrow the list based on observed traffic. The "no Origin = allow" policy protects against mobile/CLI clients that don't send Origin. If Claude AI doesn't send Origin (likely for server-to-server calls), the middleware passes through automatically.
**Warning signs:** Claude AI requests start failing after hardening; logs show unexpected Origin values.

## Code Examples

### Complete Middleware Implementation
```python
# src/sketchpad/middleware.py
# Source: Starlette BaseHTTPMiddleware docs + MCP spec security requirements
import json
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

class OriginValidationMiddleware(BaseHTTPMiddleware):
    """Validate Origin header on protected paths per MCP spec.

    Policy:
    - No Origin header: ALLOW (non-browser clients)
    - Origin in allowlist: ALLOW
    - Origin not in allowlist: REJECT 403
    """

    def __init__(self, app, allowed_origins: list[str], protected_paths: list[str] | None = None):
        super().__init__(app)
        self.allowed_origins = set(allowed_origins)
        self.protected_paths = set(protected_paths or ["/mcp"])

    async def dispatch(self, request: Request, call_next):
        if request.url.path not in self.protected_paths:
            return await call_next(request)

        origin = request.headers.get("origin")

        if origin is None:
            return await call_next(request)

        if origin in self.allowed_origins:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        logger.warning(
            "Origin rejected: origin=%s ip=%s path=%s",
            origin, client_ip, request.url.path,
        )
        return JSONResponse(
            status_code=403,
            content={
                "error": "origin_not_allowed",
                "detail": f"Origin '{origin}' is not in the allowlist",
            },
        )
```

### Updated __main__.py Entry Point
```python
# src/sketchpad/__main__.py
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from starlette.middleware import Middleware
from sketchpad.server import create_app
from sketchpad.config import get_config
from sketchpad.middleware import OriginValidationMiddleware

app = create_app()

cfg = get_config()
middleware = [
    Middleware(
        OriginValidationMiddleware,
        allowed_origins=cfg["ALLOWED_ORIGINS"],
    ),
]

app.run(transport="http", host="0.0.0.0", port=8000, middleware=middleware)
```

### Updated config.py
```python
# Add to get_config() dict:
"ALLOWED_ORIGINS": [
    o.strip() for o in
    os.environ.get("ALLOWED_ORIGINS", "https://claude.ai,https://www.claude.ai").split(",")
    if o.strip()
],
```

### Security Test Script (test_security.py)
```python
#!/usr/bin/env -S uv run python
"""Security hardening tests for the Sketchpad MCP server.

Tests Origin validation (SEC-01) and token authentication (SEC-02)
against the live deployment at the public URL.
"""
import httpx
import sys

SERVER_URL = "https://sketchpad.kempenich.ai"

def test_bad_origin():
    """Request with malicious Origin should be rejected with 403."""
    resp = httpx.post(
        f"{SERVER_URL}/mcp",
        json={"jsonrpc": "2.0", "method": "initialize", "id": 1},
        headers={"Origin": "https://evil.com", "Content-Type": "application/json"},
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    body = resp.json()
    assert body["error"] == "origin_not_allowed"

def test_no_origin():
    """Request with no Origin should pass through (to auth check)."""
    resp = httpx.post(
        f"{SERVER_URL}/mcp",
        json={"jsonrpc": "2.0", "method": "initialize", "id": 1},
        headers={"Content-Type": "application/json"},
    )
    # Should get 401 (auth required), NOT 403 (origin blocked)
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

def test_no_token():
    """Request without Authorization header should return 401."""
    resp = httpx.post(
        f"{SERVER_URL}/mcp",
        json={"jsonrpc": "2.0", "method": "initialize", "id": 1},
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
    assert "www-authenticate" in resp.headers

def test_discovery_open():
    """Discovery endpoints should remain open (no Origin check, no auth)."""
    resp = httpx.get(f"{SERVER_URL}/.well-known/oauth-authorization-server")
    assert resp.status_code == 200
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No Origin validation | MCP spec REQUIRES Origin validation on Streamable HTTP | MCP spec 2025-06-18 | Servers MUST validate; 403 for invalid Origin |
| Custom auth middleware | FastMCP built-in `RequireAuthMiddleware` | FastMCP 2.x+ | Auth handled automatically when `auth=` is provided |
| MCP SDK `TransportSecuritySettings` | FastMCP Starlette middleware | FastMCP 3.x | SDK settings not passed through by FastMCP; use Starlette middleware instead |
| DNS rebinding as primary threat | Token-based auth as primary defense for remote servers | MCP spec 2025-06-18 | DNS rebinding is mainly a localhost concern; remote servers behind reverse proxies focus on token auth + Origin validation |

**Deprecated/outdated:**
- `TransportSecuritySettings` via `mcp.server.fastmcp` (the MCP SDK's own FastMCP class): This project uses the `fastmcp` library (gofastmcp.com), not the SDK's built-in FastMCP. The SDK's settings are not exposed through the library's `create_streamable_http_app()`.

## Discretion Recommendations

### Origin Allowlist Values
**Recommendation:** Default to `https://claude.ai,https://www.claude.ai` as the allowlist. Claude AI mobile app and Claude Code CLI likely do NOT send Origin headers (they are not browsers), so they will pass through under the "no Origin = allow" policy. If Claude AI's web interface sends requests, it would likely use `https://claude.ai` as Origin. Log all incoming Origins during initial deployment to refine.

### Gating `/authorize` and `/token`
**Recommendation:** Do NOT gate these with Origin checks. These are OAuth flow endpoints that receive redirects from GitHub (for `/authorize` callback) and form-encoded POST requests from clients (for `/token`). Adding Origin checks risks breaking the OAuth flow. The MCP spec only requires Origin validation on the MCP endpoint itself, not on OAuth infrastructure.

### Test Script Organization
**Recommendation:** Create a separate `test_security.py` script alongside `test_oauth.py`. The security tests are short, non-interactive (no browser needed), and test a different concern. Keeping them separate makes them independently runnable. Structure similar to test_oauth.py with TestResults tracker.

### Claude Code Test Skill Updates
**Recommendation:** Do NOT modify the test skill. The test skill exercises read/write via MCP tools, which already go through auth. If hardening breaks the happy path, the test skill will fail naturally. Adding explicit security checks to an interactive skill adds complexity without value. The `test_security.py` script handles security-specific verification.

### WWW-Authenticate Header
**Recommendation:** FastMCP's `RequireAuthMiddleware` already returns proper `WWW-Authenticate: Bearer` headers with `error`, `error_description`, and `resource_metadata` URL. No additional work needed -- this was verified by reading the source code (`fastmcp/server/auth/middleware.py`).

## Open Questions

1. **What Origin does Claude AI actually send?**
   - What we know: Claude AI mobile app likely doesn't send Origin (native app, not browser). Claude Code CLI definitely doesn't send Origin. Claude.ai web interface would send `https://claude.ai` if it made direct requests to MCP servers, but it likely proxies through Anthropic's backend.
   - What's unclear: The exact Origin value (if any) that reaches the server from a legitimate Claude AI request.
   - Recommendation: Deploy with permissive allowlist, log all Origin values, refine after observing real traffic. The "no Origin = allow" policy ensures this doesn't block legitimate traffic during discovery.

2. **Does Cloudflare Tunnel preserve the Origin header?**
   - What we know: Cloudflare generally passes through standard HTTP headers. It adds its own headers (CF-Connecting-IP, CF-Ray) but documentation doesn't explicitly address Origin.
   - What's unclear: Whether Cloudflare Tunnel modifies, strips, or adds Origin headers.
   - Recommendation: Test empirically by sending requests with explicit Origin through the tunnel and logging what arrives. If stripped, the "no Origin = allow" policy handles it. If modified, update the allowlist accordingly.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Manual test scripts (Python + httpx), no pytest |
| Config file | None -- scripts are standalone |
| Quick run command | `python test_security.py` (hits live server) |
| Full suite command | `python test_security.py && python test_oauth.py` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEC-01 | Bad Origin returns 403 | integration (live) | `python test_security.py` | No -- Wave 0 |
| SEC-01 | No Origin passes through | integration (live) | `python test_security.py` | No -- Wave 0 |
| SEC-01 | Discovery endpoints stay open | integration (live) | `python test_security.py` | No -- Wave 0 |
| SEC-02 | No token returns 401 | integration (live) | `python test_security.py` | No -- Wave 0 |
| SEC-02 | 401 includes WWW-Authenticate | integration (live) | `python test_security.py` | No -- Wave 0 |
| Both | Legitimate request still works | e2e (interactive) | Claude Code test skill + phone test | Skill exists |

### Sampling Rate
- **Per task commit:** `curl` smoke tests against live server
- **Per wave merge:** `python test_security.py` against live deployment
- **Phase gate:** Full test_security.py green + Claude Code test skill + phone re-verification

### Wave 0 Gaps
- [ ] `test_security.py` -- covers SEC-01 and SEC-02 automated checks
- [ ] No framework install needed (httpx already in dependencies)

## Sources

### Primary (HIGH confidence)
- MCP Specification 2025-06-18, Transports section -- Origin validation requirement ("Servers MUST validate the Origin header")
- FastMCP 3.1.0 source code (`server/mixins/transport.py`) -- `mcp.run()` passes `middleware` kwarg through to `http_app()`
- FastMCP 3.1.0 source code (`server/http.py`) -- `create_streamable_http_app()` accepts `middleware` parameter, appends to Starlette app
- FastMCP 3.1.0 source code (`server/auth/middleware.py`) -- `RequireAuthMiddleware` returns 401 with `WWW-Authenticate: Bearer` header
- MCP Python SDK 1.26.0 source code (`server/transport_security.py`) -- Reference implementation of Origin validation (returns 403 for invalid Origin, allows absent Origin)
- Starlette documentation -- `BaseHTTPMiddleware` pattern for request interception

### Secondary (MEDIUM confidence)
- [FastMCP HTTP Deployment docs](https://gofastmcp.com/deployment/http) -- `http_app(middleware=[...])` API documentation
- [FastMCP Middleware docs](https://gofastmcp.com/servers/middleware) -- Native middleware system (not used for this phase, but documented for reference)
- [MCP Python SDK PR #861](https://github.com/modelcontextprotocol/python-sdk/pull/861) -- DNS rebinding protection implementation details
- [MCP Python SDK Issue #1798](https://github.com/modelcontextprotocol/python-sdk/issues/1798) -- Guide for resolving 421 Invalid Host Header

### Tertiary (LOW confidence)
- Claude AI Origin header values -- no authoritative documentation found; recommendation based on inference from client types (mobile app, CLI, web)
- Cloudflare Tunnel Origin header behavior -- not explicitly documented; recommendation is to test empirically

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- verified from installed source code, no new dependencies
- Architecture: HIGH -- middleware injection path verified by reading FastMCP 3.1.0 source
- Pitfalls: MEDIUM -- Cloudflare Tunnel behavior and Claude AI Origin values are empirical unknowns
- SEC-02 verification: HIGH -- `RequireAuthMiddleware` source code confirms 401 + WWW-Authenticate behavior

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable -- FastMCP 3.1.0 is pinned in uv.lock)
