# Feature Research

**Domain:** Remote MCP server with OAuth 2.1 — single-file read/write, Claude AI Integration
**Researched:** 2026-03-02
**Confidence:** HIGH (official MCP spec + Claude support docs verified)

---

## Feature Landscape

### Table Stakes (Claude AI Won't Connect Without These)

These are the non-negotiable features. Missing any one of them means Claude.ai cannot discover, authenticate, or use the server.

| Feature | Why Required | Complexity | Notes |
|---------|-------------|------------|-------|
| **HTTPS transport** | All OAuth endpoints MUST be served over HTTPS per OAuth 2.1 | LOW | Provided by Cloudflare Tunnel; server itself can speak HTTP internally |
| **Streamable HTTP MCP endpoint** (POST + GET on single URL) | Claude.ai uses Streamable HTTP transport (2025-03-26+). SSE-only is deprecated | MEDIUM | Single URL e.g. `/mcp` handles both POST (send) and GET (SSE stream). Return 405 on GET if not supporting server-push |
| **MCP initialize/initialized handshake** | First interaction MUST be `initialize` request; server MUST respond with capabilities; client sends `initialized` notification | LOW | Declare `tools` capability in initialize response. Protocol version negotiation required |
| **tools/list handler** | Claude discovers tools by calling `tools/list`. Without it there are no tools | LOW | Return array of tool definitions with `name`, `description`, `inputSchema` |
| **tools/call handler** | Claude invokes tools by calling `tools/call`. This is the actual work | LOW | Dispatch by `name`, return `content` array with `type: "text"` items |
| **`read_file` tool** | Core requirement from PROJECT.md | LOW | Returns contents of the single persistent file |
| **`write_file` tool** | Core requirement from PROJECT.md | LOW | Replaces contents of the single persistent file |
| **HTTP 401 on unauthenticated requests** | Claude initiates OAuth flow when it gets 401. Server MUST return 401 when token is absent or invalid | LOW | All MCP endpoints (POST /mcp) return 401 without valid Bearer token |
| **`/.well-known/oauth-authorization-server`** (RFC 8414) | Claude MUST follow RFC 8414 metadata discovery. Server SHOULD implement it; fallback to default paths if absent but discovery is strongly recommended | MEDIUM | JSON document listing `authorization_endpoint`, `token_endpoint`, `registration_endpoint`, `code_challenge_methods_supported: ["S256"]` |
| **`/authorize` endpoint** | Authorization code flow — redirects user to GitHub (or renders consent page). Required for the OAuth dance | HIGH | This is the hard part: must redirect to GitHub, handle callback, issue own auth code. See third-party flow below |
| **`/token` endpoint** | Exchanges authorization code for access token. Must verify PKCE (`code_verifier` vs stored `code_challenge`) | HIGH | Public client (no secret). Must validate `code_verifier` using SHA256. Return `access_token`, `token_type: "bearer"`, `expires_in` |
| **`/register` endpoint** (RFC 7591 DCR) | Claude.ai registers itself dynamically — it has no pre-configured client_id for private servers. Without DCR, Claude cannot obtain a client_id automatically | MEDIUM | Accept `client_name`, `redirect_uris`, `grant_types`, `token_endpoint_auth_method: "none"`. Return `client_id` |
| **PKCE enforcement (S256)** | OAuth 2.1 REQUIRES PKCE for all public clients. Claude sends `code_challenge` and `code_verifier`. Server MUST validate | MEDIUM | Store `code_challenge` at /authorize time. Verify `SHA256(code_verifier) == code_challenge` at /token time |
| **Bearer token validation on MCP endpoint** | Server MUST validate the Bearer token on every request and return 401/403 if invalid | MEDIUM | Token can be opaque (random string stored in memory/DB) or JWT. Opaque is simpler for a spike |
| **Token expiry** | Tokens MUST expire. Short-lived tokens required by spec | LOW | Expiry can be generous (e.g. 1 hour) for spike. Store expiry alongside token |

