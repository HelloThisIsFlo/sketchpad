---
phase: 6
slug: storage-limits
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 06-01-01 | 01 | 1 | STOR-CFG | unit | `pytest tests/test_storage_limits.py::test_config_keys -x` | Wave 0 | pending |
| 06-01-02 | 01 | 1 | STOR-01 | unit | `pytest tests/test_storage_limits.py::test_replace_exceeds_user_limit -x` | Wave 0 | pending |
| 06-01-03 | 01 | 1 | STOR-01 | unit | `pytest tests/test_storage_limits.py::test_append_exceeds_user_limit -x` | Wave 0 | pending |
| 06-01-04 | 01 | 1 | STOR-01 | unit | `pytest tests/test_storage_limits.py::test_at_user_limit_accepted -x` | Wave 0 | pending |
| 06-01-05 | 01 | 1 | STOR-01 | unit | `pytest tests/test_storage_limits.py::test_user_limit_error_message -x` | Wave 0 | pending |
| 06-01-06 | 01 | 1 | STOR-01 | unit | `pytest tests/test_storage_limits.py::test_user_limit_logged_warning -x` | Wave 0 | pending |
| 06-01-07 | 01 | 1 | STOR-02 | unit | `pytest tests/test_storage_limits.py::test_global_limit_exceeded -x` | Wave 0 | pending |
| 06-01-08 | 01 | 1 | STOR-02 | unit | `pytest tests/test_storage_limits.py::test_global_limit_replace_net_addition -x` | Wave 0 | pending |
| 06-01-09 | 01 | 1 | STOR-02 | unit | `pytest tests/test_storage_limits.py::test_global_limit_error_message -x` | Wave 0 | pending |
| 06-01-10 | 01 | 1 | STOR-02 | unit | `pytest tests/test_storage_limits.py::test_per_user_checked_before_global -x` | Wave 0 | pending |
| 06-01-11 | 01 | 1 | STOR-READ | unit | `pytest tests/test_storage_limits.py::test_read_no_soft_warning -x` | Wave 0 | pending |
| 06-01-12 | 01 | 1 | STOR-BYTE | unit | `pytest tests/test_storage_limits.py::test_multibyte_char_size -x` | Wave 0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_storage_limits.py` -- stubs for STOR-01, STOR-02, config changes, read_file cleanup
- [ ] Update `tests/test_user_isolation.py:_mock_config()` -- replace `SIZE_LIMIT` with new keys

*Existing infrastructure covers all other phase requirements.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
