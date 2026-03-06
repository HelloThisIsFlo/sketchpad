# Milestones

## v1.0 MVP (Shipped: 2026-03-06)

**Phases:** 4 | **Plans:** 12 | **Timeline:** 4 days (2026-03-02 → 2026-03-06)
**Files modified:** 85 | **Lines of code:** 1,022 Python

**Delivered:** A minimal remote MCP server with OAuth 2.1 authentication, deployed on Kubernetes behind Cloudflare Tunnel, proven end-to-end from Claude AI on phone.

**Key accomplishments:**
1. K8s infrastructure with Cloudflare Tunnel, NFS-backed PVCs, and GitHub Actions CI
2. FastMCP 3.1.0 server with OAuth 2.1 (DCR + PKCE) via GitHubProvider
3. Encrypted OAuth state persistence (FileTreeStore + Fernet) surviving pod restarts
4. Full E2E OAuth handshake confirmed from Claude AI (CLI + phone)
5. Origin validation middleware blocking disallowed Origins on /mcp endpoint
6. Complete documentation suite (5 numbered guides + README index)

**Git range:** initial commit → 42cd142

---

