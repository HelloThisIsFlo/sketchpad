# Stack Research

**Domain:** Remote MCP server with OAuth 2.1 (DCR + PKCE), Kubernetes deployment, Cloudflare Tunnel ingress
**Researched:** 2026-03-02
**Confidence:** HIGH (core stack verified via official docs and PyPI; auth proxy pattern verified via FastMCP official docs)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Runtime | FastMCP requires >=3.10; 3.11 is the production-standard baseline in community examples (liatrio reference). 3.13 is fine too — stay on 3.11 for broad image availability. |
| FastMCP | 3.0.2 | MCP server framework + OAuth 2.1 proxy | The canonical Python MCP server library; v1.0 was incorporated into the official MCP Python SDK, then split back out. FastMCP 3.0 (Jan 2026) is the stable production release, downloaded ~1M times/day, powering ~70% of MCP servers. It bundles: Streamable HTTP transport, GitHubProvider (OAuth proxy), JWT issuance, DCR endpoint, /.well-known/ metadata, WWW-Authenticate headers. Eliminates need to hand-roll OAuth 2.1 compliance. |
| Uvicorn | 0.34+ | ASGI server | Official recommendation for FastMCP production deployments. Fastest Python ASGI server (~45K req/s). Used in all FastMCP deployment docs. Run with Gunicorn process manager in production for graceful reloads. |
| uv | latest | Package manager + lock files | 10-100x faster than pip, lock-file based, Rust-native. Now the de-facto standard for new Python projects. Depot/Astral provide official Docker patterns. Use in Dockerfile for reproducible builds. |

### Authentication Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| FastMCP GitHubProvider | (bundled with FastMCP 3.x) | OAuth 2.1 proxy for GitHub | GitHub does NOT support DCR (RFC 7591). GitHubProvider implements the OAuth Proxy pattern: it presents a DCR-compliant interface to Claude AI while using pre-registered GitHub OAuth App credentials upstream. It issues its own JWTs so MCP clients only ever see FastMCP tokens. This is the correct pattern for GitHub as identity provider. |
| PyJWT | 2.11.0 | JWT encode/decode/verify | Bundled dependency of FastMCP. Needed explicitly only if writing custom token validation logic. Use `pyjwt[crypto]` for RS256. python-jose is UNMAINTAINED — do not use it. |
| cryptography | 43+ | Fernet encryption for token storage | Required for `FernetEncryptionWrapper` around storage backends. Ensures OAuth tokens stored in files/Redis are encrypted at rest. Installed as a FastMCP dependency. |

### Storage (for OAuth state persistence)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| py-key-value-aio (FileTreeStore) | latest | File-based OAuth state persistence | Single-pod Kubernetes with PVC: mount PVC at `/var/cache/fastmcp`, use `FileTreeStore` + `FernetEncryptionWrapper`. No Redis sidecar needed. OAuth client registrations and tokens survive pod restarts. Use this for the sketchpad (single pod, simplicity is the goal). |
| py-key-value-aio (RedisStore) | latest | Redis-based OAuth state persistence | Multi-pod / multi-replica deployments only. Requires Redis sidecar. NOT needed for this project. |

### HTTP / ASGI

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Starlette | (bundled with FastMCP) | ASGI routing / middleware | FastMCP's HTTP transport returns a Starlette ASGI app. You can mount custom routes alongside MCP endpoints using standard Starlette patterns. |
| httpx | (bundled dependency) | Async HTTP client | Used internally by FastMCP for upstream OAuth token exchange with GitHub. Not needed directly unless testing the OAuth flow. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Dependency management, virtualenv, lock files | `uv sync`, `uv run`, `uv lock`. Use `pyproject.toml` not `requirements.txt`. |
| pytest + pytest-asyncio | Test runner | `uv run pytest`. FastMCP tools are async — pytest-asyncio handles event loop. |
| Ruff | Linter + formatter | Replaces flake8 + black + isort. From Astral (same team as uv). Single tool. |
| mypy | Type checking | FastMCP is fully typed; catching type errors early prevents OAuth wiring bugs. |
| Docker (multi-stage with uv) | Container image build | Official pattern: copy uv binary from `ghcr.io/astral-sh/uv`, install deps from lockfile in separate layer for cache efficiency. Python 3.11-slim base. |

---

## Installation

