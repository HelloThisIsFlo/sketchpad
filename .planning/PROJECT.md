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

---
*Last updated: 2026-03-02 after initialization*
