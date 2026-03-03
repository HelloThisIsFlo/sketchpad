---
phase: 1
slug: infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-03
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Shell commands (kubectl, curl, helm) |
| **Config file** | None — infrastructure validation is command-based |
| **Quick run command** | `kubectl get all -n sketchpad` |
| **Full suite command** | See per-requirement commands in Verification Map below |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `kubectl get all -n sketchpad`
- **After every plan wave:** Run full suite of smoke/integration commands
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | INFRA-01 | smoke | `kubectl get deployment sketchpad-placeholder -n sketchpad && kubectl get svc sketchpad -n sketchpad` | N/A (kubectl) | ⬜ pending |
| 1-02-01 | 02 | 1 | INFRA-02 | smoke | `kubectl get pvc sketchpad-data -n sketchpad -o jsonpath='{.status.phase}'` (expect "Bound") | N/A | ⬜ pending |
| 1-02-02 | 02 | 1 | INFRA-03 | smoke | `kubectl get pvc sketchpad-state -n sketchpad -o jsonpath='{.status.phase}'` (expect "Bound") | N/A | ⬜ pending |
| 1-03-01 | 03 | 1 | INFRA-04 | smoke | `kubectl get secret github-oauth encryption-key cloudflared-tunnel-token -n sketchpad` | N/A | ⬜ pending |
| 1-04-01 | 04 | 2 | INFRA-05 | integration | `curl -sf -o /dev/null -w '%{http_code}' https://thehome-sketchpad.kempenich.dev/` (expect "200") | N/A | ⬜ pending |
| 1-05-01 | 05 | 2 | INFRA-06 | smoke | `docker pull ghcr.io/<owner>/sketchpad:latest` or verify push log | N/A | ⬜ pending |
| 1-06-01 | 06 | 1 | DOCS-02 | file-check | `test -f docs/github-oauth-app.md` | ❌ W0 | ⬜ pending |
| 1-06-02 | 06 | 1 | DOCS-03 | file-check | `test -f docs/cloudflare-tunnel.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `docs/github-oauth-app.md` — stubs for DOCS-02
- [ ] `docs/synology-nfs.md` — additional guide per CONTEXT.md decisions
- [ ] `docs/cloudflare-tunnel.md` — stubs for DOCS-03
- [ ] Namespace `sketchpad` must be created first
- [ ] Helm must be available locally (`helm version`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Synology NFS share created with correct permissions | INFRA-02 | Requires Synology DSM UI | Follow `docs/synology-nfs.md`, verify share visible in DSM |
| Cloudflare Tunnel created in dashboard | INFRA-05 | Requires Cloudflare dashboard | Follow `docs/cloudflare-tunnel.md`, verify tunnel shows "Healthy" |
| GitHub OAuth App created | INFRA-04 | Requires GitHub settings UI | Follow `docs/github-oauth-app.md`, verify client ID/secret available |
| ghcr.io package set to Public | INFRA-06 | Requires GitHub Packages UI | After first push, change visibility in Package settings |
| Synology NFS share added to Hyper Backup | N/A | Requires Synology Hyper Backup UI | Open Hyper Backup, add `/volume1/k8s` to existing backup task |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
