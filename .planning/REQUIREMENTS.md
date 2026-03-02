# Requirements: Sketchpad

**Defined:** 2026-03-02
**Core Value:** OAuth 2.1 authentication (DCR + PKCE) works correctly between Claude AI and my server

## v1 Requirements

Requirements for the spike. Each maps to roadmap phases.

### Discovery

- [ ] **DISC-01**: Server exposes `/.well-known/oauth-authorization-server` (RFC 8414) returning authorization, token, and registration endpoint URLs
- [ ] **DISC-02**: Server exposes `/.well-known/oauth-protected-resource` (RFC 9728) returning resource identifier and authorization server reference
- [ ] **DISC-03**: Claude AI can discover the server's auth requirements by hitting the MCP endpoint and receiving a 401 with correct `WWW-Authenticate: Bearer resource_metadata="..."` header

### Authentication

- [ ] **AUTH-01**: Server accepts Dynamic Client Registration (RFC 7591) at `/register` — Claude can self-register and receive a `client_id`
- [ ] **AUTH-02**: Server redirects to GitHub OAuth at `/authorize` with stored `code_challenge` and `state`
- [ ] **AUTH-03**: Server handles GitHub OAuth callback, exchanges GitHub code for GitHub access token, generates own authorization code, and redirects to Claude's callback URL
- [ ] **AUTH-04**: Server exchanges authorization code for access token at `/token` with PKCE verification (`SHA256(code_verifier) == code_challenge`)
- [ ] **AUTH-05**: Server issues refresh tokens alongside access tokens
- [ ] **AUTH-06**: Server accepts `grant_type=refresh_token` at `/token` and issues new access/refresh token pair
- [ ] **AUTH-07**: Access tokens expire after a configured duration (e.g. 1 hour)

### MCP Protocol

- [ ] **MCP-01**: Server accepts MCP requests via Streamable HTTP transport (POST on `/mcp`)
- [ ] **MCP-02**: Server handles `initialize` request and responds with capabilities including `tools`
- [ ] **MCP-03**: Server handles `tools/list` request and returns tool definitions for `read_file` and `write_file`
- [ ] **MCP-04**: Server handles `tools/call` request and dispatches to the correct tool handler
- [ ] **MCP-05**: Server validates Bearer token on every MCP request and returns 401 for missing/invalid tokens

### File Tools

- [ ] **TOOL-01**: `read_file` tool returns the current contents of the sketchpad file
- [ ] **TOOL-02**: `write_file` tool replaces the contents of the sketchpad file with provided text

### Infrastructure

- [ ] **INFRA-01**: Server is deployed as a Kubernetes Deployment with a ClusterIP Service
- [ ] **INFRA-02**: Sketchpad file persists across pod restarts via PersistentVolumeClaim
- [ ] **INFRA-03**: OAuth state (tokens, registrations, auth codes) persists across pod restarts via PVC-backed store
- [ ] **INFRA-04**: GitHub OAuth App credentials and other secrets stored as Kubernetes Secrets
- [ ] **INFRA-05**: Server is accessible over HTTPS via Cloudflare Tunnel
- [ ] **INFRA-06**: Container image is built and pushed to a registry accessible by the cluster

### Security

- [ ] **SEC-01**: Server validates Origin header on incoming requests (DNS rebinding protection)
- [ ] **SEC-02**: Only authenticated requests can access MCP tools (no anonymous tool calls)

### End-to-End

- [ ] **E2E-01**: User can read the sketchpad from Claude AI on their phone
- [ ] **E2E-02**: User can write to the sketchpad from Claude AI on their phone
- [ ] **E2E-03**: Data written in one conversation persists and is readable in a new conversation

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
| DISC-01 | — | Pending |
| DISC-02 | — | Pending |
| DISC-03 | — | Pending |
| AUTH-01 | — | Pending |
| AUTH-02 | — | Pending |
| AUTH-03 | — | Pending |
| AUTH-04 | — | Pending |
| AUTH-05 | — | Pending |
| AUTH-06 | — | Pending |
| AUTH-07 | — | Pending |
| MCP-01 | — | Pending |
| MCP-02 | — | Pending |
| MCP-03 | — | Pending |
| MCP-04 | — | Pending |
| MCP-05 | — | Pending |
| TOOL-01 | — | Pending |
| TOOL-02 | — | Pending |
| INFRA-01 | — | Pending |
| INFRA-02 | — | Pending |
| INFRA-03 | — | Pending |
| INFRA-04 | — | Pending |
| INFRA-05 | — | Pending |
| INFRA-06 | — | Pending |
| SEC-01 | — | Pending |
| SEC-02 | — | Pending |
| E2E-01 | — | Pending |
| E2E-02 | — | Pending |
| E2E-03 | — | Pending |

**Coverage:**
- v1 requirements: 28 total
- Mapped to phases: 0
- Unmapped: 28 (awaiting roadmap)

---
*Requirements defined: 2026-03-02*
*Last updated: 2026-03-02 after initial definition*