### Differentiators (Useful But Not Needed for the Spike)

These make the server more robust or correct per the latest spec, but the spike works without them.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **`/.well-known/oauth-protected-resource`** (RFC 9728) | Required in draft spec (not 2025-03-26). Claude.ai supports both. Cleaner discovery path; avoids fallback behavior | MEDIUM | JSON with `resource`, `authorization_servers`, `bearer_methods_supported`. Becomes REQUIRED when Claude moves to draft spec |
| **Refresh tokens** | Allows Claude to silently refresh without re-authenticating. Better UX for long sessions | MEDIUM | Issue alongside access token. Add `/token` grant_type=refresh_token handling |
| **Scope enforcement** | Restrict tools to specific scopes (e.g. `files:read`, `files:write`). Least-privilege principle | LOW | Declare scopes in metadata. Check scope claim on token during tool dispatch |
| **Session management** (`Mcp-Session-Id` header) | Enables stateful MCP sessions. Server can track session state | MEDIUM | Include `Mcp-Session-Id` in initialize response. Reject requests without it with 400 |
| **`notifications/tools/list_changed`** | Notify Claude when tool list changes. Declared via `listChanged: true` in capabilities | LOW | Not needed for static 2-tool server |
| **Origin header validation** | Prevents DNS rebinding attacks. MUST per Streamable HTTP spec | LOW | Check `Origin` header on all incoming connections |
| **Persistent token store (DB)** | Tokens survive server restarts. Eliminates re-auth after pod restart | MEDIUM | For spike, in-memory is acceptable if tokens are short-lived |

### Anti-Features (Deliberately Do NOT Build These)

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **JWT access tokens** | Adds crypto complexity (key generation, signing, verification). Spec does not require JWT — opaque tokens work fine | Use random UUID tokens stored in memory/simple dict with expiry time |
| **Persistent OAuth state (DB)** | Database setup, migration, connection pool — all extra complexity for a spike | In-memory dicts for auth codes, tokens, and client registrations. Accepted tradeoff: re-auth after restart |
| **Multi-user support / user isolation** | PROJECT.md explicitly out of scope. Complicates token-to-user mapping | Single-owner design: any successfully authenticated request is "the user" |
| **Consent UI** | HTML consent page adds frontend work. For personal use with GitHub IdP, auto-approve is fine | Auto-approve authorization for all valid GitHub users (or just hardcode allowed GitHub login) |
| **Rate limiting** | Out of scope per PROJECT.md | Skip entirely |
| **OpenID Connect / OIDC discovery** | Claude supports RFC 8414 metadata. OIDC is an alternative path, not required here | Use RFC 8414 only |
| **`client_credentials` grant** | For machine-to-machine flows. This server is user-facing (human completes GitHub login) | Authorization code flow only |
| **Resource subscriptions** | Claude.ai explicitly does not support resource subscriptions yet | Do not expose `resources` capability |
| **Sampling / elicitations** | Claude.ai does not support these capabilities | Do not declare them in initialize response |
| **`tools/list` pagination** | Two tools. Cursor-based pagination is unnecessary complexity | Return all tools in a single response, no `nextCursor` |
| **SSE server-push (GET /mcp)** | Streamable HTTP GET is optional. Claude does not require server-initiated messages for tool use | Return 405 on GET /mcp, or implement minimal SSE that immediately closes |

---

## Feature Dependencies

```
GitHub OAuth App (client_id + secret)
    └──required by──> /authorize endpoint (redirects to GitHub)
                          └──required by──> /token endpoint (receives GitHub code, issues own token)
                                                └──required by──> Bearer token validation
                                                                      └──required by──> tools/list, tools/call

/.well-known/oauth-authorization-server
    └──enables──> Claude DCR discovery
                      └──required by──> /register endpoint
                                            └──enables──> Claude auto-registration

MCP initialize handshake
    └──required by──> tools/list
                          └──required by──> tools/call
                                                └──splits into──> read_file tool
                                                                   write_file tool

PersistentVolumeClaim (K8s)
    └──required by──> read_file / write_file (data survives pod restarts)

HTTPS (Cloudflare Tunnel)
    └──required by──> all OAuth endpoints (OAuth 2.1 MUST use HTTPS)
    └──required by──> MCP endpoint (Claude.ai only connects to HTTPS)
```

