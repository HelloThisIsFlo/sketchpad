---
phase: 05-per-user-storage-isolation
verified: 2026-03-06T19:10:00Z
status: passed
score: 12/12 must-haves verified
---

# Phase 5: Per-User Storage Isolation Verification Report

**Phase Goal:** Each authenticated user reads and writes only their own sketchpad, isolated by OAuth username
**Verified:** 2026-03-06T19:10:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

Truths are sourced from both plans' `must_haves.truths` and the ROADMAP success criteria.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Two different GitHub usernames resolve to two different directories -- one user cannot access another's data | VERIFIED | `test_two_users_isolated` (unit) + `test_two_users_isolated_via_tools` (integration) both pass. `resolve_user_dir` maps to `base/github/{username}` with distinct paths per username. |
| 2 | A username containing ../ or similar traversal sequences is rejected before any file access occurs | VERIFIED | `test_path_traversal_blocked` passes -- raises ValueError. Regex rejects `../etc` at validation layer (dots invalid for GitHub). Defense-in-depth `is_relative_to` at line 39 of user_identity.py as second layer. |
| 3 | A server operator can see path traversal attempts in WARNING-level logs | VERIFIED | `test_traversal_logged` passes -- asserts WARNING level and suspicious input `../etc` appears in caplog. Logger at line 29: `logger.warning("Invalid GitHub username attempted: %s", raw_identifier)`. |
| 4 | Usernames with invalid characters (spaces, dots, leading hyphens) are rejected | VERIFIED | `test_invalid_username_rejected` parametrized with 5 cases (empty, leading-hyphen, spaces, dots, too-long) -- all pass. Regex `^[a-z0-9]([a-z0-9-]*[a-z0-9])?$` enforces allowed chars. |
| 5 | GitHub usernames differing only in case (e.g. Octocat vs octocat) map to the same directory | VERIFIED | `test_username_lowercased` + `test_sanitize_injective` both pass. `.lower()` at line 27 of user_identity.py before regex check. |
| 6 | Valid single-character GitHub usernames are accepted | VERIFIED | `test_single_char_username` passes. Regex `^[a-z0-9]([a-z0-9-]*[a-z0-9])?$` allows single-char match via optional group. |
| 7 | A user who has never written before sees a welcome message when reading | VERIFIED | `test_read_returns_welcome_for_new_user` passes. `read_file` returns `WELCOME_MESSAGE` when `sketchpad_path.exists()` is False (tools.py line 31-32). |
| 8 | A user's first write automatically creates their personal directory -- no manual setup | VERIFIED | `test_auto_create_dir` passes. `write_file` calls `sketchpad_path.parent.mkdir(parents=True, exist_ok=True)` at tools.py line 54. |
| 9 | Two users writing to their sketchpads cannot see each other's content | VERIFIED | `test_two_users_isolated_via_tools` passes -- alice writes, bob writes, alice reads back only her own data. |
| 10 | The username never appears in the tool parameter list that Claude AI sees | VERIFIED | `test_tool_schema_excludes_username` passes -- read_file has 0 params, write_file has only {content, mode}, no identity-related params. Username extracted server-side via `get_access_token()`. |
| 11 | An unauthenticated request is rejected -- it never falls back to a shared sketchpad | VERIFIED | `test_missing_token_raises` + `test_missing_login_claim_raises` both pass. `assert token is not None` and `assert login` at tools.py lines 14-16 ensure fail-fast. |
| 12 | Tool descriptions tell the user the sketchpad is personal and shared across their AI agents | VERIFIED | read_file docstring: "Read your personal sketchpad...shared across all your AI agents (Claude, Cursor, etc.)". write_file docstring: "Write to your personal sketchpad...shared across all your AI agents that use the same GitHub identity." |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sketchpad/user_identity.py` | resolve_user_dir with sanitization and path traversal defense | VERIFIED | 43 lines. Exports `resolve_user_dir`. Regex validation + `.lower()` + `Path.resolve()` + `is_relative_to()`. |
| `tests/test_user_isolation.py` | Unit + integration tests for all ISOL requirements (min 50 lines) | VERIFIED | 273 lines. 15 unit tests + 8 integration tests = 23 total. All pass. |
| `tests/conftest.py` | Shared fixtures: tmp data dir | VERIFIED | 7 lines. `tmp_data_dir` fixture wrapping pytest `tmp_path`. |
| `src/sketchpad/tools.py` | Per-user read_file and write_file with OAuth identity extraction (min 40 lines) | VERIFIED | 66 lines. Imports `get_access_token` and `resolve_user_dir`. `_get_user_sketchpad_path()` helper extracts identity. |
| `tests/__init__.py` | Empty package init | VERIFIED | Exists. |
| `pyproject.toml` | pytest config and dev dependency | VERIFIED | `[project.optional-dependencies] dev = ["pytest>=8.0"]` and `[tool.pytest.ini_options] testpaths = ["tests"]`. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/sketchpad/user_identity.py` | `pathlib.Path` | `Path.resolve()` + `is_relative_to()` | WIRED | Line 35: `Path(data_dir).resolve()`, line 39: `user_dir.is_relative_to(base)` |
| `tests/test_user_isolation.py` | `src/sketchpad/user_identity.py` | `from sketchpad.user_identity import resolve_user_dir` | WIRED | Line 7 of test file |
| `src/sketchpad/tools.py` | `src/sketchpad/user_identity.py` | `from sketchpad.user_identity import resolve_user_dir` | WIRED | Line 6 of tools.py; used at line 18 in `_get_user_sketchpad_path()` |
| `src/sketchpad/tools.py` | `fastmcp.server.dependencies` | `from fastmcp.server.dependencies import get_access_token` | WIRED | Line 3 of tools.py; used at line 13 in `_get_user_sketchpad_path()` |
| `src/sketchpad/server.py` | `src/sketchpad/tools.py` | `register_tools(mcp)` | WIRED | Line 89 of server.py; tools registered on auth-enabled MCP instance |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ISOL-01 | 05-01, 05-02 | Per-user directory from `TokenClaim("login")` | SATISFIED | `resolve_user_dir` maps `(data_dir, "github", login)` to `data_dir/github/{lowered_login}`. `_get_user_sketchpad_path()` extracts login from `get_access_token().claims["login"]`. Tests verify isolated paths and isolated reads/writes. |
| ISOL-02 | 05-01, 05-02 | Path traversal prevented via `Path.resolve()` + `is_relative_to()` | SATISFIED | user_identity.py lines 35-41: defense-in-depth with regex as first layer and `is_relative_to` as second. `test_path_traversal_blocked` and `test_traversal_logged` verify. |
| ISOL-03 | 05-02 | User directory auto-created on first `write_file` | SATISFIED | tools.py line 54: `sketchpad_path.parent.mkdir(parents=True, exist_ok=True)`. `test_auto_create_dir` verifies directory and file creation from cold start. |
| ISOL-04 | 05-01, 05-02 | Username sanitized to filesystem-safe characters | SATISFIED | user_identity.py: `.lower()` + regex `^[a-z0-9]([a-z0-9-]*[a-z0-9])?$` validates. Tests cover lowercasing, invalid chars, idempotency, and injectivity. |

