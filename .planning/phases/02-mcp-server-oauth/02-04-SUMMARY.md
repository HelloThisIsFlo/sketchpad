---
phase: 02-mcp-server-oauth
plan: 04
subsystem: testing
tags: [oauth, rfc-9728, discovery, mcp, curl, bash]

# Dependency graph
requires:
  - phase: 02-mcp-server-oauth
    provides: test-oauth.sh end-to-end script (Plan 02-03)
provides:
  - Corrected DISC-02 endpoint URL in test-oauth.sh per RFC 9728 Section 3.1
affects: [02-05-PLAN, verification]

# Tech tracking
tech-stack:
  added: []
  patterns: [RFC 9728 path-aware well-known URL construction]

key-files:
  created: []
  modified: [test-oauth.sh]

key-decisions:
  - "DISC-02 URL is path-aware per RFC 9728: /.well-known/oauth-protected-resource{resource_path} where resource_path=/mcp"

patterns-established:
  - "RFC 9728 path-aware discovery: well-known URL includes the MCP resource path suffix"

requirements-completed: [DISC-02]

# Metrics
duration: 1min
completed: 2026-03-04
---

# Phase 2 Plan 4: Fix DISC-02 URL Summary

**Corrected test-oauth.sh DISC-02 endpoint from /.well-known/oauth-protected-resource to /.well-known/oauth-protected-resource/mcp per RFC 9728 path-aware discovery**

## Performance

- **Duration:** 45s
- **Started:** 2026-03-04T12:04:31Z
- **Completed:** 2026-03-04T12:05:16Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Fixed the DISC-02 discovery URL in test-oauth.sh to match FastMCP's RFC 9728 path-aware registration
- Updated FAIL message to reference RFC 9728 Section 3.1 for better debugging context
- Root cause confirmed: FastMCP registers the protected resource metadata endpoint at the path-aware URL because MCP resource is served at /mcp

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix DISC-02 URL in test-oauth.sh** - `66a0e4b` (fix)

## Files Created/Modified
- `test-oauth.sh` - Updated DISC-02 endpoint URL from `/.well-known/oauth-protected-resource` to `/.well-known/oauth-protected-resource/mcp`

## Decisions Made
- DISC-02 URL uses RFC 9728 path-aware format: `/.well-known/oauth-protected-resource{resource_path}` where resource_path is `/mcp` (the MCP server's resource path)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- test-oauth.sh now has the correct DISC-02 endpoint URL
- Plan 05 checkpoint can verify this against a live server to confirm the 404 is resolved

## Self-Check: PASSED

- FOUND: test-oauth.sh
- FOUND: 02-04-SUMMARY.md
- FOUND: commit 66a0e4b

---
*Phase: 02-mcp-server-oauth*
*Completed: 2026-03-04*
