---
phase: 9
slug: description-update
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (installed) |
| **Config file** | none — uses defaults, tests/ directory |
| **Quick run command** | `python3 -m pytest tests/ -x -q` |
| **Full suite command** | `python3 -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/ -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 0 | DESC-01 | unit | `python3 -m pytest tests/test_descriptions.py::test_read_file_description -x` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 0 | DESC-01 | unit | `python3 -m pytest tests/test_descriptions.py::test_write_file_description -x` | ❌ W0 | ⬜ pending |
| 09-01-03 | 01 | 0 | DESC-02 | unit | `python3 -m pytest tests/test_descriptions.py::test_content_param_has_description -x` | ❌ W0 | ⬜ pending |
| 09-01-04 | 01 | 0 | DESC-02 | unit | `python3 -m pytest tests/test_descriptions.py::test_mode_param_has_description -x` | ❌ W0 | ⬜ pending |
| 09-01-05 | 01 | 0 | DESC-03 | unit | `python3 -m pytest tests/test_descriptions.py::test_write_description_has_guardrails -x` | ❌ W0 | ⬜ pending |
| 09-01-06 | 01 | 0 | D-05 | unit | `python3 -m pytest tests/test_descriptions.py::test_append_newline_separator -x` | ❌ W0 | ⬜ pending |
| 09-01-07 | 01 | 0 | D-05 | unit | `python3 -m pytest tests/test_descriptions.py::test_first_append_no_leading_newline -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_descriptions.py` — new file covering DESC-01, DESC-02, DESC-03 and newline behavior
- [ ] Update `tests/test_parameter_validation.py::test_default_mode_is_append` — assertion needs updating for newline separator

*Existing infrastructure covers framework and fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Claude AI on live server reads/writes without refusal | DESC-01 (SC-1) | Requires deployed MCP server + Claude session | Deploy updated descriptions, connect Claude AI, attempt read then write |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
