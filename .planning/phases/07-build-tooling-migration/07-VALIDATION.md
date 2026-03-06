---
phase: 7
slug: build-tooling-migration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-06
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 8.0 |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest -x` |
| **Full suite command** | `uv run pytest -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -x`
- **After every plan wave:** Run `uv run pytest -v && uv run ruff check .`
- **Before `/gsd:verify-work`:** Full suite must be green + CI pipeline green on push to main
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | BUILD-01 | smoke | `just --list` (verify output contains all recipe names) | N/A | ⬜ pending |
| 07-01-02 | 01 | 1 | BUILD-01 | smoke | `just build` / `just status` (verify recipes run) | N/A | ⬜ pending |
| 07-02-01 | 02 | 1 | BUILD-01 | smoke | `uv run ruff check . && uv run ruff format --check .` | N/A | ⬜ pending |
| 07-03-01 | 03 | 2 | BUILD-02 | smoke | Push to main, verify CI run passes | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

None — existing test infrastructure covers regression. BUILD-01/BUILD-02 are tooling changes verified by running the tools themselves (just --list, CI pipeline run), not by pytest tests.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Justfile recipes match Makefile output | BUILD-01 | Tooling migration — output comparison is visual | Run `just build`, `just status`, etc. and compare with old `make` commands |
| CI pipeline runs with just+lint gates | BUILD-02 | Requires actual GitHub Actions run | Push to main and verify CI workflow completes successfully |
| Makefile deleted with no stale references | BUILD-01 | File deletion verification | `ls Makefile` should fail; grep for "make" in CI/docs |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
