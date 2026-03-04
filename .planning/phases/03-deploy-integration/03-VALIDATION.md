---
phase: 3
slug: deploy-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-04
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | test_oauth.py (custom E2E script) + Claude Code skill |
| **Config file** | None (script reads .env) |
| **Quick run command** | `uv run python test_oauth.py` |
| **Full suite command** | `uv run python test_oauth.py` + manual Claude Code `/test-sketchpad` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `kubectl get pods -n sketchpad` + `curl -sf https://thehome-sketchpad.kempenich.dev/.well-known/oauth-authorization-server`
- **After every plan wave:** Run `uv run python test_oauth.py` against live URL
- **Before `/gsd:verify-work`:** Full E2E from Claude Code CLI + phone test
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | E2E-01 | manual-only | N/A (phone interaction) | N/A | ⬜ pending |
| 03-01-02 | 01 | 1 | E2E-02 | manual-only | N/A (phone interaction) | N/A | ⬜ pending |
| 03-01-03 | 01 | 1 | E2E-03 | manual + semi-auto | `kubectl rollout restart deployment/sketchpad -n sketchpad` then Claude read | N/A | ⬜ pending |
| 03-02-01 | 02 | 1 | DOCS-01 | smoke | `test -f docs/README.md && ls docs/0[1-5]-*.md \| wc -l` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 1 | DOCS-04 | smoke | `test -f docs/05-claude-ai-setup.md && grep -q "phone" docs/05-claude-ai-setup.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `docs/README.md` — docs index with Quick Start
- [ ] `docs/04-deploy.md` — deployment guide
- [ ] `docs/05-claude-ai-setup.md` — Claude AI setup guide
- [ ] `k8s/deployment.yaml` — real MCP server Deployment
- [ ] `k8s/service.yaml` — updated Service (targetPort 8000)
- [ ] `Makefile` — build/push/deploy workflow
- [ ] `.claude/skills/test-sketchpad/SKILL.md` — test skill
- [ ] Optional: `/health` endpoint in `src/sketchpad/server.py`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Read sketchpad from Claude AI on phone | E2E-01 | Requires human interaction with Claude AI on phone | Open Claude on phone → ask to read a file → verify content appears |
| Write to sketchpad from Claude AI on phone | E2E-02 | Requires human interaction with Claude AI on phone | Open Claude on phone → ask to write text → verify write succeeds |
| Data persists across conversations | E2E-03 | Requires pod restart + new conversation | Restart pod → new conversation → read back previously written content |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