```bash
# Initialize project with uv
uv init sketchpad
cd sketchpad

# Core runtime
uv add "fastmcp>=3.0.2"
uv add uvicorn
uv add "py-key-value-aio[file]"   # for FileTreeStore
uv add cryptography                # for FernetEncryptionWrapper

# Dev tooling
uv add --dev pytest pytest-asyncio ruff mypy

# Lock
uv lock
```

---

## Key Configuration Pattern (FastMCP + GitHubProvider)

```python
import os
from fastmcp import FastMCP
from fastmcp.server.auth.providers.github import GitHubProvider
from py_key_value_aio.file import FileTreeStore
from fastmcp.server.auth.storage import FernetEncryptionWrapper
from cryptography.fernet import Fernet

auth = GitHubProvider(
    client_id=os.environ["GITHUB_CLIENT_ID"],
    client_secret=os.environ["GITHUB_CLIENT_SECRET"],
    base_url=os.environ["MCP_BASE_URL"],          # e.g. https://sketchpad.example.com
    jwt_signing_key=os.environ["JWT_SIGNING_KEY"],  # persist across restarts
    client_storage=FernetEncryptionWrapper(
        backend=FileTreeStore(path="/data/oauth-state"),  # on PVC
        fernet=Fernet(os.environ["STORAGE_ENCRYPTION_KEY"]),
    ),
)

mcp = FastMCP(name="sketchpad", auth=auth)
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| FastMCP 3.x | Official `mcp` SDK directly | If you need raw control over the MCP wire protocol or FastMCP's abstraction is too heavy. For this project: FastMCP's GitHubProvider saves ~500 lines of hand-rolled OAuth. |
| FastMCP GitHubProvider | Authlib + hand-rolled OAuth 2.1 server | If GitHub supports DCR (it doesn't). Authlib has all the RFC implementations but requires you to assemble DCR + PKCE + RFC 8414 + RFC 9728 yourself. Not worth it when FastMCP bundles it. |
| FastMCP GitHubProvider | mcp-oauth-gateway (atrawog) | If you need a sidecar proxy that adds OAuth to *any* MCP server without code changes. More ops complexity (Redis required). Useful when you can't modify server code. |
| File storage (FileTreeStore on PVC) | Redis (RedisStore) | Redis only when you need multi-replica horizontal scaling. Single-pod deployment with PVC is simpler and correct for this use case. |
| Uvicorn | Hypercorn | Only if you need HTTP/2 or HTTP/3. For MCP over HTTP/1.1, Uvicorn is faster and simpler. |
| uv | pip + venv | uv is strictly better for new projects. Only use pip if integrating with legacy tooling that can't handle pyproject.toml. |
| Python 3.11 | Python 3.13 | 3.13 works fine with FastMCP. Use 3.13 if you want newest async performance improvements. 3.11 has wider base image availability. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `python-jose` | Unmaintained, known CVEs (CVE-2016-10555 signature bypass when mixing alg types), community explicitly recommends migrating away | `PyJWT` (bundled with FastMCP, actively maintained) |
| SSE transport | Superseded by Streamable HTTP in MCP spec 2025-03-26 and later. Claude AI client prefers Streamable HTTP. | Streamable HTTP (FastMCP default for `transport="http"`) |
| In-memory `client_storage` (Linux default) | On Linux, FastMCP defaults to ephemeral JWT keys and in-memory storage. Pod restart = all OAuth clients must re-register and re-authenticate. Claude AI will prompt the user to re-authorize. | `FileTreeStore` on PVC with `FernetEncryptionWrapper` |
| `mcp` SDK's built-in `OAuthAuthorizationServerProvider` | Pre-2025, the MCP Python SDK tried to be its own auth server. Current spec (2025-06-18) separates resource server from authorization server. The old built-in pattern is architecturally outdated. | FastMCP's GitHubProvider (OAuth proxy to GitHub as AS) |
| Directly proxying GitHub as Authorization Server | GitHub doesn't support DCR (RFC 7591). Claude AI's MCP client requires DCR. The initial OAuth handshake will fail with `client_id` not found. | FastMCP's GitHubProvider, which wraps GitHub in a DCR-compliant proxy layer |
| HostPath volumes for persistence | Ties pod to a specific node. Node failure = data loss. | PersistentVolumeClaim (spec-standard, survives node rescheduling) |

---

## Stack Patterns by Variant

**Single-pod Kubernetes (this project):**
- Use `FileTreeStore` on PVC — no Redis sidecar, no extra service
- Set `replicas: 1` in Deployment
- Session affinity not needed with stateless MCP tools

**Multi-pod / load-balanced (future Obsidian vault server):**
- Use `RedisStore` with FernetEncryptionWrapper
- Enable `stateless_http=True` for stateless tool handlers
- Deploy Redis as a sidecar or cluster service
- Consider sticky sessions if tools maintain in-memory state

**Development / local:**
- Default in-memory storage is fine
- Run with `fastmcp run server.py --transport http --port 8000`
- Use `ngrok` or Cloudflare Tunnel dev mode for Claude AI to reach localhost

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| fastmcp==3.0.2 | Python 3.10–3.13 | Tested on 3.11 and 3.12 in community examples |
| fastmcp==3.0.2 | uvicorn>=0.30 | FastMCP uses standard ASGI interface |
| fastmcp==3.0.2 | mcp spec 2025-03-26, 2025-06-18 | GitHubProvider added in 2.12.0; production storage in 2.13.0; stable in 3.0 |
| PyJWT==2.11.0 | Python 3.9–3.13 | Released 2026-01-30 |
| Authlib==1.6.9 | Python 3.9–3.13 | Released 2026-03-02 (same day as this research). NOT needed if using FastMCP's built-in auth. |

---

## Sources

- [FastMCP PyPI — version 3.0.2, released 2026-02-22](https://pypi.org/project/fastmcp/) — HIGH confidence
- [FastMCP Authentication docs — GitHubProvider, OAuthProxy, TokenVerifier](https://gofastmcp.com/servers/auth/authentication) — HIGH confidence
- [FastMCP GitHub OAuth Integration docs — DCR proxy pattern, setup steps](https://gofastmcp.com/integrations/github) — HIGH confidence
- [FastMCP Storage Backends docs — FileTreeStore, RedisStore, FernetEncryptionWrapper](https://gofastmcp.com/servers/storage-backends) — HIGH confidence
- [FastMCP HTTP Deployment docs — Streamable HTTP, Uvicorn, stateless mode](https://gofastmcp.com/deployment/http) — HIGH confidence
- [FastMCP OAuth Proxy docs — full config options, jwt_signing_key, client_storage](https://gofastmcp.com/servers/auth/oauth-proxy) — HIGH confidence
- [FastMCP 2.13 release blog — storage + security hardening](https://www.jlowin.dev/blog/fastmcp-2-13) — MEDIUM confidence
- [MCP Authorization Specification 2025-06-18 — RFC 9728, RFC 7591, RFC 8414, PKCE](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization) — HIGH confidence (official Anthropic spec)
- [mcp PyPI 1.9.1 — official SDK dependencies, transport support](https://pypi.org/project/mcp/1.9.1/) — HIGH confidence
- [FastMCP DeepWiki OAuth flow — OAuthAuthorizationServerProvider, client-side vs server-side](https://deepwiki.com/modelcontextprotocol/python-sdk/8.3-oauth-authentication-flow) — MEDIUM confidence
- [PyJWT PyPI — version 2.11.0, released 2026-01-30](https://pypi.org/project/PyJWT/) — HIGH confidence
- [Authlib PyPI — version 1.6.9, released 2026-03-02, supports RFC 7591/7636](https://pypi.org/project/Authlib/) — HIGH confidence
- [GitHub — does not support DCR, confirmed by FastMCP docs and multiple sources](https://gofastmcp.com/integrations/github) — HIGH confidence (multiple sources agree)
- [liatrio/fastmcp-github-oauth — reference implementation, Python 3.11+](https://github.com/liatrio/fastmcp-github-oauth) — MEDIUM confidence
- [Horizon/Prefect blog — Why MCP bet on DCR and OAuth proxy necessity](https://horizon.prefect.io/blog/why-mcp-bet-on-dynamic-client-registration) — MEDIUM confidence
- [uv Dockerfile patterns — Depot official guide](https://depot.dev/docs/container-builds/how-to-guides/optimal-dockerfiles/python-uv-dockerfile) — MEDIUM confidence

---

*Stack research for: Remote MCP server (Python) with OAuth 2.1, Kubernetes, Cloudflare Tunnel*
*Researched: 2026-03-02*
