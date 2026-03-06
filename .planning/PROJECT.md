# Sketchpad

## What This Is

A minimal remote MCP server exposing two tools — read and write a single file per user. Built in Python with FastMCP 3.1.0, deployed on a home Kubernetes cluster (Talos OS), exposed via Cloudflare Tunnel, and authenticated with OAuth 2.1 (DCR + PKCE) through GitHub. Each authenticated user gets their own isolated sketchpad.

## Core Value

OAuth 2.1 authentication (DCR + PKCE) works correctly between Claude AI and my server — if auth works, everything else is trivial.

## Current Milestone: v1.1 Multi-Users

**Goal:** Each authenticated user gets their own isolated sketchpad, segregated by OAuth username.

**Target features:**
- Per-user storage isolation (folder per username)
- User identity extraction from OAuth token
- Migrate build tooling from Makefile to Just

## Requirements

### Validated

- ✓ Claude AI discovers the server via MCP metadata endpoints — v1.0
- ✓ OAuth 2.1 flow completes (DCR, PKCE, public client support) — v1.0
- ✓ GitHub used as upstream identity provider — v1.0
- ✓ Claude AI can call read_file tool — v1.0
- ✓ Claude AI can call write_file tool — v1.0
- ✓ Data persists across pod restarts (PVC) — v1.0
- ✓ Server accessible over internet via Cloudflare Tunnel — v1.0
- ✓ Full chain works from Claude AI on phone — v1.0

### Active

- [ ] Per-user sketchpad isolation via OAuth username
- [ ] User identity extraction from OAuth token
- [ ] Makefile → Just migration

### Out of Scope

- Obsidian vault logic (search, listing, multiple files) — that's the next project
- Cloudflare Tunnel daemon deployment — assumed to already exist on the cluster
- Multi-user admin/management — no admin UI, users are self-service via OAuth
- User collaboration/sharing — each user's sketchpad is fully isolated
- Web UI — Claude AI is the only client
- Rate limiting, logging, monitoring — unnecessary for a spike
- Mobile app — Claude AI app is the client
- SSE transport — deprecated; Streamable HTTP is the standard
- Consent UI / approval screen — single-user personal server
- OIDC / OpenID Connect — RFC 8414 metadata is sufficient

## Context

Shipped v1.0 with 1,022 LOC Python across 85 files.
Tech stack: FastMCP 3.1.0, Python, Kubernetes (Talos OS), Cloudflare Tunnel, GitHub OAuth.
OAuth 2.1 chain proven end-to-end from Claude AI on phone and CLI.

**The real goal:** Access an Obsidian vault from Claude AI on a phone. Sketchpad proved the full infrastructure chain works. Swap in vault tools for the next project.

**Known:** GitHub doesn't issue refresh tokens — AUTH-05/AUTH-06 are provider-specific, not server failures.

## Manual Steps (User Must Do)

1. **Create GitHub OAuth App** — GitHub → Settings → Developer settings → OAuth Apps → New. Callback URL: `https://<hostname>/auth/callback`.
2. **Configure Cloudflare Tunnel hostname** — Point subdomain at sketchpad K8s Service.
3. **Test from phone** — Open Claude AI app, add the integration, read/write the sketchpad.

## Testing

- **E2E test script: `test_oauth.py`** — The primary verification tool. Exercises the full real-user flow against a running server + tunnel: OAuth discovery, 401 enforcement, dynamic client registration, browser-based GitHub login, token exchange, refresh, and MCP tool calls (read/write/read-back). Run with `uv run python test_oauth.py`. Always use this for UAT — unit tests (pytest) verify code correctness but miss deployment and integration issues.
- **Unit/integration tests: `uv run pytest`** — 23 tests covering path resolution, sanitization, traversal defense, tool isolation, auth enforcement, and schema safety. These use mocked auth and temp dirs.

## Constraints

- **Auth protocol**: OAuth 2.1 with DCR and PKCE — required by Claude AI
- **Identity provider**: GitHub — simplest for personal use
- **Language**: Python — user preference, good MCP SDK support
- **Deployment**: Kubernetes on Talos OS — existing infrastructure
- **Ingress**: Cloudflare Tunnel — no inbound ports (CGNAT)
- **Persistence**: PersistentVolumeClaim — data must survive pod restarts

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Single-file instead of vault | Isolates OAuth complexity from business logic | ✓ Good — cleanly proved auth chain |
| Python | User preference + good MCP SDK ecosystem | ✓ Good — FastMCP 3.1.0 excellent |
| GitHub as identity provider | Simplest OAuth provider for personal use | ✓ Good — no refresh tokens (minor) |
| PVC for persistence | HostPath too fragile, PVC is K8s-standard | ✓ Good — NFS-backed, survives restarts |
| Cloudflare Tunnel for ingress | Bypasses CGNAT, already used for other services | ✓ Good — zero port forwarding needed |
| OAUTH_PROVIDER env var + factory | Server extensible for future OAuth providers | ✓ Good — clean architecture |
| Named tunnel "TheMac" | Permanent hostname avoids re-configuring callback URL | ✓ Good — themac-sketchpad.kempenich.dev |
| FastMCP 3.1.0 with GitHubProvider | Eliminates hand-rolled OAuth 2.1 (~500 lines saved) | ✓ Good — DCR + RFC 9728 bugs fixed |
| FileTreeStore + Fernet encryption | No Redis sidecar needed for OAuth state persistence | ✓ Good — PVC-backed, encrypted at rest |
| Two separate PVCs | sketchpad-data + sketchpad-state vs shared subPath | ✓ Good — clean separation |
| GitHub Actions CI | Replaces local docker build+push; uses GITHUB_TOKEN | ✓ Good — no PAT needed |
| Origin validation on /mcp only | Discovery, health, OAuth endpoints remain open | ✓ Good — CLIs pass through (no Origin) |
| @mcp.custom_route for /health | Bypasses FastMCP auth for K8s probe | ✓ Good — avoids 401 on liveness checks |
| Username-based user folders | Human-readable, simple. Username rename = new sketchpad (acceptable) | — Pending |
| Fresh start for v1.1 | No migration of v1.0 single-user data | — Pending |

---
*Last updated: 2026-03-06 after v1.1 milestone start*
