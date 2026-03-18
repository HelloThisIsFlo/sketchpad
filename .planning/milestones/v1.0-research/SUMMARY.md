# Project Research Summary

**Project:** Sketchpad — Remote MCP Server with OAuth 2.1
**Domain:** Remote MCP server (Python), GitHub OAuth proxy, Kubernetes/Talos, Cloudflare Tunnel
**Researched:** 2026-03-02
**Confidence:** HIGH

## Executive Summary

This project implements a remote MCP server that lets Claude AI read and write a single persistent text file, protected by GitHub-based authentication. The core challenge is not the tools themselves — reading and writing a file is trivial — but the OAuth 2.1 plumbing required for Claude to discover, authenticate with, and call any remote MCP server. Experts build this by leveraging FastMCP's `GitHubProvider`, which acts as an OAuth 2.1 authorization server to Claude while delegating identity verification to GitHub. This OAuth proxy pattern eliminates the need to hand-roll ~500 lines of auth server code and keeps the implementation within 50-100 lines of application code.

The recommended approach is to deploy a single-pod Python service (FastMCP + uvicorn) in a dedicated Kubernetes namespace, with Cloudflare Tunnel as the sole internet ingress path. GitHub OAuth handles identity, FastMCP handles the authorization server (DCR, PKCE, JWT issuance), and a PVC-backed file provides persistence across pod restarts. This is the standard pattern for personal MCP servers on self-hosted Kubernetes and is well-documented in FastMCP's official docs.

The dominant risk is OAuth misconfiguration — specifically, the 10-step OAuth handshake between Claude, the MCP server, and GitHub has multiple failure points that produce silent or misleading errors. Key mitigations: use FastMCP's `GitHubProvider` to avoid rolling custom auth, verify each OAuth endpoint manually with curl before testing with Claude, use Claude Code CLI (not Claude.ai web) as the primary test client, and set up Kubernetes storage correctly before any pod deployment. Every known critical pitfall has a concrete prevention strategy.

## Key Findings

### Recommended Stack

FastMCP 3.0.2 is the correct choice for this project. It is the canonical Python MCP server library (~1M downloads/day, used by ~70% of MCP servers), and critically, it bundles everything needed for OAuth 2.1 compliance: the `GitHubProvider` OAuth proxy, JWT issuance, DCR endpoint, RFC 8414 metadata, and correct WWW-Authenticate headers. Using FastMCP instead of the raw MCP SDK saves substantial implementation effort and avoids the known DCR bugs in the lower-level SDK. The project uses `uv` for package management (10-100x faster than pip, now the Python community standard), with Uvicorn as the ASGI server. For OAuth state persistence, `FileTreeStore` on a Kubernetes PVC with `FernetEncryptionWrapper` is the right choice for a single-pod deployment — no Redis sidecar needed.

**Core technologies:**
- Python 3.11+: Runtime — stable, wide base image availability, FastMCP tested baseline
- FastMCP 3.0.2: MCP framework + OAuth 2.1 proxy — eliminates hand-rolled auth, GitHubProvider is the correct GitHub integration pattern
- uvicorn 0.34+: ASGI server — official FastMCP recommendation, fastest Python ASGI (~45K req/s)
- uv: Package manager — reproducible lock-file builds, Dockerfile-friendly, community standard
- FileTreeStore + FernetEncryptionWrapper: OAuth state persistence — single-pod PVC-backed, encrypted at rest, no Redis

**What NOT to use:** `python-jose` (unmaintained, CVEs), SSE transport (deprecated since MCP spec 2025-03-26), in-memory OAuth storage on Linux (survives only until pod restart), HostPath volumes (node-tied data), direct GitHub-as-authorization-server pattern (GitHub does not support DCR).

### Expected Features

The spec-mandated minimum to make Claude connect is surprisingly large. The OAuth plumbing alone (discovery, DCR, PKCE, token exchange) comprises the majority of the work. The actual file tools are two simple functions.