No orphaned requirements. REQUIREMENTS.md maps ISOL-01 through ISOL-04 to Phase 5, and all four are claimed by plans 05-01 and 05-02.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | - | - | No anti-patterns detected |

No TODO/FIXME/HACK comments. No placeholder returns. No empty handlers. No console.log-only implementations.

### Human Verification Required

### 1. End-to-end OAuth identity flow

**Test:** Deploy the server, authenticate as a real GitHub user via Claude AI or Cursor, write to the sketchpad, then verify the file appears at `/data/github/{username}/sketchpad.md` on the server filesystem.
**Expected:** File exists at the correct per-user path with written content.
**Why human:** Tests mock `get_access_token()` -- the real FastMCP OAuth token-to-claims flow through GitHub is not exercised in unit/integration tests.

### 2. Cross-agent access with same identity

**Test:** Authenticate from two different MCP clients (e.g., Claude AI on phone and Cursor on desktop) using the same GitHub account. Write from one, read from the other.
**Expected:** Both clients see the same sketchpad content.
**Why human:** Requires two real MCP clients and a running server. This is the core value proposition mentioned in 05-CONTEXT.md.

### 3. Tool description display in Claude AI

**Test:** Connect to the server from Claude AI and inspect how the tool descriptions appear in the UI.
**Expected:** Tool descriptions clearly communicate "your personal sketchpad" and cross-agent sharing.
**Why human:** Tool description rendering depends on the MCP client's UI presentation.

### Gaps Summary

No gaps found. All 12 observable truths are verified. All 4 requirements (ISOL-01 through ISOL-04) are satisfied with implementation evidence. All key links are wired. All 23 tests pass. No anti-patterns detected. The phase goal -- "Each authenticated user reads and writes only their own sketchpad, isolated by OAuth username" -- is achieved.

The 3 human verification items are confidence-boosters for production deployment, not blockers. The automated test suite comprehensively covers the isolation logic, path traversal defense, auth enforcement, and schema safety.

---

_Verified: 2026-03-06T19:10:00Z_
_Verifier: Claude (gsd-verifier)_
