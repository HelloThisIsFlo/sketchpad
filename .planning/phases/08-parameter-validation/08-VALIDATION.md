---
phase: 8
slug: parameter-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
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
| **Estimated runtime** | ~2 seconds |

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
| 08-01-01 | 01 | 1 | VALID-01 | unit | `uv run pytest tests/test_parameter_validation.py::test_literal_type_annotation -x` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | VALID-02 | unit | `uv run pytest tests/test_parameter_validation.py::test_default_mode_is_append -x` | ❌ W0 | ⬜ pending |
| 08-01-03 | 01 | 1 | VALID-03 | unit | `uv run pytest tests/test_parameter_validation.py::test_schema_enum -x` | ❌ W0 | ⬜ pending |
| 08-01-04 | 01 | 1 | VALID-04 | unit | `uv run pytest tests/test_parameter_validation.py::test_invalid_mode_rejected -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_parameter_validation.py` — stubs for VALID-01 through VALID-04
- No framework install needed (pytest already configured)
- No fixture gaps (existing conftest.py sufficient)

*Existing infrastructure covers framework and fixture needs.*

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