**Must have (table stakes — Claude cannot connect without these):**
- HTTPS via Cloudflare Tunnel — OAuth 2.1 requires HTTPS; server speaks HTTP internally
- `/.well-known/oauth-authorization-server` (RFC 8414) — Claude discovers auth endpoints here
- `/register` (RFC 7591 DCR) — Claude auto-registers; no pre-configured client_id
- `/authorize` with GitHub redirect — initiates OAuth, stores code_challenge
- `/token` with PKCE verification — exchanges auth code for JWT after PKCE validation
- MCP endpoint POST `/mcp` — handles initialize, tools/list, tools/call with Bearer auth
- `read_file` tool — reads from single PVC-backed file
- `write_file` tool — writes to same file
- Bearer token validation on every MCP request — 401 on missing/invalid token
- PVC for file persistence — survives pod restarts

**Should have (v1.x additions after spike validates):**
- `/.well-known/oauth-protected-resource` (RFC 9728) — becoming mandatory in draft spec
- Refresh tokens — avoid re-auth when tokens expire
- Origin header validation — DNS rebinding protection

**Defer to v2+ (Obsidian vault server):**
- Multiple file tools (list, search, create, delete)
- Scope-based access control (`vault:read`, `vault:write`)
- Session management, stateful sessions
- Multi-user support

**Deliberately exclude:** JWT access tokens (FastMCP handles this; no custom crypto), consent UI (auto-approve for single-user), rate limiting, OIDC, resource subscriptions, SSE server-push.

### Architecture Approach

The system follows three clearly separated concerns: Cloudflare Tunnel provides HTTPS ingress from the internet to the cluster; FastMCP with `GitHubProvider` handles all OAuth 2.1 authorization server duties and MCP protocol; and Kubernetes provides the runtime (PVC for file storage, Secrets for credentials, ClusterIP Service for internal routing). `cloudflared` runs as a separate Deployment (not a sidecar) to allow independent restart and lifecycle from the MCP server pod.

**Major components:**
1. FastMCP server + GitHubProvider — MCP protocol, OAuth 2.1 auth server, JWT issuance, all auto-generated endpoints
2. cloudflared Deployment — outbound Cloudflare Tunnel, routes internet traffic to ClusterIP Service
3. ClusterIP Service + PVC — internal networking and persistent file storage
4. GitHub OAuth App — upstream identity provider (user login only; does NOT speak to Claude directly)
5. Kubernetes Secrets — GitHub client credentials, Cloudflare tunnel token, JWT signing key, storage encryption key

**Build order matters:** StorageClass must exist before PVC; PVC before pod; GitHub OAuth App before Secrets; Secrets before pod; Cloudflare Tunnel before hostname routing; all of the above before end-to-end OAuth testing from Claude.

### Critical Pitfalls

1. **GitHub does not support DCR** — Do not try to use GitHub directly as the authorization server Claude talks to. GitHub only handles user login (the browser redirect). Your server (via FastMCP GitHubProvider) is the authorization server that speaks DCR to Claude. Using `FastMCP(..., auth=GitHubProvider(...))` gets this right automatically. Recovery cost if you build it wrong: HIGH.

2. **about:blank loop in Claude.ai web** — Known Claude-side bug where Claude.ai web opens a blank browser window and the server receives zero requests. Claude Code CLI does not have this bug. Use Claude Code CLI as the primary test client. Only attempt Claude.ai web after CLI works. Do not debug your server for a client-side bug.

3. **Wrong WWW-Authenticate header format** — The 401 response from the MCP endpoint must include `Bearer resource_metadata="https://your-server.com/.well-known/oauth-protected-resource"`. Wrong parameter name (`realm`, `as_uri`, etc.) or wrong URL silently breaks the entire OAuth discovery chain. FastMCP generates this correctly; only matters if writing custom auth.

4. **Talos OS has no default StorageClass** — PVCs pend forever if `local-path-provisioner` is not installed. Must configure with Talos-specific volume path (`/var/mnt/local-path-provisioner`, not `/opt/...` which is read-only). Check `kubectl get storageclass` before creating any PVC.

5. **DCR grant_types validation bug in FastMCP** — FastMCP issue #2460: DCR endpoint may reject `grant_types: ["authorization_code"]` (valid per RFC 7591) and require also `refresh_token`. Verify with a manual curl to `/register` before testing with Claude. Check current FastMCP version against the issue tracker.

## Implications for Roadmap

Based on the dependency graph from ARCHITECTURE.md and the pitfall-to-phase mapping from PITFALLS.md, four phases emerge naturally.

