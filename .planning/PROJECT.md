# Sketchpad

## What This Is

A minimal remote MCP server exposing two tools -- read and write a single file per user. Built in Python with FastMCP 3.1.0, deployed on a home Kubernetes cluster (Talos OS), exposed via Cloudflare Tunnel, and authenticated with OAuth 2.1 (DCR + PKCE) through GitHub. Each authenticated user gets their own isolated sketchpad with per-user and global storage limits.

## Core Value

OAuth 2.1 authentication (DCR + PKCE) works correctly between Claude AI and my server -- if auth works, everything else is trivial.

## Requirements

### Validated

- v1.0: Claude AI discovers the server via MCP metadata endpoints
- v1.0: OAuth 2.1 flow completes (DCR, PKCE, public client support)
- v1.0: GitHub used as upstream identity provider
- v1.0: Claude AI can call read_file tool
- v1.0: Claude AI can call write_file tool
- v1.0: Data persists across pod restarts (PVC)
- v1.0: Server accessible over internet via Cloudflare Tunnel
- v1.0: Full chain works from Claude AI on phone
- v1.1: Per-user sketchpad isolation via OAuth username (ISOL-01..04)
- v1.1: Per-user (20KB) and global (50MB) storage limits (STOR-01..02)
- v1.1: Justfile replaces Makefile with CI gates (BUILD-01..02)

### Active

<!-- Current scope: v1.2 Tool Polish -->

- [ ] Validate write_file mode parameter against allowed values; change default to "append"
- [ ] Reframe tool descriptions from user-facing notepad to inter-agent persistence layer

### Out of Scope

- Obsidian vault logic (search, listing, multiple files) -- that's the next project
- Cloudflare Tunnel daemon deployment -- assumed to already exist on the cluster
- Multi-user admin/management -- no admin UI, users are self-service via OAuth
- User collaboration/sharing -- each user's sketchpad is fully isolated
- Web UI -- Claude AI is the only client
- Rate limiting, logging, monitoring -- unnecessary for a spike
- Mobile app -- Claude AI app is the client
- SSE transport -- deprecated; Streamable HTTP is the standard
- Consent UI / approval screen -- single-user personal server
- OIDC / OpenID Connect -- RFC 8414 metadata is sufficient
- Identity linking across providers -- provider switch = new sketchpad (accepted)

## Current Milestone: v1.2 Tool Polish

**Goal:** Harden the tool API — validate inputs and clarify tool descriptions for agent consumption.

**Target features:**
- Mode parameter validation with `Literal` type annotation
- Inter-agent persistence framing in tool docstrings

## Context

Shipped v1.1 with 1,816 LOC Python.
Tech stack: FastMCP 3.1.0, Python, Kubernetes (Talos OS), Cloudflare Tunnel, GitHub OAuth, Justfile, Ruff.
35 tests covering path traversal defense, tool isolation, auth enforcement, schema safety, storage limits.
OAuth 2.1 chain proven end-to-end from Claude AI on phone and CLI.

**The real goal:** Access an Obsidian vault from Claude AI on a phone. Sketchpad proved the full infrastructure chain works. Swap in vault tools for the next project.

**Known:** GitHub doesn't issue refresh tokens -- AUTH-05/AUTH-06 are provider-specific, not server failures.
**Known:** NFS subdirectory permissions on Synology NAS need empirical verification during deployment.

## Manual Steps (User Must Do)

1. **Create GitHub OAuth App** -- GitHub -> Settings -> Developer settings -> OAuth Apps -> New. Callback URL: `https://<hostname>/auth/callback`.
2. **Configure Cloudflare Tunnel hostname** -- Point subdomain at sketchpad K8s Service.
3. **Test from phone** -- Open Claude AI app, add the integration, read/write the sketchpad.

## Testing

- **E2E test script: `test_oauth.py`** -- Full real-user flow against running server + tunnel. Run with `uv run python test_oauth.py`.
- **Unit/integration tests: `uv run pytest`** (or `just test`) -- 35 tests covering path resolution, sanitization, traversal defense, tool isolation, auth enforcement, schema safety, storage limits.

## Constraints

- **Auth protocol**: OAuth 2.1 with DCR and PKCE -- required by Claude AI
- **Identity provider**: GitHub -- simplest for personal use
- **Language**: Python -- user preference, good MCP SDK support
- **Deployment**: Kubernetes on Talos OS -- existing infrastructure
- **Ingress**: Cloudflare Tunnel -- no inbound ports (CGNAT)
- **Persistence**: PersistentVolumeClaim -- data must survive pod restarts
- **Build runner**: Just -- replaces Make (v1.1)
- **Linter/formatter**: Ruff -- E4/E7/E9/F/B/I rules (v1.1)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Single-file instead of vault | Isolates OAuth complexity from business logic | Good -- cleanly proved auth chain |
| Python | User preference + good MCP SDK ecosystem | Good -- FastMCP 3.1.0 excellent |
| GitHub as identity provider | Simplest OAuth provider for personal use | Good -- no refresh tokens (minor) |
| PVC for persistence | HostPath too fragile, PVC is K8s-standard | Good -- NFS-backed, survives restarts |
| Cloudflare Tunnel for ingress | Bypasses CGNAT, already used for other services | Good -- zero port forwarding needed |
| OAUTH_PROVIDER env var + factory | Server extensible for future OAuth providers | Good -- clean architecture |
| Named tunnel "TheMac" | Permanent hostname avoids re-configuring callback URL | Good -- sketchpad.kempenich.dev |
| FastMCP 3.1.0 with GitHubProvider | Eliminates hand-rolled OAuth 2.1 (~500 lines saved) | Good -- DCR + RFC 9728 bugs fixed |
| FileTreeStore + Fernet encryption | No Redis sidecar needed for OAuth state persistence | Good -- PVC-backed, encrypted at rest |
| Two separate PVCs | sketchpad-data + sketchpad-state vs shared subPath | Good -- clean separation |
| GitHub Actions CI | Replaces local docker build+push; uses GITHUB_TOKEN | Good -- no PAT needed |
| Origin validation on /mcp only | Discovery, health, OAuth endpoints remain open | Good -- CLIs pass through (no Origin) |
| @mcp.custom_route for /health | Bypasses FastMCP auth for K8s probe | Good -- avoids 401 on liveness checks |
| Username-based user folders | Human-readable, simple. Username rename = new sketchpad | Good -- resolve_user_dir() is injective+idempotent |
| Fresh start for v1.1 | No migration of v1.0 single-user data | Good -- clean slate, no migration complexity |
| No slugify library | GitHub usernames already filesystem-safe | Good -- lowercase + regex sufficient |
| Assert for missing auth | Fail-fast, no fallback to shared storage | Good -- security-critical |
| MAX_STORAGE_USER/GLOBAL | Hard write-time enforcement replaces soft read-time warning | Good -- clean rejection with user-friendly messages |
| Ruff for lint+format | Single tool replaces flake8+isort+black | Good -- fast, configured in pyproject.toml |
| Just replaces Make | Modern command runner with better syntax | Good -- 10 recipes, recipe groups |
| CI test+lint gates | Tests and lint must pass before Docker build | Good -- prevents broken images |

---
*Last updated: 2026-03-18 after v1.2 milestone start*
