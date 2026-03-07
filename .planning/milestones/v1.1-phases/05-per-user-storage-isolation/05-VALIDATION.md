---
phase: 5
slug: per-user-storage-isolation
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-06
validated: 2026-03-06
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Actual runtime** | 0.65s (35 tests) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 0 | ISOL-01..04 | setup | `uv run pytest tests/ -x -q` | Yes | green |
| 05-02-01 | 02 | 1 | ISOL-01 | unit | `uv run pytest tests/test_user_isolation.py::test_user_path_resolution -x` | Yes | green |
| 05-02-02 | 02 | 1 | ISOL-01 | unit | `uv run pytest tests/test_user_isolation.py::test_two_users_isolated -x` | Yes | green |
| 05-02-03 | 02 | 1 | ISOL-02 | unit | `uv run pytest tests/test_user_isolation.py::test_path_traversal_blocked -x` | Yes | green |
| 05-02-04 | 02 | 1 | ISOL-02 | unit | `uv run pytest tests/test_user_isolation.py::test_traversal_logged -x` | Yes | green |
| 05-02-05 | 02 | 1 | ISOL-03 | unit | `uv run pytest tests/test_user_isolation.py::test_auto_create_dir -x` | Yes | green |
| 05-02-06 | 02 | 1 | ISOL-04 | unit | `uv run pytest tests/test_user_isolation.py::test_username_lowercased -x` | Yes | green |
| 05-02-07 | 02 | 1 | ISOL-04 | unit | `uv run pytest tests/test_user_isolation.py::test_invalid_username_rejected -x` | Yes | green |
| 05-02-08 | 02 | 1 | ISOL-04 | unit | `uv run pytest tests/test_user_isolation.py::test_sanitize_idempotent -x` | Yes | green |
| 05-02-09 | 02 | 1 | ISOL-04 | unit | `uv run pytest tests/test_user_isolation.py::test_sanitize_injective -x` | Yes | green |

*Status: pending · **green** · red · flaky*

### Additional Tests (beyond original map)

| Test | Requirement | Source |
|------|-------------|--------|
| `test_single_char_username` | ISOL-04 | Plan 01 |
| `test_auto_create_dir_not_done_by_resolve` | ISOL-03 | Plan 01 |
| `test_unknown_provider_rejected` | ISOL-04 | Plan 01 |
| `test_read_returns_welcome_for_new_user` | ISOL-01 | Plan 02 |
| `test_auto_create_dir` (tool-level) | ISOL-03 | Plan 02 |
| `test_read_after_write` | ISOL-01 | Plan 02 |
| `test_two_users_isolated_via_tools` | ISOL-01 | Plan 02 |
| `test_missing_token_raises` | Auth | Plan 02 |
| `test_missing_login_claim_raises` | Auth | Plan 02 |
| `test_response_excludes_username` | ISOL-01 | Plan 02 |
| `test_tool_schema_excludes_username` | ISOL-01 | Plan 02 |

---

## Wave 0 Requirements

- [x] `tests/` directory
- [x] `tests/conftest.py` — shared fixtures (tmp data dir, mock token, mock config)
- [x] `tests/test_user_isolation.py` — 23 tests covering ISOL-01 through ISOL-04
- [x] pytest configuration in `pyproject.toml`: `[tool.pytest.ini_options]` with `testpaths = ["tests"]`
- [x] pytest dependency: added to dev dependencies

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| NFS subdirectory creation on Synology NAS | ISOL-03 | Requires live NFS-backed PVC in Kubernetes | Deploy to staging, write as two different GitHub users, verify directories created |
| Two different GitHub OAuth users see isolated data | ISOL-01 | Requires real GitHub OAuth flow | Authenticate as user A, write data; authenticate as user B, verify user A's data is invisible |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s (0.65s actual)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete

---

## Validation Audit 2026-03-06

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Total tests (phase 5) | 23 |
| Total tests (suite) | 35 |
| All green | Yes |
