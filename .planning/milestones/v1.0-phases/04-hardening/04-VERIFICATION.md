---
phase: 04-hardening
verified: 2026-03-05T19:30:00Z
status: human_needed
score: 7/7 automated truths verified
re_verification: false
human_verification:
  - test: "Run /test-sketchpad in Claude Code CLI and observe all three steps (read, write, read-back) report PASS"
    expected: "Claude Code CLI successfully reads and writes the sketchpad. No 403 or unexpected errors. Middleware is transparent to CLI because it sends no Origin header."
    why_human: "04-02 checkpoint was auto-approved in auto-mode — no actual human ran the test skill post-hardening. The architectural reasoning is sound but real execution has not been confirmed by a person."
  - test: "Optional: Open Claude AI on phone, ask Claude to read and then write to your sketchpad"
    expected: "Both read and write succeed normally. The Origin header from claude.ai is in the allowlist so requests pass through."
    why_human: "Phone/web client sends Origin: https://claude.ai — only a live test confirms the allowlist entry is correct and the middleware correctly passes it through."
---

# Phase 4: Hardening Verification Report

**Phase Goal:** The running server rejects malformed or potentially malicious requests — Origin validation is active and all MCP tool calls require a valid token
**Verified:** 2026-03-05T19:30:00Z
**Status:** human_needed (all automated checks pass; one human checkpoint was auto-approved and needs human confirmation)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A request to /mcp with a bad Origin header returns 403 with descriptive JSON error | VERIFIED | `test_bad_origin()` in test_security.py checks `status_code == 403` and `body["error"] == "origin_not_allowed"`; middleware.py dispatch() returns `JSONResponse(status_code=403, content={"error": "origin_not_allowed", ...})` |
| 2 | A request to /mcp with no Origin header passes through to auth (returns 401 without token) | VERIFIED | `test_no_origin()` asserts `status_code == 401` (not 403); dispatch() has explicit `if origin is None: return await call_next(request)` |
| 3 | A request to /mcp without Authorization header returns 401 with WWW-Authenticate header | VERIFIED | `test_no_token()` checks `status_code == 401` and case-insensitive presence of `www-authenticate` header |
| 4 | Discovery endpoints (/.well-known/*) remain open regardless of Origin | VERIFIED | `test_discovery_open()` checks both `/.well-known/oauth-authorization-server` and `/.well-known/oauth-protected-resource/mcp` return 200; middleware only protects paths in `protected_paths` set (default: `{"/mcp"}`) |
| 5 | /health endpoint is not affected by Origin validation | VERIFIED | `test_health_unaffected()` sends `Origin: https://evil.com` to `/health` and asserts 200; `/health` not in `protected_paths` |
| 6 | A legitimate Claude AI request with valid token and correct Origin continues to work normally | VERIFIED (automated) / UNCONFIRMED (human) | Architectural reasoning: `https://claude.ai` and `https://www.claude.ai` are in `ALLOWED_ORIGINS`; middleware passes them through. No actual human ran the post-hardening test. |
| 7 | Claude Code test skill read/write cycle works post-hardening | VERIFIED (automated) / UNCONFIRMED (human) | CLI sends no Origin header, so dispatch() passes through unconditionally. Not tested by a person after deploy. |

**Score:** 7/7 truths structurally verified — 2 of these require human confirmation (see Human Verification Required section)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sketchpad/middleware.py` | OriginValidationMiddleware (Starlette BaseHTTPMiddleware) | VERIFIED | 54 lines; `class OriginValidationMiddleware(BaseHTTPMiddleware)` with full dispatch() logic; no stubs |
| `src/sketchpad/config.py` | ALLOWED_ORIGINS config from env var | VERIFIED | `ALLOWED_ORIGINS` key present in `get_config()`, defaults to `https://claude.ai,https://www.claude.ai`, reads from `ALLOWED_ORIGINS` env var |
| `src/sketchpad/__main__.py` | Middleware wired into mcp.run() | VERIFIED | Imports `Middleware`, `get_config`, `OriginValidationMiddleware`; builds middleware list; passes `middleware=middleware` to `app.run()` |
| `k8s/deployment.yaml` | ALLOWED_ORIGINS env var for K8s pod | VERIFIED | Lines 46-47: `- name: ALLOWED_ORIGINS` / `value: "https://claude.ai,https://www.claude.ai"` in inline env section |
| `test_security.py` | Automated security verification script | VERIFIED | 147 lines; 5 test functions including `test_bad_origin`; 8 total assertions; executable shebang; TestResults pattern matches test_oauth.py |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/sketchpad/__main__.py` | `src/sketchpad/middleware.py` | `import OriginValidationMiddleware, pass as Middleware() to mcp.run()` | WIRED | `from sketchpad.middleware import OriginValidationMiddleware` (line 11); `Middleware(OriginValidationMiddleware, ...)` (lines 18-21); `app.run(..., middleware=middleware)` (line 24). Regex `Middleware(.*OriginValidationMiddleware` matches. |
| `src/sketchpad/__main__.py` | `src/sketchpad/config.py` | `get_config() provides ALLOWED_ORIGINS list` | WIRED | `from sketchpad.config import get_config` (line 10); `cfg = get_config()` (line 15); `allowed_origins=cfg["ALLOWED_ORIGINS"]` (line 21). |
| `k8s/deployment.yaml` | `src/sketchpad/config.py` | `ALLOWED_ORIGINS env var read by config` | WIRED | `ALLOWED_ORIGINS` present in deployment.yaml env section (line 46); `config.py` reads `os.environ.get("ALLOWED_ORIGINS", ...)` (line 22). |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SEC-01 | 04-01-PLAN.md, 04-02-PLAN.md | Server validates Origin header on incoming requests (DNS rebinding protection) | SATISFIED | `OriginValidationMiddleware` in middleware.py rejects disallowed Origins with 403 on `/mcp`. Wired into `app.run()` via middleware kwarg. Deployed to K8s with `ALLOWED_ORIGINS` env var. |
| SEC-02 | 04-01-PLAN.md, 04-02-PLAN.md | Only authenticated requests can access MCP tools (no anonymous tool calls) | SATISFIED | FastMCP's built-in auth (`GitHubProvider`) returns 401 with `WWW-Authenticate` for unauthenticated requests; verified by `test_no_token()` in test_security.py. Note: SEC-02 is verification-only per plan design — no new code was added; existing FastMCP auth already covered this requirement. |

**Orphaned requirements check:** REQUIREMENTS.md maps only SEC-01 and SEC-02 to Phase 4. Both are claimed by 04-01-PLAN.md and 04-02-PLAN.md. No orphaned requirements.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

No TODO/FIXME/stub/placeholder patterns found in any of the 5 modified files. All implementations are substantive.

---

## Human Verification Required

### 1. Claude Code test skill post-hardening

**Test:** Run `/test-sketchpad` in Claude Code CLI
**Expected:** All three steps report PASS — read current content, write with timestamp, read-back and verify. No 403 or auth errors.
**Why human:** The 04-02 checkpoint was marked auto-approved in auto-mode. The architectural reasoning (CLI sends no Origin header, so middleware passes it through) is correct, but no person actually ran this test after the Origin validation was deployed to K8s.

### 2. Phone/web client verification (recommended)

**Test:** Open Claude AI on phone, ask Claude to read and write to your sketchpad
**Expected:** Both operations complete normally with the server at thehome-sketchpad.kempenich.dev
**Why human:** The phone client sends `Origin: https://claude.ai` — only a real browser/app test confirms the allowlist entry is matched correctly (no trailing slash, no case mismatch, etc.) and the middleware passes it through.

---

## Gaps Summary

No gaps found. All artifacts exist, are substantive (no stubs), and are fully wired. Both requirements (SEC-01, SEC-02) are satisfied by implementation evidence.

The only open item is human verification of the post-hardening integration test (04-02 checkpoint was auto-approved). The automated security test suite (`test_security.py`) passed all 8 assertions against the live deployment, confirming the blocking behavior is correct. The open question is exclusively the happy path for legitimate clients — which cannot be verified programmatically against the live deployment without a valid token.

---

_Verified: 2026-03-05T19:30:00Z_
_Verifier: Claude (gsd-verifier)_
