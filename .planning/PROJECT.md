# Sketchpad

## What This Is

A deliberately minimal remote MCP server that exposes two tools — read and write a single file. Built in Python, deployed on a home Kubernetes cluster (Talos OS), exposed to the internet via Cloudflare Tunnel, and authenticated with OAuth 2.1. It exists to prove the entire Claude AI Integration chain works end-to-end before building a more complex Obsidian vault server.

## Core Value

OAuth 2.1 authentication (DCR + PKCE) works correctly between Claude AI and my server — if auth works, everything else is trivial.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Claude AI can discover the server as an Integration via MCP metadata endpoints
- [ ] OAuth 2.1 flow completes successfully (Dynamic Client Registration, PKCE, public client support)
- [ ] GitHub used as upstream identity provider
- [ ] Claude AI can call a "read" tool that returns the contents of a single persistent file
- [ ] Claude AI can call a "write" tool that updates the contents of that file
- [ ] Data persists across server pod restarts (PersistentVolumeClaim)
- [ ] Server is accessible over the internet via Cloudflare Tunnel
- [ ] The full chain works from Claude AI on a phone

### Out of Scope

- Obsidian vault logic (search, listing, multiple files) — that's the next project
- Cloudflare Tunnel daemon deployment — assumed to already exist on the cluster
- Multi-user support — this is a personal tool, single user
- Web UI — Claude AI is the only client
- Rate limiting, logging, monitoring — unnecessary for a spike
- Mobile app — Claude AI app is the client

## Context

**The real goal:** Access an Obsidian vault (folder of Markdown files) from Claude AI on a phone. That requires a remote MCP server with OAuth, internet exposure, and K8s deployment. Too many unknowns at once.

**Sketchpad's role:** Isolate and debug the OAuth flow with the simplest possible server. If read/write of a single file works from Claude AI, the entire infrastructure chain is proven. Swap in vault tools later.

**OAuth is the risk:** Claude AI requires OAuth 2.1 with Dynamic Client Registration (DCR) and PKCE. The interaction between Claude's OAuth client and the server is a black box. Error messages are often cryptic. This is why the business logic is deliberately trivial — any failure is an auth/infrastructure problem, not a logic problem.

**Kubernetes environment:** Talos OS cluster at home, behind residential ISP (likely CGNAT). Cloudflare Tunnel provides internet ingress. Flo has tunnel experience from other services but hasn't configured one for this project yet.

**K8s experience level:** Beginner. Manifests should be explicit and well-commented. May need to check/create a StorageClass for PVC.

**Execution environment:** `kubectl` on this machine talks to the Talos cluster. Container images go to GitHub Container Registry (ghcr.io) as a public repo. Claude can apply manifests, create secrets, build/push images directly. **Namespace constraint:** Stay in a dedicated namespace (e.g. `sketchpad`). Don't touch anything outside it. If things break, user deletes the namespace and starts over.

**Autonomy preference:** Make standard decisions autonomously. User doesn't want to make choices — just the most standard, boring approach that works. Only pause for things that physically require the user (GitHub OAuth App creation, Cloudflare dashboard config, phone testing).

## Manual Steps (User Must Do)

1. **Create GitHub OAuth App** — GitHub → Settings → Developer settings → OAuth Apps → New. Set callback URL to `https://<hostname>/github/callback`. Provide `client_id` and `client_secret` back.
2. **Configure Cloudflare Tunnel hostname** — Point a subdomain (e.g. `sketchpad.yourdomain.com`) at the sketchpad K8s Service. Instructions provided in Phase 1.
3. **Test from phone** — Open Claude AI app, add the integration, read/write the sketchpad.

## Constraints

- **Auth protocol**: OAuth 2.1 with DCR and PKCE — required by Claude AI's Integration protocol
- **Identity provider**: GitHub — simplest option for a personal tool
- **Language**: Python — user preference, good MCP SDK support
- **Deployment**: Kubernetes on Talos OS — existing infrastructure
- **Ingress**: Cloudflare Tunnel — no inbound ports available (CGNAT)
- **Persistence**: PersistentVolumeClaim — data must survive pod restarts

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Single-file instead of vault | Isolates OAuth complexity from business logic | — Pending |
| Python | User preference + good MCP SDK ecosystem | — Pending |
| GitHub as identity provider | Simplest OAuth provider for personal use | — Pending |
| PVC for persistence | HostPath too fragile, PVC is K8s-standard | — Pending |
| Cloudflare Tunnel for ingress | Bypasses CGNAT, already used for other services | — Pending |
| OAUTH_PROVIDER env var + factory | Makes server extensible for future OAuth providers (only GitHub now) | Implemented in Phase 2 parallel session |
| test-oauth.sh → test_oauth.py | Bash couldn't handle SSE from Streamable HTTP; Python httpx handles it | Implemented in Phase 2 parallel session |
| Named tunnel "TheMac" | Permanent hostname avoids re-configuring GitHub callback URL each session | themac-sketchpad.kempenich.dev |
| GitHub refresh tokens: N/A | GitHub doesn't issue refresh tokens; AUTH-05/AUTH-06 are provider-specific | Documented as SKIP in test, not failure |

---
*Last updated: 2026-03-04 after Phase 2 verification*
