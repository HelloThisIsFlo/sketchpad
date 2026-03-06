---
phase: 6
slug: storage-limits
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-06
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | STOR-CFG | unit | `pytest tests/test_storage_limits.py::test_config_keys -x` | Yes | green |
| 06-01-02 | 01 | 1 | STOR-01 | unit | `pytest tests/test_storage_limits.py::test_replace_exceeds_user_limit -x` | Yes | green |
| 06-01-03 | 01 | 1 | STOR-01 | unit | `pytest tests/test_storage_limits.py::test_append_exceeds_user_limit -x` | Yes | green |
| 06-01-04 | 01 | 1 | STOR-01 | unit | `pytest tests/test_storage_limits.py::test_at_user_limit_accepted -x` | Yes | green |
| 06-01-05 | 01 | 1 | STOR-01 | unit | `pytest tests/test_storage_limits.py::test_user_limit_error_message -x` | Yes | green |
| 06-01-06 | 01 | 1 | STOR-01 | unit | `pytest tests/test_storage_limits.py::test_user_limit_logged_warning -x` | Yes | green |
| 06-01-07 | 01 | 1 | STOR-02 | unit | `pytest tests/test_storage_limits.py::test_global_limit_exceeded -x` | Yes | green |
| 06-01-08 | 01 | 1 | STOR-02 | unit | `pytest tests/test_storage_limits.py::test_global_limit_replace_net_addition -x` | Yes | green |
| 06-01-09 | 01 | 1 | STOR-02 | unit | `pytest tests/test_storage_limits.py::test_global_limit_error_message -x` | Yes | green |
| 06-01-10 | 01 | 1 | STOR-02 | unit | `pytest tests/test_storage_limits.py::test_per_user_checked_before_global -x` | Yes | green |
| 06-01-11 | 01 | 1 | STOR-READ | unit | `pytest tests/test_storage_limits.py::test_read_no_soft_warning -x` | Yes | green |
| 06-01-12 | 01 | 1 | STOR-BYTE | unit | `pytest tests/test_storage_limits.py::test_multibyte_char_size -x` | Yes | green |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [x] `tests/test_storage_limits.py` -- 12 tests for STOR-01, STOR-02, config changes, read_file cleanup
- [x] Update `tests/test_user_isolation.py:_mock_config()` -- replaced `SIZE_LIMIT` with new keys

*All wave 0 requirements satisfied.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s (0.61s actual)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete

---

## Validation Audit 2026-03-06

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Total tests | 12 |
| All green | 12 |
| Suite runtime | 0.61s |
