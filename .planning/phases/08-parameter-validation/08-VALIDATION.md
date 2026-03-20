---
phase: 8
slug: parameter-validation
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-20
audited: 2026-03-20
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -x` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~0.7 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x`
- **After every plan wave:** Run `just test && just lint`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | VALID-01 | unit | `uv run pytest tests/test_parameter_validation.py::test_literal_type_annotation -x` | ✅ | ✅ green |
| 08-01-02 | 01 | 1 | VALID-02 | unit | `uv run pytest tests/test_parameter_validation.py::test_default_mode_is_append -x` | ✅ | ✅ green |
| 08-01-03 | 01 | 1 | VALID-03 | unit | `uv run pytest tests/test_parameter_validation.py::test_schema_enum -x` | ✅ | ✅ green |
| 08-01-04 | 01 | 1 | VALID-04 | unit | `uv run pytest tests/test_parameter_validation.py::test_invalid_mode_rejected -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_parameter_validation.py` — 4 tests for VALID-01 through VALID-04
- No framework install needed (pytest already configured)
- No fixture gaps (existing conftest.py sufficient)

*All Wave 0 requirements satisfied during execution.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved

---

## Validation Audit 2026-03-20

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

All 4 requirements (VALID-01..04) have automated tests in `tests/test_parameter_validation.py`. Full suite: 39 passed, 0 failures. No gaps to fill.