### Dependency Notes

- **GitHub OAuth App required before /authorize**: The authorize endpoint redirects to `https://github.com/login/oauth/authorize`. A GitHub OAuth App (client_id + secret) must be created first. This is a prerequisite to any OAuth testing.
- **DCR required before tool access**: Claude.ai will attempt DCR before the authorization flow. If `/register` is absent and no pre-configured client_id exists, Claude will fail to initiate auth.
- **Token validation required on every MCP call**: The MCP endpoint must check the Bearer token on both `tools/list` and `tools/call`. These cannot be unauthenticated, or Claude can access tools without auth.
- **PVC independent of auth**: File persistence (PVC) is an infrastructure dependency, not an auth dependency. But without it, write_file changes vanish on pod restart.
- **RFC 9728 enhances RFC 8414**: The draft spec requires `/.well-known/oauth-protected-resource` pointing to the auth server. The 2025-03-26 spec (what Claude.ai currently uses) only requires RFC 8414. Implement RFC 8414 first; add RFC 9728 if Claude fails discovery.

---

## MVP Definition

### Launch With (v1 — the spike)

The minimum needed to prove the full chain works:

- [ ] **HTTPS endpoint via Cloudflare Tunnel** — without HTTPS, OAuth is blocked entirely
- [ ] **`/.well-known/oauth-authorization-server`** — Claude discovers auth endpoints from here; fallback exists but discovery is expected
- [ ] **`/register` (DCR)** — Claude auto-registers; without it Claude cannot get a client_id
- [ ] **`/authorize`** — initiates GitHub OAuth, stores code_challenge, redirects user to GitHub
- [ ] **`/token`** — exchanges code for token after PKCE verification, returns opaque access token
- [ ] **MCP endpoint POST `/mcp`** — handles initialize, initialized, tools/list, tools/call with Bearer auth
- [ ] **`read_file` tool** — reads from a single PVC-backed file path
- [ ] **`write_file` tool** — writes to the same file path

### Add After Validation (v1.x)

Once the auth chain is proven to work:

- [ ] **RFC 9728 `/.well-known/oauth-protected-resource`** — add when moving toward spec compliance or if draft spec is adopted by Claude.ai
- [ ] **Refresh tokens** — add once access tokens expire during testing and re-auth becomes annoying
- [ ] **Persistent token store** — add if re-auth on pod restart becomes a problem in daily use
- [ ] **Scope enforcement** — add when expanding to multi-tool servers (Obsidian vault)

### Future Consideration (v2+ — Obsidian vault server)

- [ ] **Multiple file tools** (list_files, search_files, read_file, write_file, create_file, delete_file) — replace sketchpad tools entirely
- [ ] **Scope-based access control** — `vault:read` vs `vault:write`
- [ ] **Session management** — stateful sessions for long vault interactions
- [ ] **Token refresh** — essential for long-running vault sessions

---

## Feature Prioritization Matrix

| Feature | Spike Value | Implementation Cost | Priority |
|---------|-------------|---------------------|----------|
| HTTPS (Cloudflare Tunnel) | HIGH | LOW (infra exists) | P1 |
| `/.well-known/oauth-authorization-server` | HIGH | LOW | P1 |
| `/register` (DCR) | HIGH | LOW | P1 |
| `/authorize` with GitHub redirect | HIGH | HIGH | P1 |
| `/token` with PKCE verification | HIGH | HIGH | P1 |
| MCP endpoint (initialize + tools) | HIGH | MEDIUM | P1 |
| `read_file` + `write_file` tools | HIGH | LOW | P1 |
| Bearer token validation | HIGH | LOW | P1 |
| PVC for file persistence | HIGH | LOW | P1 |
| RFC 9728 protected resource metadata | MEDIUM | LOW | P2 |
| Refresh tokens | MEDIUM | MEDIUM | P2 |
| Persistent token store | LOW | MEDIUM | P3 |
| Scope enforcement | LOW | LOW | P3 |
| Origin header validation | MEDIUM | LOW | P2 |

