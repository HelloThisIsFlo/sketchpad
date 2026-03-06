---
phase: 04-hardening
plan: 01
subsystem: security
tags: [origin-validation, middleware, starlette, cors-alternative, mcp-security]

# Dependency graph
requires:
  - phase: 03-deploy-integration
    provides: Running MCP server on K8s with OAuth auth at thehome-sketchpad.kempenich.dev
provides:
  - Origin validation middleware blocking disallowed Origins on /mcp with 403
  - ALLOWED_ORIGINS configurable via environment variable
  - Automated security test suite (test_security.py) for regression testing
affects: [04-hardening]

# Tech tracking
tech-stack:
  added: []
  patterns: [Starlette BaseHTTPMiddleware for request filtering, middleware kwarg in FastMCP app.run()]

key-files:
  created: [src/sketchpad/middleware.py, test_security.py]
  modified: [src/sketchpad/config.py, src/sketchpad/__main__.py, k8s/deployment.yaml]

key-decisions:
  - "Origin validation only on /mcp path -- discovery, health, OAuth endpoints remain open"
  - "No Origin header = pass through (non-browser CLI clients) -- auth layer handles token check"
  - "No CORS middleware added (user decision) -- Origin check is allowlist-only, not CORS"
  - "docker buildx --platform linux/amd64 for Apple Silicon to amd64 K8s (consistent with Phase 3)"

patterns-established:
  - "Middleware injection via app.run(middleware=[...]) kwarg in __main__.py"
  - "Security test script pattern: test_security.py alongside test_oauth.py at project root"

requirements-completed: [SEC-01, SEC-02]

# Metrics
duration: 3min
completed: 2026-03-05
---

# Phase 4 Plan 1: Origin Validation + Auth Verification Summary

**Starlette Origin validation middleware on /mcp endpoint with automated security test suite verifying 403/401 responses on live K8s deployment**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-05T18:50:26Z
- **Completed:** 2026-03-05T18:53:32Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Origin validation middleware rejects disallowed Origins with 403 JSON error on /mcp
- Requests without Origin header pass through to auth (401 without token, not 403)
- FastMCP's built-in auth returns 401 with WWW-Authenticate for unauthenticated requests
- Discovery endpoints and /health remain unaffected by Origin checks
- All 8 security assertions pass against live deployment at thehome-sketchpad.kempenich.dev

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Origin validation middleware and wire into server** - `3e79c51` (feat)
2. **Task 2: Update K8s manifest, build, deploy, and run security tests** - `26b9c6c` (feat)

## Files Created/Modified
- `src/sketchpad/middleware.py` - OriginValidationMiddleware (Starlette BaseHTTPMiddleware) with configurable allowed origins and protected paths
- `src/sketchpad/config.py` - Added ALLOWED_ORIGINS config from env var (defaults to claude.ai)
- `src/sketchpad/__main__.py` - Wired middleware into FastMCP app.run() via middleware kwarg
- `k8s/deployment.yaml` - Added ALLOWED_ORIGINS env var for K8s pod
- `test_security.py` - 5 automated security tests (8 assertions) against live deployment

## Decisions Made
- Origin validation only applied to /mcp path -- other endpoints (discovery, health, OAuth) remain open per MCP spec
- Absent Origin header passes through to auth layer -- non-browser clients (curl, CLI) are not blocked
- No CORS middleware added (per user decision in research phase)
- Used docker buildx --platform linux/amd64 for Apple Silicon build (consistent with Phase 3 pattern)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - build, push, deploy, and all tests succeeded on first attempt.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Origin validation active and verified on live deployment
- Security test suite available for regression testing
- Ready for 04-02 plan (if any additional hardening tasks)

## Self-Check: PASSED

All 5 created/modified files verified present. Both task commits (3e79c51, 26b9c6c) verified in git log.

---
*Phase: 04-hardening*
*Completed: 2026-03-05*
