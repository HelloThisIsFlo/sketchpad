---
phase: 5
slug: per-user-storage-isolation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-06
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (not yet configured — Wave 0 installs) |
| **Config file** | none — Wave 0 adds `[tool.pytest.ini_options]` to `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~3 seconds |

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
| 05-01-01 | 01 | 0 | ISOL-01..04 | setup | `uv run pytest tests/ -x -q` | No — W0 creates | pending |
| 05-02-01 | 02 | 1 | ISOL-01 | unit | `uv run pytest tests/test_user_isolation.py::test_user_path_resolution -x` | No — W0 | pending |
| 05-02-02 | 02 | 1 | ISOL-01 | unit | `uv run pytest tests/test_user_isolation.py::test_two_users_isolated -x` | No — W0 | pending |
| 05-02-03 | 02 | 1 | ISOL-02 | unit | `uv run pytest tests/test_user_isolation.py::test_path_traversal_blocked -x` | No — W0 | pending |
| 05-02-04 | 02 | 1 | ISOL-02 | unit | `uv run pytest tests/test_user_isolation.py::test_traversal_logged -x` | No — W0 | pending |
| 05-02-05 | 02 | 1 | ISOL-03 | unit | `uv run pytest tests/test_user_isolation.py::test_auto_create_dir -x` | No — W0 | pending |
| 05-02-06 | 02 | 1 | ISOL-04 | unit | `uv run pytest tests/test_user_isolation.py::test_username_lowercased -x` | No — W0 | pending |
| 05-02-07 | 02 | 1 | ISOL-04 | unit | `uv run pytest tests/test_user_isolation.py::test_invalid_username_rejected -x` | No — W0 | pending |
| 05-02-08 | 02 | 1 | ISOL-04 | unit | `uv run pytest tests/test_user_isolation.py::test_sanitize_idempotent -x` | No — W0 | pending |
| 05-02-09 | 02 | 1 | ISOL-04 | unit | `uv run pytest tests/test_user_isolation.py::test_sanitize_injective -x` | No — W0 | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [ ] `tests/` directory — does not exist yet
- [ ] `tests/conftest.py` — shared fixtures (tmp data dir, mock token, mock config)
- [ ] `tests/test_user_isolation.py` — stubs for ISOL-01 through ISOL-04
- [ ] pytest configuration in `pyproject.toml`: `[tool.pytest.ini_options]` with `testpaths = ["tests"]`
- [ ] pytest dependency: add `pytest` to dev dependencies

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| NFS subdirectory creation on Synology NAS | ISOL-03 | Requires live NFS-backed PVC in Kubernetes | Deploy to staging, write as two different GitHub users, verify directories created |
| Two different GitHub OAuth users see isolated data | ISOL-01 | Requires real GitHub OAuth flow | Authenticate as user A, write data; authenticate as user B, verify user A's data is invisible |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
