# Sketchpad

## What This Is

A minimal remote MCP server exposing two tools — read and write a single file. Built in Python with FastMCP 3.1.0, deployed on a home Kubernetes cluster (Talos OS), exposed via Cloudflare Tunnel, and authenticated with OAuth 2.1 (DCR + PKCE) through GitHub. Proves the full Claude AI Integration chain works end-to-end.

## Core Value

OAuth 2.1 authentication (DCR + PKCE) works correctly between Claude AI and my server — if auth works, everything else is trivial.

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

(None — milestone complete. Define new requirements with `/gsd:new-milestone`)

### Out of Scope

- Obsidian vault logic (search, listing, multiple files) — that's the next project
- Cloudflare Tunnel daemon deployment — assumed to already exist on the cluster
- Multi-user support — this is a personal tool, single user
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

---
*Last updated: 2026-03-06 after v1.0 milestone*