**Priority key:**
- P1: Must have — spike cannot succeed without it
- P2: Should have — adds robustness/compliance, easy to add
- P3: Nice to have — defer until Obsidian vault server

---

## The Third-Party Auth Flow (Critical Architecture Detail)

This deserves special attention because it is the most complex part and the core risk of the project.

Claude.ai acts as a **public OAuth 2.1 client** (no secret, uses PKCE). The server acts as **both** an OAuth resource server (validates tokens for MCP calls) **and** an OAuth authorization server (issues tokens to Claude). The server itself delegates identity to GitHub.

**Full flow:**

```
1. Claude → POST /mcp (no token) → Server returns 401
2. Claude → GET /.well-known/oauth-authorization-server → Server returns RFC 8414 metadata
3. Claude → POST /register → Server returns client_id (DCR)
4. Claude → opens browser → GET /authorize?client_id=...&code_challenge=...&redirect_uri=https://claude.ai/api/mcp/auth_callback
5. Server → stores {code_challenge, client_id, state} → redirects browser to GitHub OAuth
6. GitHub → user logs in → redirects to Server callback (/github/callback?code=...)
7. Server → exchanges GitHub code for GitHub access token (server-to-server call to GitHub)
8. Server → verifies GitHub user is allowed → generates auth_code → redirects browser to Claude callback
   (https://claude.ai/api/mcp/auth_callback?code=auth_code&state=...)
9. Claude → POST /token?code=auth_code&code_verifier=... → Server verifies PKCE → returns access_token
10. Claude → POST /mcp + Authorization: Bearer access_token → Server validates → returns MCP response
```

**The server must implement two OAuth legs:**
- Leg 1 (server as OAuth client to GitHub): Redirect to GitHub, handle GitHub callback, store GitHub access token
- Leg 2 (server as OAuth server to Claude): Issue auth codes, verify PKCE, issue access tokens

This is the complexity. Everything else (the tools themselves) is trivial by comparison.

---

## Sources

- MCP Authorization Spec (2025-03-26): https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization — HIGH confidence
- MCP Authorization Spec (draft): https://modelcontextprotocol.io/specification/draft/basic/authorization — HIGH confidence
- MCP Transports Spec (2025-06-18): https://modelcontextprotocol.io/specification/2025-06-18/basic/transports — HIGH confidence
- MCP Lifecycle Spec (2025-03-26): https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle — HIGH confidence
- MCP Tools Spec (2025-03-26): https://modelcontextprotocol.io/specification/2025-03-26/server/tools — HIGH confidence
- Claude Support: Building custom connectors via remote MCP servers: https://support.claude.com/en/articles/11503834-building-custom-connectors-via-remote-mcp-servers — HIGH confidence
- MCP Connect Remote Servers: https://modelcontextprotocol.io/docs/develop/connect-remote-servers — HIGH confidence
- Upstash MCP OAuth implementation guide: https://upstash.com/blog/mcp-oauth-implementation — MEDIUM confidence
- WorkOS MCP Auth developer guide: https://workos.com/blog/mcp-auth-developer-guide — MEDIUM confidence
- RFC 8414 (Authorization Server Metadata): https://datatracker.ietf.org/doc/html/rfc8414
- RFC 7591 (Dynamic Client Registration): https://datatracker.ietf.org/doc/html/rfc7591
- RFC 9728 (Protected Resource Metadata): https://datatracker.ietf.org/doc/html/rfc9728
- OAuth 2.1 Draft: https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-12

---
*Feature research for: Remote MCP server with OAuth 2.1 — Claude AI Integration spike*
*Researched: 2026-03-02*
