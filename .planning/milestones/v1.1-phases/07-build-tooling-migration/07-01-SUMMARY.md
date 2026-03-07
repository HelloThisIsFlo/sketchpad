---
phase: 07-build-tooling-migration
plan: 01
subsystem: infra
tags: [ruff, just, linter, formatter, command-runner]

requires:
  - phase: 06-storage-limits
    provides: complete Python codebase to format and lint
provides:
  - Justfile with 10 recipes (build, deploy, restart, status, test, lint, fmt, dev, logs, default)
  - Ruff linter/formatter configured in pyproject.toml
  - All Python files normalized to ruff format
affects: [07-build-tooling-migration]

tech-stack:
  added: [ruff 0.15, just 1.46]
  patterns: [Justfile as command runner, ruff for lint+format]

key-files:
  created: [Justfile]
  modified: [pyproject.toml, src/sketchpad/server.py, src/sketchpad/tools.py, src/sketchpad/user_identity.py, tests/test_storage_limits.py, tests/test_user_isolation.py, uv.lock]

key-decisions:
  - "Included I (isort) rules in ruff lint selection -- auto-fixed 6 import sorting violations"
  - "Installed just via Homebrew (not available in project venv)"

patterns-established:
  - "Use `just <recipe>` for all project commands (test, lint, fmt, build, deploy)"
  - "Ruff with E4/E7/E9/F/B/I rules as lint baseline"

requirements-completed: [BUILD-01]

duration: 2min
completed: 2026-03-06
---

# Phase 7 Plan 1: Ruff + Justfile Summary

**Ruff linter/formatter configured with one-time format pass, Justfile created with 10 recipes replacing Makefile**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-06T23:36:47Z
- **Completed:** 2026-03-06T23:38:52Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Ruff added as dev dependency with py312 target, line-length 88, E4/E7/E9/F/B/I rules
- One-time format pass: 5 files reformatted, 6 import sorting violations auto-fixed
- Justfile with 10 recipes (default, build, deploy, restart, status, test, lint, fmt, dev, logs)
- All 35 existing tests pass, lint clean, format clean

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ruff config and run one-time format** - `d86a876` (style)
2. **Task 2: Create Justfile with all recipes** - `a890fe0` (feat)

## Files Created/Modified
- `Justfile` - Command runner with 10 recipes (Build, Dev, K8s groups)
- `pyproject.toml` - Added ruff dev dependency and [tool.ruff] config sections
- `src/sketchpad/server.py` - Import sorting normalized
- `src/sketchpad/tools.py` - Ruff formatting applied
- `src/sketchpad/user_identity.py` - Import sorting normalized
- `tests/test_storage_limits.py` - Import sorting normalized
- `tests/test_user_isolation.py` - Import sorting + formatting normalized
- `test_oauth.py` - Ruff formatting applied
- `test_security.py` - Ruff formatting applied
- `uv.lock` - Updated with ruff dependency

## Decisions Made
- Included I (isort) rules in ruff -- auto-fixed 6 import sorting violations as part of one-time format
- Installed `just` via Homebrew since it's a system tool, not a Python dependency

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed just via Homebrew**
- **Found during:** Task 2
- **Issue:** `just` command not found on system
- **Fix:** `brew install just` (system-level tool, not in uv venv)
- **Verification:** `just --list` shows all 10 recipes

**2. [Rule 1 - Bug] Fixed import sorting violations**
- **Found during:** Task 1 (ruff check after format)
- **Issue:** `ruff format` doesn't sort imports; `ruff check` found 6 I001 violations
- **Fix:** Ran `ruff check --fix .` to auto-sort imports
- **Files modified:** src/sketchpad/server.py, src/sketchpad/user_identity.py, tests/test_storage_limits.py, tests/test_user_isolation.py
- **Verification:** `ruff check .` passes clean
- **Committed in:** d86a876 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both auto-fixes necessary for correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Justfile ready for Makefile retirement in plan 07-02
- All lint/format tooling established for CI integration

## Self-Check: PASSED

- All key files exist (Justfile, pyproject.toml, SUMMARY.md)
- All commits verified (d86a876, a890fe0)
- Justfile contains IMAGE constant, pyproject.toml contains [tool.ruff]

---
*Phase: 07-build-tooling-migration*
*Completed: 2026-03-06*
