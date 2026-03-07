---
phase: 3
slug: deploy-integration
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-04
validated: 2026-03-05
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `test_oauth.py` (custom E2E script) + `test_security.py` (security checks) |
| **Config file** | `.env` (secrets for OAuth flow) |
| **Quick run command** | `curl -sf https://sketchpad.kempenich.ai/health` |
| **Full suite command** | `uv run python test_oauth.py` (interactive, requires server + tunnel) |
| **Estimated runtime** | ~15 seconds (automated checks) |

---

## Sampling Rate

- **After every task commit:** `kubectl get pods -n sketchpad` + `curl -sf https://sketchpad.kempenich.ai/.well-known/oauth-authorization-server`
- **After every plan wave:** `uv run python test_oauth.py` against live URL
- **Before `/gsd:verify-work`:** Full E2E from Claude Code CLI + phone test
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 03-01-01 | 01 | 1 | E2E-01 | manual-only | N/A (phone interaction) | COVERED (manual-only) |
| 03-01-02 | 01 | 1 | E2E-02 | manual-only | N/A (phone interaction) | COVERED (manual-only) |
| 03-01-03 | 01 | 1 | E2E-03 | manual-only | N/A (pod restart + cross-conversation) | COVERED (manual-only) |
| 03-02-01 | 02 | 1 | DOCS-01 | artifact | Files verified in repo | COVERED |
| 03-02-02 | 02 | 1 | DOCS-04 | artifact | Files verified in repo | COVERED |

*Status: COVERED · COVERED (manual-only)*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No additional test framework or stubs needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Verified |
|----------|-------------|------------|-------------------|----------|
| Read sketchpad from Claude AI on phone | E2E-01 | Requires human interaction with Claude AI on phone | Open Claude on phone > ask to read a file > verify content appears | Yes (VERIFICATION.md) |
| Write to sketchpad from Claude AI on phone | E2E-02 | Requires human interaction with Claude AI on phone | Open Claude on phone > ask to write text > verify write succeeds | Yes (VERIFICATION.md) |
| Data persists across pod restart | E2E-03 | Requires pod restart + new conversation on live cluster | Write content > `kubectl rollout restart deployment/sketchpad -n sketchpad` > new conversation > read back | Yes (VERIFICATION.md — survived full Proxmox reboot) |

---

## Artifact Verifications

| Requirement | Check | Result |
|-------------|-------|--------|
| DOCS-01 | `docs/README.md` exists + 5 numbered guides (01-05) present | Verified: all 7 docs in `docs/`, README with Quick Start, guides 01-05 present |
| DOCS-04 | `docs/05-claude-ai-setup.md` contains phone setup section | Verified: "Claude.ai (Phone)" section at line 15, "phone" referenced 3 times |

---

## Validation Sign-Off

- [x] All tasks have automated verify, artifact check, or manual-only justification
- [x] Sampling continuity: manual-only tasks are infrastructure/E2E requiring live cluster
- [x] No Wave 0 gaps — existing test infrastructure sufficient
- [x] No watch-mode flags
- [x] Feedback latency < 15s for automated checks
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-05

---

## Validation Audit 2026-03-05

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Manual-only (justified) | 3 |
| Artifact-verified | 2 |

**Auditor notes:** All 5 requirements reviewed. E2E-01/02/03 are correctly manual-only — they require phone interaction and live cluster access. DOCS-01/04 are documentation artifacts verified by direct file inspection (not just trusting the VERIFICATION report). No automated test gaps exist.