### Phase 1: Infrastructure Prerequisites
**Rationale:** All subsequent phases depend on a working K8s namespace, Secrets, StorageClass, and Cloudflare Tunnel. Pitfall 7 (no StorageClass on Talos) will block Phase 2 if not addressed first. Pitfall 9 (cloudflared parameter ordering) is easier to fix before the MCP server complicates the stack.
**Delivers:** Namespace, Secrets (GitHub OAuth App credentials, Cloudflare tunnel token), StorageClass verified (local-path-provisioner installed if needed), PVC provisioned and bound, cloudflared Deployment running, Cloudflare hostname routing configured, HTTPS public endpoint verified.
**Avoids:** Pitfall 7 (StorageClass), Pitfall 9 (cloudflared crash loop), Pitfall 10 (port 443 requirement).
**Research flag:** None — Cloudflare Tunnel K8s deployment is well-documented.

### Phase 2: MCP Server Core (FastMCP + Tools)
**Rationale:** FastMCP app and tools can be built and tested locally before K8s deployment. Local testing with `fastmcp run` plus ngrok/tunnel catches code bugs before infrastructure complexity enters. The two tool functions are the simplest part; the FastMCP + GitHubProvider wiring is the configuration-level work.
**Delivers:** `main.py` with `FastMCP` + `GitHubProvider` configured, `read_file` and `write_file` tool handlers, local dev testing verified, container image built and pushed to registry, PVC-backed file persistence wired.
**Avoids:** Pitfall 1 (GitHub-as-auth-server misconception — GitHubProvider handles this), Pitfall 12 (SSE transport — FastMCP defaults to Streamable HTTP).
**Research flag:** None — FastMCP GitHubProvider pattern is fully documented with code samples.

### Phase 3: Kubernetes Deployment and OAuth Validation
**Rationale:** Deploy the MCP server to the cluster and verify the full OAuth chain end-to-end. This is the integration phase where most pitfalls surface. Pitfalls 3, 4, 5, and 6 all manifest here and require the "looks done but isn't" checklist from PITFALLS.md. Use curl → MCP Inspector → Claude Code CLI progression.
**Delivers:** MCP server Deployment applied, ClusterIP Service routing to cloudflared, full 10-step OAuth flow completing successfully in Claude Code CLI, `read_file` and `write_file` tools verified callable from Claude.
**Avoids:** Pitfall 2 (about:blank — test with CLI not web), Pitfall 3 (WWW-Authenticate format), Pitfall 4 (DCR grant_types), Pitfall 5 (RFC 9728 path bug), Pitfall 6 (redirect_uri mismatch), Pitfall 8 (Cloudflare TLS confusion), Pitfall 15 (token audience validation).
**Research flag:** This phase has the highest risk. Recommend a checkpoint: verify each OAuth discovery endpoint with curl before attempting Claude integration.

### Phase 4: Hardening (v1.x)
**Rationale:** Once the spike proves the full chain, add robustness without redesign. These are all additive changes; none require architectural rework.
**Delivers:** RFC 9728 `/.well-known/oauth-protected-resource` endpoint (required in draft spec), refresh token support (avoids re-auth after token expiry), persistent OAuth state storage (`FileTreeStore` + `FernetEncryptionWrapper` on PVC) for restart survivability, Origin header validation (DNS rebinding protection).
**Avoids:** Token state loss on pod restart (Pitfall context from STACK.md "Linux defaults to ephemeral keys").
**Research flag:** None — these are incremental additions to known patterns.

### Phase Ordering Rationale

- **Infrastructure first** because the Talos StorageClass issue (Pitfall 7) and Cloudflare Tunnel parameter issue (Pitfall 9) are blockers that are cheaper to resolve before app complexity is added.
- **Server code second** because local development (without K8s) allows faster iteration on FastMCP configuration bugs before networking is involved.
- **Deployment + integration third** because this is where Claude's OAuth client behavior intersects with the server — it must be tested holistically, not in parts.
- **Hardening last** because the spike must validate the architecture before investing in persistence and robustness.

### Research Flags

Phases with standard patterns (skip research-phase):
- **Phase 1 (Infrastructure):** Cloudflare Tunnel K8s deployment is documented with exact manifests. local-path-provisioner for Talos has official docs. No unknowns.
- **Phase 2 (MCP Server):** FastMCP GitHubProvider has official documentation with code samples. Patterns are fully specified.
- **Phase 4 (Hardening):** All additions are documented FastMCP features (FileTreeStore, FernetEncryptionWrapper, RFC 9728).

