# Roadmap: Sketchpad

## Overview

Sketchpad proves the full Claude AI integration chain works before building anything complex. The journey: stand up the Kubernetes infrastructure and Cloudflare Tunnel first (Phase 1), then build and locally validate the FastMCP server with its OAuth 2.1 plumbing and file tools (Phase 2), then deploy to the cluster and walk the full OAuth handshake from Claude AI (Phase 3), then harden the running server with security controls (Phase 4). Every phase delivers something independently verifiable — infrastructure can be curl-tested before any app code exists; the server can be tested locally before K8s enters; OAuth can be validated endpoint by endpoint before Claude AI touches it.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Infrastructure** - Kubernetes namespace, Secrets, StorageClass, PVC, and Cloudflare Tunnel yielding a reachable HTTPS endpoint
- [ ] **Phase 2: MCP Server + OAuth** - FastMCP server with GitHubProvider, OAuth endpoints, file tools — built and validated locally
- [ ] **Phase 3: Deploy + Integration** - Server deployed to cluster and full OAuth handshake confirmed from Claude AI
- [ ] **Phase 4: Hardening** - Origin validation and security controls applied to the running server

## Phase Details

### Phase 1: Infrastructure
**Goal**: A reachable HTTPS public endpoint exists, Kubernetes storage is provisioned and bound, and all secrets are in place — ready to host the MCP server with zero infrastructure surprises
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06, DOCS-02, DOCS-03
**Success Criteria** (what must be TRUE):
  1. `kubectl get storageclass` shows a working StorageClass and `kubectl get pvc` shows the sketchpad PVC as Bound
  2. `kubectl get secret` shows GitHub OAuth App credentials, Cloudflare tunnel token, and any encryption keys present in the target namespace
  3. `curl -I https://<public-hostname>/` returns an HTTP response (any status) — the Cloudflare Tunnel is routing traffic to the cluster
  4. Container image is pushed to a registry and `kubectl` can pull it (confirmed by a test pod or the deployment in Phase 3)
  5. cloudflared Deployment is Running and logs show an active tunnel connection to Cloudflare
  6. `docs/github-oauth-app.md` exists with step-by-step guide for creating the GitHub OAuth App
  7. `docs/cloudflare-tunnel.md` exists with config snippet and hostname setup instructions
**Plans:** 2 plans
Plans:
- [x] 01-01-PLAN.md — Create all K8s manifests, Dockerfile, and documentation guides
- [x] 01-02-PLAN.md — Deploy infrastructure to cluster and verify end-to-end

### Phase 2: MCP Server + OAuth
**Goal**: A locally running FastMCP server correctly implements the full OAuth 2.1 protocol and file tools — every endpoint responds correctly when hit with curl or MCP Inspector before any Kubernetes complexity is involved
**Depends on**: Phase 1 (for GitHub OAuth App credentials used in local dev config)
**Requirements**: DISC-01, DISC-02, DISC-03, AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07, MCP-01, MCP-02, MCP-03, MCP-04, MCP-05, TOOL-01, TOOL-02
**Success Criteria** (what must be TRUE):
  1. `curl http://localhost:8000/.well-known/oauth-authorization-server` returns JSON with `authorization_endpoint`, `token_endpoint`, and `registration_endpoint` fields
  2. `curl http://localhost:8000/.well-known/oauth-protected-resource` returns JSON referencing the authorization server
  3. `curl -X POST http://localhost:8000/mcp` without a token returns HTTP 401 with a `WWW-Authenticate: Bearer resource_metadata=` header
  4. `curl -X POST http://localhost:8000/register` with a valid client metadata body returns a `client_id`
  5. MCP Inspector (or curl) can call `tools/list` with a valid token and receive `read_file` and `write_file` definitions; calling each tool returns the expected file content or confirms a write
**Plans:** 3 plans
Plans:
- [x] 02-01-PLAN.md — Create FastMCP server with GitHubProvider OAuth and file tools
- [x] 02-02-PLAN.md — Dockerfile, test-oauth.sh script, and MCP Inspector guide
- [ ] 02-03-PLAN.md — End-to-end verification via cloudflared tunnel

### Phase 3: Deploy + Integration
**Goal**: The MCP server runs on Kubernetes, is reachable via Cloudflare Tunnel over HTTPS, and Claude AI (via Claude Code CLI) completes the full OAuth handshake and can call both file tools
**Depends on**: Phase 2
**Requirements**: E2E-01, E2E-02, E2E-03, DOCS-01, DOCS-04
**Success Criteria** (what must be TRUE):
  1. Claude Code CLI adds the server as a remote integration and completes the OAuth flow (GitHub login, redirect back, token issued) without errors
  2. Claude AI (via CLI) can call `read_file` and the result appears in the conversation
  3. Claude AI (via CLI) can call `write_file` with new text and a subsequent `read_file` call in the same conversation returns the updated content
  4. After restarting the pod (`kubectl rollout restart deployment/sketchpad`), a new Claude conversation can read the content written in a previous conversation
  5. `docs/` folder exists with index and all guides; `docs/claude-ai-setup.md` covers adding the integration on phone
**Plans**: TBD

### Phase 4: Hardening
**Goal**: The running server rejects malformed or potentially malicious requests — Origin validation is active and all MCP tool calls require a valid token
**Depends on**: Phase 3
**Requirements**: SEC-01, SEC-02
**Success Criteria** (what must be TRUE):
  1. A request to the MCP endpoint with an `Origin` header that does not match the server's configured hostname returns an error (not processed)
  2. A request to any MCP tool endpoint with no `Authorization` header returns HTTP 401, not tool output
  3. A legitimate Claude AI request with a valid token and correct Origin continues to work normally after hardening is applied
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Infrastructure | 2/2 | Complete | 2026-03-04 |
| 2. MCP Server + OAuth | 2/3 | In Progress | - |
| 3. Deploy + Integration | 0/TBD | Not started | - |
| 4. Hardening | 0/TBD | Not started | - |
