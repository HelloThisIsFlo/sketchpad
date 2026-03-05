# Requirements: Sketchpad

**Defined:** 2026-03-02
**Core Value:** OAuth 2.1 authentication (DCR + PKCE) works correctly between Claude AI and my server

## v1 Requirements

Requirements for the spike. Each maps to roadmap phases.

### Discovery

- [x] **DISC-01**: Server exposes `/.well-known/oauth-authorization-server` (RFC 8414) returning authorization, token, and registration endpoint URLs
- [x] **DISC-02**: Server exposes `/.well-known/oauth-protected-resource` (RFC 9728) returning resource identifier and authorization server reference
- [x] **DISC-03**: Claude AI can discover the server's auth requirements by hitting the MCP endpoint and receiving a 401 with correct `WWW-Authenticate: Bearer resource_metadata="..."` header

### Authentication

- [x] **AUTH-01**: Server accepts Dynamic Client Registration (RFC 7591) at `/register` — Claude can self-register and receive a `client_id`
- [x] **AUTH-02**: Server redirects to GitHub OAuth at `/authorize` with stored `code_challenge` and `state`
- [x] **AUTH-03**: Server handles GitHub OAuth callback, exchanges GitHub code for GitHub access token, generates own authorization code, and redirects to Claude's callback URL
- [x] **AUTH-04**: Server exchanges authorization code for access token at `/token` with PKCE verification (`SHA256(code_verifier) == code_challenge`)
- [x] **AUTH-05**: Server issues refresh tokens alongside access tokens
- [x] **AUTH-06**: Server accepts `grant_type=refresh_token` at `/token` and issues new access/refresh token pair
- [x] **AUTH-07**: Access tokens expire after a configured duration (e.g. 1 hour)

### MCP Protocol

- [x] **MCP-01**: Server accepts MCP requests via Streamable HTTP transport (POST on `/mcp`)
- [x] **MCP-02**: Server handles `initialize` request and responds with capabilities including `tools`
- [x] **MCP-03**: Server handles `tools/list` request and returns tool definitions for `read_file` and `write_file`
- [x] **MCP-04**: Server handles `tools/call` request and dispatches to the correct tool handler
- [x] **MCP-05**: Server validates Bearer token on every MCP request and returns 401 for missing/invalid tokens

### File Tools

- [x] **TOOL-01**: `read_file` tool returns the current contents of the sketchpad file
- [x] **TOOL-02**: `write_file` tool replaces the contents of the sketchpad file with provided text

### Infrastructure

- [x] **INFRA-01**: Server is deployed as a Kubernetes Deployment with a ClusterIP Service
- [x] **INFRA-02**: Sketchpad file persists across pod restarts via PersistentVolumeClaim
- [x] **INFRA-03**: OAuth state (tokens, registrations, auth codes) persists across pod restarts via PVC-backed store
- [x] **INFRA-04**: GitHub OAuth App credentials and other secrets stored as Kubernetes Secrets
- [x] **INFRA-05**: Server is accessible over HTTPS via Cloudflare Tunnel
- [x] **INFRA-06**: Container image is built and pushed to a registry accessible by the cluster

### Security

- [x] **SEC-01**: Server validates Origin header on incoming requests (DNS rebinding protection)
- [x] **SEC-02**: Only authenticated requests can access MCP tools (no anonymous tool calls)

### Documentation

- [x] **DOCS-01**: `docs/` folder exists with an index and step-by-step guides for all manual setup steps
- [x] **DOCS-02**: Guide for creating the GitHub OAuth App (exact URLs, what to enter, what to copy back)
- [x] **DOCS-03**: Guide for configuring Cloudflare Tunnel to point at the sketchpad service (config snippet, hostname setup)
- [x] **DOCS-04**: Guide for adding the server as a Claude AI Integration on phone (exact steps in the app)

### End-to-End

- [x] **E2E-01**: User can read the sketchpad from Claude AI on their phone
- [x] **E2E-02**: User can write to the sketchpad from Claude AI on their phone
- [x] **E2E-03**: Data written in one conversation persists and is readable in a new conversation

## v2 Requirements

Deferred to the Obsidian vault server project.

- **VAULT-01**: Server exposes `list_files` tool to browse vault structure
- **VAULT-02**: Server exposes `search_files` tool with full-text search across vault
- **VAULT-03**: Server exposes `create_file` and `delete_file` tools
- **VAULT-04**: Scope-based access control (`vault:read`, `vault:write`)
- **VAULT-05**: Multi-file read/write operations
- **VAULT-06**: Session management for long vault interactions

## Out of Scope

| Feature | Reason |
|---------|--------|
| Consent UI / approval screen | Single-user personal server — auto-approve all authenticated GitHub users |
| Multi-user support | Personal tool, single owner |
| Web UI | Claude AI is the only client |
| Rate limiting | Unnecessary for personal server behind auth |
| SSE transport (GET /mcp) | Deprecated since MCP spec 2025-03-26; Streamable HTTP is the standard |
| JWT custom implementation | FastMCP handles JWT internally via GitHubProvider |
| OIDC / OpenID Connect | RFC 8414 metadata is sufficient; OIDC adds unnecessary complexity |
| Resource subscriptions | Claude AI does not support them |
| Cloudflare Tunnel daemon deployment | Assumed to exist on cluster; project provides config reference only |
| Mobile app | Claude AI app is the client |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DISC-01 | Phase 2 | Complete |
| DISC-02 | Phase 2 | Complete |
| DISC-03 | Phase 2 | Complete |
| AUTH-01 | Phase 2 | Complete |
| AUTH-02 | Phase 2 | Complete |
| AUTH-03 | Phase 2 | Complete |
| AUTH-04 | Phase 2 | Complete |
| AUTH-05 | Phase 2 | Complete |
| AUTH-06 | Phase 2 | Complete |
| AUTH-07 | Phase 2 | Complete |
| MCP-01 | Phase 2 | Complete |
| MCP-02 | Phase 2 | Complete |
| MCP-03 | Phase 2 | Complete |
| MCP-04 | Phase 2 | Complete |
| MCP-05 | Phase 2 | Complete |
| TOOL-01 | Phase 2 | Complete |
| TOOL-02 | Phase 2 | Complete |
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| INFRA-03 | Phase 1 | Complete |
| INFRA-04 | Phase 1 | Complete |
| INFRA-05 | Phase 1 | Complete |
| INFRA-06 | Phase 1 | Complete |
| SEC-01 | Phase 4 | Complete |
| SEC-02 | Phase 4 | Complete |
| DOCS-01 | Phase 3 | Complete |
| DOCS-02 | Phase 1 | Complete |
| DOCS-03 | Phase 1 | Complete |
| DOCS-04 | Phase 3 | Complete |
| E2E-01 | Phase 3 | Complete |
| E2E-02 | Phase 3 | Complete |
| E2E-03 | Phase 3 | Complete |

**Coverage:**
- v1 requirements: 32 total
- Mapped to phases: 32
- Unmapped: 0

---
*Requirements defined: 2026-03-02*
*Last updated: 2026-03-02 after roadmap creation*
