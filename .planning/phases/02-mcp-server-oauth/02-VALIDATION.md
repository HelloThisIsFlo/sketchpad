---
phase: 2
slug: mcp-server-oauth
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-04
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | bash + curl + jq (test-oauth.sh) |
| **Config file** | none — script-based testing |
| **Quick run command** | `curl -sf http://localhost:8000/.well-known/oauth-authorization-server \| jq .` |
| **Full suite command** | `./test-oauth.sh http://localhost:8000` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `curl -sf http://localhost:8000/.well-known/oauth-authorization-server | jq .`
- **After every plan wave:** Run `./test-oauth.sh http://localhost:8000`
- **Before `/gsd:verify-work`:** Full suite must be green + MCP Inspector manual verification
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | DISC-01 | smoke | `curl -sf http://localhost:8000/.well-known/oauth-authorization-server \| jq -e '.authorization_endpoint'` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | DISC-02 | smoke | `curl -sf http://localhost:8000/.well-known/oauth-protected-resource \| jq -e '.resource'` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | DISC-03 | smoke | `curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:8000/mcp` (expect 401) | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | AUTH-01 | smoke | `curl -sf -X POST http://localhost:8000/register -H 'Content-Type: application/json' -d '...' \| jq -e '.client_id'` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 1 | AUTH-02 | manual | Open authorize URL in browser, verify GitHub login page | manual-only | ⬜ pending |
| 02-01-06 | 01 | 1 | AUTH-03 | manual | Complete GitHub login, verify redirect with code param | manual-only | ⬜ pending |
| 02-01-07 | 01 | 1 | AUTH-04 | smoke | POST /token with code + code_verifier, expect access_token | ❌ W0 | ⬜ pending |
| 02-01-08 | 01 | 1 | AUTH-05 | smoke | Check token response for refresh_token field | ❌ W0 | ⬜ pending |
| 02-01-09 | 01 | 1 | AUTH-06 | smoke | POST /token with grant_type=refresh_token | ❌ W0 | ⬜ pending |
| 02-01-10 | 01 | 1 | AUTH-07 | integration | Check expires_in field in token response | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | MCP-01 | smoke | POST /mcp with valid token + initialize request | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | MCP-02 | smoke | Check initialize response for tools capability | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 1 | MCP-03 | smoke | POST /mcp with tools/list, check tool names | ❌ W0 | ⬜ pending |
| 02-02-04 | 02 | 1 | MCP-04 | smoke | POST /mcp with tools/call for each tool | ❌ W0 | ⬜ pending |
| 02-02-05 | 02 | 1 | MCP-05 | smoke | POST /mcp without token -> 401 | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 1 | TOOL-01 | smoke | Call read_file via MCP, check response | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 1 | TOOL-02 | smoke | Call write_file then read_file, verify content | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `test-oauth.sh` — smoke tests covering DISC-01 through TOOL-02
- [ ] `.env` file with valid GitHub OAuth credentials — required for any testing
- [ ] Server running locally — `uv run python -m sketchpad.server`

*Wave 0 creates test-oauth.sh during initial plan execution.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GitHub OAuth redirect | AUTH-02 | Requires browser interaction with GitHub login | Open authorize URL in browser, verify redirect to GitHub |
| GitHub callback flow | AUTH-03 | Requires completing GitHub login | Complete GitHub login, verify redirect back with code param |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