Phases needing extra verification during execution:
- **Phase 3 (OAuth Validation):** Not a research gap but an integration complexity. The "looks done but isn't" checklist from PITFALLS.md should be used as a phase gate. Multiple known bugs in Claude's client (about:blank, redirect_uri) and FastMCP's DCR validation require hands-on verification with real tokens.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | FastMCP 3.0.2 verified on PyPI; official docs confirm GitHubProvider, FileTreeStore, FernetEncryptionWrapper patterns. All library versions current as of 2026-03-02. |
| Features | HIGH | Based on official MCP spec (2025-03-26 and draft), official Claude support docs, and RFC text. DCR + PKCE requirements confirmed from multiple sources. |
| Architecture | HIGH | Official FastMCP deployment docs, official Cloudflare Tunnel K8s guide, official Talos docs. System diagram verified against component responsibilities. |
| Pitfalls | HIGH | Majority confirmed by official GitHub issues on `anthropics/claude-code`, `jlowin/fastmcp`, `modelcontextprotocol/python-sdk`. Not inference — documented bugs with issue numbers. |

**Overall confidence:** HIGH

### Gaps to Address

- **FastMCP DCR grant_types bug (issue #2460):** Status unknown — may be fixed in latest FastMCP 3.0.2. Verify empirically with curl during Phase 3 rather than assuming it is resolved.
- **Claude.ai web vs CLI parity:** The about:blank bug (issue #11814) was unresolved as of early 2026. Success criteria for Phase 3 should be defined as "works in Claude Code CLI" not "works in Claude.ai web." Web compatibility can be retested after CLI validation.
- **Draft spec adoption timeline:** The MCP draft spec makes RFC 9728 mandatory (currently optional in 2025-03-26). It is unknown when Claude AI will move to the draft spec. Phase 4 (adding RFC 9728 endpoint) is the hedge against this.
- **Talos StorageClass status:** Research cannot confirm whether the home cluster already has local-path-provisioner installed. Phase 1 starts with `kubectl get storageclass` to establish ground truth.

## Sources

### Primary (HIGH confidence)
- FastMCP PyPI 3.0.2 — version, download stats, release date
- FastMCP official docs (gofastmcp.com) — GitHubProvider, FileTreeStore, FernetEncryptionWrapper, OAuth proxy pattern, HTTP deployment
- MCP Authorization Specification 2025-03-26 (modelcontextprotocol.io) — DCR requirement, PKCE requirement, Streamable HTTP transport
- MCP Authorization Specification 2025-06-18 (modelcontextprotocol.io) — RFC 9728 WWW-Authenticate format
- MCP Authorization Specification draft (modelcontextprotocol.io) — RFC 9728 mandatory status, resource server separation
- Claude Support: Building custom connectors via remote MCP servers — Claude.ai integration requirements
- RFC 7591 (DCR), RFC 8414 (AS Metadata), RFC 9728 (Protected Resource Metadata), OAuth 2.1 draft
- PyJWT 2.11.0 (PyPI) — version verification, active maintenance status
- Cloudflare Tunnel Kubernetes deployment guide (developers.cloudflare.com)
- Talos local storage documentation (docs.siderolabs.com)
- GitHub issue: github/github-mcp-server #1404 — GitHub DCR not supported (confirmed)
- GitHub issue: anthropics/claude-code #11814 — about:blank bug (confirmed, unresolved)
- GitHub issue: anthropics/claude-code #10439 — redirect_uri bug
- GitHub issue: jlowin/fastmcp #2460 — DCR grant_types validation bug
- GitHub issue: modelcontextprotocol/python-sdk #1052 — RFC 9728 path bug

### Secondary (MEDIUM confidence)
- liatrio/fastmcp-github-oauth — reference implementation, Python 3.11+
- Horizon/Prefect blog — OAuth proxy necessity rationale
- Depot official guide — uv Dockerfile patterns
- Upstash MCP OAuth implementation guide
- WorkOS MCP Auth developer guide
- FastMCP DeepWiki OAuth flow analysis
- MCP OAuth Gateway (atrawog) — architecture reference
- Azure remote MCP Python OAuth sample — endpoint structure reference

---
*Research completed: 2026-03-02*
*Ready for roadmap: yes*
