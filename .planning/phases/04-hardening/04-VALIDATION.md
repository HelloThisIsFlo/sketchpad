---
phase: 4
slug: hardening
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-05
validated: 2026-03-05
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manual test scripts (Python + httpx), no pytest |
| **Config file** | none — standalone scripts |
| **Quick run command** | `curl -s -o /dev/null -w "%{http_code}" -H "Origin: https://evil.com" -X POST https://thehome-sketchpad.kempenich.dev/mcp` |
| **Full suite command** | `python test_security.py && python test_oauth.py` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick curl smoke test against live server
- **After every plan wave:** Run `python test_security.py && python test_oauth.py`
- **Before `/gsd:verify-work`:** Full suite must be green + Claude Code test skill + phone re-verification
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | SEC-01 | integration (live) | `python test_security.py` (test_bad_origin) | yes | green |
| 04-01-02 | 01 | 1 | SEC-01 | integration (live) | `python test_security.py` (test_no_origin) | yes | green |
| 04-01-03 | 01 | 1 | SEC-01 | integration (live) | `python test_security.py` (test_discovery_open) | yes | green |
| 04-01-04 | 01 | 1 | SEC-02 | integration (live) | `python test_security.py` (test_no_token) | yes | green |
| 04-01-05 | 01 | 1 | SEC-02 | integration (live) | `python test_security.py` (test_no_token — WWW-Authenticate assertion) | yes | green |
| 04-02-01 | 02 | 2 | SEC-01, SEC-02 | e2e (interactive) | Claude Code test skill + phone test | skill exists | manual-only |

*Status: pending · green · red · flaky · manual-only*

---

## Wave 0 Requirements

- [x] `test_security.py` — covers SEC-01 and SEC-02 automated checks (bad Origin 403, no Origin pass, no token 401, WWW-Authenticate header, discovery open)
- No framework install needed (httpx already in dependencies)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Legitimate Claude AI request works after hardening | SEC-01, SEC-02 | Requires Claude AI to initiate real MCP session via OAuth | Run Claude Code test skill (`/test-sketchpad`) and verify read/write cycle |
| Phone test works after hardening | SEC-01, SEC-02 | Requires mobile browser OAuth flow | Open server URL on phone, authenticate, verify MCP tool access |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete

---

## Validation Audit 2026-03-05

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

All 5 automated test functions in `test_security.py` (8 assertions) confirmed passing against live deployment per 04-01-SUMMARY.md and 04-VERIFICATION.md. No new tests needed.
