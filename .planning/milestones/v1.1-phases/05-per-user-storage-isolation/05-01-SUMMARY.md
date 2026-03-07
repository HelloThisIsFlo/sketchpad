---
phase: 05-per-user-storage-isolation
plan: 01
subsystem: auth
tags: [path-traversal, user-identity, pytest, tdd, sanitization]

# Dependency graph
requires:
  - phase: 04-hardening
    provides: "Shipped v1.0 with OAuth 2.1 authentication"
provides:
  - "resolve_user_dir() function: maps (provider, raw_username) to safe filesystem path"
  - "pytest infrastructure with conftest.py fixtures"
  - "15 unit tests covering ISOL-01, ISOL-02, ISOL-04"
affects: [05-02-wire-tools, 06-storage-limits]

# Tech tracking
tech-stack:
  added: [pytest]
  patterns: [tdd-red-green, path-traversal-defense, provider-scoped-directories]

key-files:
  created:
    - src/sketchpad/user_identity.py
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_user_isolation.py
  modified:
    - pyproject.toml

key-decisions:
  - "No slugify library needed -- GitHub usernames are already filesystem-safe; lowercase + regex is sufficient"
  - "Regex catches traversal attempts before is_relative_to -- defense layers work in sequence, not redundantly"

patterns-established:
  - "TDD red-green: write failing tests first, then implement to pass"
  - "Provider-scoped path resolution: data_dir / provider / sanitized_identifier"
  - "Defense-in-depth: regex validation + Path.resolve() + is_relative_to()"

requirements-completed: [ISOL-01, ISOL-02, ISOL-04]

# Metrics
duration: 2min
completed: 2026-03-06
---

# Phase 5 Plan 1: User Identity Resolution Summary

**TDD-built resolve_user_dir() with regex validation, case-normalization, and path traversal defense -- 15 tests all green**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-06T18:46:18Z
- **Completed:** 2026-03-06T18:48:23Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- pytest infrastructure established with dev dependency and conftest.py fixtures
- 15 unit tests covering user path resolution, isolation, case-sensitivity, path traversal, invalid usernames, idempotency, injectivity, single-char edge case, and unknown providers
- resolve_user_dir() function with GitHub username regex validation, lowercase normalization, and Path.resolve() + is_relative_to() defense-in-depth
- Function is pure (no side effects, no directory creation) -- testable and composable

## Task Commits

Each task was committed atomically:

1. **Task 1: Set up test infrastructure and write failing tests** - `6eb8833` (test)
2. **Task 2: Implement resolve_user_dir to pass all tests** - `f6e89a7` (feat)

_TDD: Task 1 = RED phase (all tests fail with ImportError), Task 2 = GREEN phase (all 15 pass)_

## Files Created/Modified
- `src/sketchpad/user_identity.py` - resolve_user_dir() with sanitization and traversal defense
- `tests/__init__.py` - Empty package init for test discovery
- `tests/conftest.py` - Shared fixtures (tmp_data_dir)
- `tests/test_user_isolation.py` - 15 tests covering ISOL-01, ISOL-02, ISOL-04
- `pyproject.toml` - Added pytest dev dependency and test configuration

## Decisions Made
- No slugify library: GitHub usernames are `[a-zA-Z0-9-]` (1-39 chars), already filesystem-safe. Lowercase + regex is sufficient, injective, and idempotent.
- Regex catches traversal inputs (like `../etc`) before the is_relative_to check because dots and slashes are invalid GitHub username characters. Both layers exist for defense-in-depth.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_traversal_logged assertion**
- **Found during:** Task 2 (GREEN phase)
- **Issue:** Plan's test expected "Path traversal attempt" in logs, but `../etc` is caught by regex validation (dots/slashes invalid for GitHub) before reaching the is_relative_to traversal check. The log message is "Invalid GitHub username attempted" instead.
- **Fix:** Updated test to verify WARNING-level log entry contains the suspicious input `../etc`, rather than checking for the specific "Path traversal attempt" message. Both defense layers exist; the regex is simply the first to trigger.
- **Files modified:** tests/test_user_isolation.py
- **Verification:** All 15 tests pass
- **Committed in:** f6e89a7 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug in test expectation)
**Impact on plan:** Minimal -- the security behavior is correct (traversal blocked + WARNING logged). Only the test assertion needed adjustment to match which defense layer fires first.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- resolve_user_dir() is ready to be wired into read_file/write_file tools in Plan 05-02
- pytest infrastructure is available for additional tests
- No blockers

---
## Self-Check: PASSED

All 5 files verified present. Both task commits (6eb8833, f6e89a7) verified in git log.

---
*Phase: 05-per-user-storage-isolation*
*Completed: 2026-03-06*
