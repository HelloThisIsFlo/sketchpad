# Phase 2: MCP Server + OAuth - Research

**Researched:** 2026-03-04
**Domain:** FastMCP OAuth 2.1 with GitHub identity provider, MCP Streamable HTTP transport, Python server development
**Confidence:** HIGH

## Summary

FastMCP 3.x (latest 3.1.0, released 2026-03-03) provides a turnkey `GitHubProvider` class that wraps the full OAuth 2.1 proxy pattern -- DCR, PKCE, JWT issuance, token storage, and all discovery endpoints. The server code is minimal: instantiate `GitHubProvider` with credentials and `base_url`, pass it to `FastMCP(auth=...)`, register tools, and call `mcp.run(transport="http")`. FastMCP automatically serves `/.well-known/oauth-authorization-server`, `/.well-known/oauth-protected-resource`, `/register`, `/authorize`, `/token`, `/auth/callback`, and the MCP endpoint at `/mcp`. For persistence, `FileTreeStore` wrapped in `FernetEncryptionWrapper` survives pod restarts using the PVC already provisioned in Phase 1 -- no Redis required.

Two previously-tracked bugs are now resolved: the DCR `grant_types` bug (issue #2460, closed 2026-02-06 -- the upstream Python SDK fix was merged) and the RFC 9728 `/.well-known/oauth-protected-resource` path bug (issue #1400, closed 2025-10-06 -- fixed in MCP Python SDK). Both fixes are included in current FastMCP 3.x releases. The project decision to use FastMCP 3.0.2 should be updated to target the latest 3.1.0 (or at minimum >=3.0.2) to include all fixes.

**Primary recommendation:** Use `uv` for project setup with `pyproject.toml`, FastMCP 3.1.0 with `GitHubProvider`, `FileTreeStore` + `FernetEncryptionWrapper` for OAuth state, and `mcp.run(transport="http", host="0.0.0.0", port=8000)` for the server entry point. The Dockerfile replaces the Phase 1 placeholder with a uv-based multi-stage build.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use `cloudflared tunnel --url http://localhost:8000` for ephemeral quick tunnels during dev -- random `*.trycloudflare.com` URL, zero dashboard config, zero stale state
- Update GitHub OAuth App callback URL each dev session with the new tunnel URL (acceptable friction)
- Primary test client: runnable `test-oauth.sh` script that exercises the full OAuth flow end-to-end (discovery -> register -> authorize -> token -> MCP tool calls) with clear output and comments at each step
- Secondary test tool: MCP Inspector as a guided exploration bonus -- include a section in docs with "fun things to try" so the user can learn the tool. Not a requirement, a learning opportunity
- Claude Code CLI remains the primary integration test client (Claude.ai web has known `about:blank` bug per issue #11814)
- Welcome message on first read (file doesn't exist yet) -- something like "Welcome to Sketchpad! Write something here."
- write_file supports both replace (default) and append modes via a `mode` parameter
- Content is plain text with zero validation -- tool description nudges the agent toward Markdown but accepts anything
- Soft size limit on the file to protect context windows -- Claude picks the exact threshold (something reasonable for a sketchpad, not a novel). Read response includes a warning if exceeded, not a hard block
- Edge cases (concurrent writes, etc.) throw errors -- deferred to future milestone
- Minimal Python package layout (not a single file) -- separate files for server wiring, tools, config for navigability
- `uv` for dependency management (`uv init`, `uv add fastmcp`, `uv run`)
- Dockerfile included in Phase 2 alongside the code -- test containerized version locally before K8s in Phase 3
- `.env` file in project root (gitignored) for local dev -- `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `SERVER_URL`, encryption key, etc.
- `.env.example` committed with placeholder values -- makes required config discoverable
- Server reads `.env` on startup

### Claude's Discretion
- Server URL handling for changing tunnel URLs (CLI arg override, .env update, or other approach -- minimize friction)
- Soft size limit threshold for the sketchpad file
- Exact package layout (file names, module organization within the minimal package pattern)
- MCP Inspector "things to try" content
- Welcome message exact wording
- test-oauth.sh script structure and error handling

### Deferred Ideas (OUT OF SCOPE)
- Concurrent write handling / race conditions -- future milestone
- File versioning or history -- out of scope, belongs in Obsidian vault project
- Multiple files -- that's literally the Obsidian vault project

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DISC-01 | Server exposes `/.well-known/oauth-authorization-server` (RFC 8414) | FastMCP GitHubProvider auto-registers this endpoint; returns authorization, token, registration URLs |
| DISC-02 | Server exposes `/.well-known/oauth-protected-resource` (RFC 9728) | FastMCP auto-registers this; RFC 9728 path bug fixed in MCP SDK (issue #1400, merged 2025-10) |
| DISC-03 | 401 with `WWW-Authenticate: Bearer resource_metadata=` header on unauthenticated MCP request | FastMCP returns this automatically when auth provider is configured |
| AUTH-01 | DCR at `/register` -- Claude can self-register and receive `client_id` | GitHubProvider/OAuthProxy handles DCR; grant_types bug fixed (issue #2460, closed 2026-02) |
| AUTH-02 | Server redirects to GitHub OAuth at `/authorize` with stored `code_challenge` and `state` | OAuthProxy generates its own PKCE for upstream, stores state in transaction store |
| AUTH-03 | Server handles GitHub callback, exchanges code, generates own auth code, redirects to Claude's callback | OAuthProxy callback forwarding pattern: proxy callback -> exchange with GitHub -> new code -> client redirect |
| AUTH-04 | Token exchange at `/token` with PKCE verification | OAuthProxy separately validates client PKCE params, issues FastMCP JWT |
| AUTH-05 | Server issues refresh tokens alongside access tokens | OAuthProxy JWT token factory issues both access + refresh tokens |
| AUTH-06 | Server accepts `grant_type=refresh_token` at `/token` | OAuthProxy maps refresh tokens to upstream refresh tokens |
| AUTH-07 | Access tokens expire after configured duration | FastMCP JWT tokens include expiration; configurable |
| MCP-01 | Streamable HTTP transport (POST on `/mcp`) | `mcp.run(transport="http")` serves at `/mcp` endpoint |
| MCP-02 | `initialize` request returns capabilities including `tools` | FastMCP handles initialize automatically |
| MCP-03 | `tools/list` returns `read_file` and `write_file` definitions | Register tools with `@mcp.tool` decorator |
| MCP-04 | `tools/call` dispatches to correct tool handler | FastMCP dispatch built-in |
| MCP-05 | Bearer token validation on every MCP request, 401 for invalid | Auth provider validates JWT on every request automatically |
| TOOL-01 | `read_file` returns sketchpad file contents | Implement with `@mcp.tool`, read from PVC-mounted path |
| TOOL-02 | `write_file` replaces sketchpad file contents | Implement with `@mcp.tool`, write to PVC-mounted path |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastmcp | >=3.0.2 (target 3.1.0) | MCP server framework with OAuth proxy | Official Python MCP server framework; GitHubProvider handles entire OAuth 2.1 flow |
| cryptography | latest | Fernet encryption for OAuth state at rest | Required by FernetEncryptionWrapper; FastMCP dependency |
| py-key-value-aio[disk] | (FastMCP dependency) | FileTreeStore for persistent OAuth state | Bundled with FastMCP; provides file-system KV store |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | latest | Load `.env` file for local dev | FastMCP auto-loads `.env` files on import (uses python-dotenv internally); explicit `load_dotenv()` call NOT needed |
| uvicorn | latest | ASGI server (for Docker/production) | Use `mcp.run()` for dev; `uvicorn app:http_app` for production Dockerfile |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FileTreeStore | RedisStore | Redis requires a sidecar; FileTreeStore + PVC is simpler for single-pod |
| `mcp.run()` | `uvicorn` CLI | `mcp.run()` is simpler for dev; uvicorn gives more control in production |
| FastMCP GitHubProvider | Hand-rolled OAuth 2.1 | ~500 lines saved; GitHubProvider handles DCR, PKCE, JWT, token storage |

### Installation (using uv)
```bash
uv init
uv add "fastmcp>=3.0.2"
uv add python-dotenv  # likely redundant -- FastMCP auto-loads .env
```

Note: `cryptography` and `py-key-value-aio[disk]` are pulled in transitively by FastMCP. No need to add them explicitly.

## Architecture Patterns

### Recommended Project Structure
```
src/
  sketchpad/
    __init__.py          # Empty or minimal
    server.py            # FastMCP instance, auth config, mcp.run()
    tools.py             # read_file and write_file tool definitions
    config.py            # Environment loading, constants (paths, limits)
pyproject.toml           # uv project config
uv.lock                  # Lockfile (committed)
Dockerfile               # Multi-stage uv build (replaces Phase 1 placeholder)
.env                     # Local dev secrets (gitignored)
.env.example             # Placeholder values (committed)
test-oauth.sh            # End-to-end OAuth flow test script
docs/
  mcp-inspector.md       # "Fun things to try" guide
```

### Pattern 1: GitHubProvider with FileTreeStore
**What:** Configure FastMCP's GitHubProvider with persistent encrypted storage on the filesystem.
**When to use:** Single-pod deployment with PVC-backed storage (our exact case).
**Example:**
```python
# Source: https://gofastmcp.com/integrations/github + https://gofastmcp.com/servers/storage-backends
import os
from pathlib import Path
from fastmcp import FastMCP
from fastmcp.server.auth.providers.github import GitHubProvider
from key_value.aio.stores.filetree import (
    FileTreeStore,
    FileTreeV1KeySanitizationStrategy,
    FileTreeV1CollectionSanitizationStrategy,
)
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from cryptography.fernet import Fernet

# Storage directory -- maps to PVC mount in K8s, local dir in dev
state_dir = Path(os.environ.get("STATE_DIR", "./state"))
state_dir.mkdir(parents=True, exist_ok=True)

store = FileTreeStore(
    data_directory=state_dir,
    key_sanitization_strategy=FileTreeV1KeySanitizationStrategy(state_dir),
    collection_sanitization_strategy=FileTreeV1CollectionSanitizationStrategy(state_dir),
)

encrypted_store = FernetEncryptionWrapper(
    key_value=store,
    fernet=Fernet(os.environ["STORAGE_ENCRYPTION_KEY"]),
)

auth = GitHubProvider(
    client_id=os.environ["GITHUB_CLIENT_ID"],
    client_secret=os.environ["GITHUB_CLIENT_SECRET"],
    base_url=os.environ.get("SERVER_URL", "http://localhost:8000"),
    jwt_signing_key=os.environ["JWT_SIGNING_KEY"],
    client_storage=encrypted_store,
)

mcp = FastMCP(name="Sketchpad", auth=auth)
```

### Pattern 2: Tool Registration with @mcp.tool
**What:** Register MCP tools as decorated async functions.
**When to use:** Defining `read_file` and `write_file`.
**Example:**
```python
# Source: https://gofastmcp.com/getting-started/quickstart
from pathlib import Path

SKETCHPAD_PATH = Path(os.environ.get("DATA_DIR", "./data")) / "sketchpad.md"
WELCOME_MESSAGE = "Welcome to Sketchpad! Write something here."
SIZE_LIMIT = 50_000  # ~50KB soft limit

@mcp.tool
def read_file() -> str:
    """Read the sketchpad file. This is a single shared Markdown file
    for jotting down notes, ideas, and drafts."""
    if not SKETCHPAD_PATH.exists():
        return WELCOME_MESSAGE
    content = SKETCHPAD_PATH.read_text(encoding="utf-8")
    if len(content) > SIZE_LIMIT:
        return content + "\n\n---\n[WARNING: File exceeds recommended size. Consider trimming.]"
    return content

@mcp.tool
def write_file(content: str, mode: str = "replace") -> str:
    """Write to the sketchpad file. Use this for notes, drafts, ideas --
    Markdown formatting recommended but not required.

    Args:
        content: The text to write.
        mode: "replace" (default) overwrites the file; "append" adds to the end.
    """
    SKETCHPAD_PATH.parent.mkdir(parents=True, exist_ok=True)
    if mode == "append":
        existing = SKETCHPAD_PATH.read_text(encoding="utf-8") if SKETCHPAD_PATH.exists() else ""
        SKETCHPAD_PATH.write_text(existing + content, encoding="utf-8")
    else:
        SKETCHPAD_PATH.write_text(content, encoding="utf-8")
    return f"File updated ({mode} mode). Size: {SKETCHPAD_PATH.stat().st_size} bytes."
```

### Pattern 3: Server Entry Point
**What:** Run the FastMCP server with HTTP transport.
**When to use:** The `if __name__` block or the Docker CMD.
**Example:**
```python
# Source: https://gofastmcp.com/deployment/running-server
if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8000,
    )
```

### Pattern 4: SERVER_URL Override for Quick Tunnels
**What:** Allow SERVER_URL to be passed as env var or CLI arg so changing tunnel URLs is easy.
**When to use:** Each dev session with cloudflared quick tunnel gives a different URL.
**Recommended approach:** Read `SERVER_URL` from environment. Developer updates `.env` or passes it directly:
```bash
# Option A: Update .env and restart
echo "SERVER_URL=https://random-words.trycloudflare.com" >> .env
uv run python -m sketchpad.server

# Option B: Override inline
SERVER_URL=https://random-words.trycloudflare.com uv run python -m sketchpad.server
```

### Anti-Patterns to Avoid
- **Hand-rolling OAuth endpoints:** FastMCP handles `/register`, `/authorize`, `/token`, `/auth/callback`, and all `.well-known` endpoints. Never build these manually.
- **Passing upstream tokens to clients:** The OAuthProxy issues its own JWTs. Clients never see GitHub tokens. This is correct and intentional.
- **Using `mcp.run()` in Docker:** Use `uvicorn` directly in production Dockerfiles for better control. `mcp.run()` is fine for local dev.
- **In-memory storage in production:** Default storage is in-memory on Linux. Always configure `FileTreeStore` + `FernetEncryptionWrapper` explicitly.
- **Forgetting `jwt_signing_key`:** Without it, JWT signing keys are ephemeral on Linux -- tokens invalidate on restart.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth 2.1 endpoints | Custom `/authorize`, `/token`, `/register` | `GitHubProvider` | ~500 lines, 6 RFCs, security-critical edge cases |
| Discovery metadata | Custom `.well-known` JSON responses | FastMCP auto-registration | RFC 8414 + RFC 9728 compliance handled |
| DCR registration | Custom client registration logic | OAuthProxy DCR handler | Handles grant_types, redirect URIs, client storage |
| PKCE verification | Custom SHA-256 code challenge verification | OAuthProxy PKCE handling | Dual PKCE (client-to-proxy and proxy-to-GitHub) |
| JWT token issuance | Custom JWT creation and verification | OAuthProxy token factory | Signing, expiration, JTI mapping, refresh tokens |
| Token encryption at rest | Custom encryption for stored tokens | `FernetEncryptionWrapper` | AES-128-CBC + HMAC-SHA256, proper key management |
| .env loading | Custom file parsing | FastMCP auto-loads `.env` | Already built into FastMCP import; uses python-dotenv |

**Key insight:** The entire OAuth 2.1 stack -- discovery, DCR, PKCE, token issuance, token storage, token verification -- is handled by FastMCP's `GitHubProvider` + `OAuthProxy`. The only custom code needed is tool definitions and configuration.

## Common Pitfalls

### Pitfall 1: GitHub OAuth App Callback URL Mismatch
**What goes wrong:** Authorization fails with "redirect_uri mismatch" error from GitHub.
**Why it happens:** The callback URL in the GitHub OAuth App settings must exactly match `{SERVER_URL}/auth/callback`. With cloudflared quick tunnels, the URL changes every session.
**How to avoid:** Document the update step clearly. Each dev session: (1) start cloudflared, (2) copy the URL, (3) update GitHub OAuth App callback to `{tunnel_url}/auth/callback`, (4) update `SERVER_URL` in `.env`.
**Warning signs:** HTTP 400 from GitHub during the authorization redirect.

### Pitfall 2: Missing jwt_signing_key in Production
**What goes wrong:** Tokens become invalid after server restart.
**Why it happens:** On Linux (and Docker), without `jwt_signing_key`, FastMCP generates an ephemeral key on startup. After restart, old JWTs fail validation.
**How to avoid:** Always set `JWT_SIGNING_KEY` environment variable. Any secret string works -- FastMCP derives a 32-byte key via HKDF internally.
**Warning signs:** All clients get 401 after server restart; re-authentication required.

### Pitfall 3: Missing STORAGE_ENCRYPTION_KEY
**What goes wrong:** Encrypted state files are unreadable after restart (wrong key).
**Why it happens:** If the Fernet key is not persisted between restarts, a new key is generated and old encrypted data is unreadable.
**How to avoid:** Generate once with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` and store in `.env` / K8s Secret.
**Warning signs:** `InvalidToken` errors when reading stored OAuth state.

### Pitfall 4: Forgetting to Bind to 0.0.0.0 in Docker
**What goes wrong:** Container starts but is unreachable from outside.
**Why it happens:** Default `host="127.0.0.1"` only accepts connections from inside the container.
**How to avoid:** Use `host="0.0.0.0"` in both `mcp.run()` and Dockerfile CMD.
**Warning signs:** Connection refused from K8s Service or `docker run -p` mapping.

### Pitfall 5: FastMCP Auto-Loading .env with Bad Syntax
**What goes wrong:** Import error on `import fastmcp` if `.env` has non-python-dotenv syntax.
**Why it happens:** FastMCP auto-parses `.env` on import using python-dotenv. Non-standard syntax causes parse errors.
**How to avoid:** Keep `.env` strictly in `KEY=value` format. No shell expansions, no multiline without quotes. Or set `FASTMCP_ENV_FILE` to point to a specific file.
**Warning signs:** `ValueError` or `ParsingError` on first import of fastmcp.

### Pitfall 6: Stateless Mode Not Needed for Single Pod
**What goes wrong:** Unnecessary complexity if you enable `stateless_http=True`.
**Why it happens:** Multi-worker/multi-pod docs suggest stateless mode, but for single-pod with one worker, stateful mode (default) is correct and simpler.
**How to avoid:** Use default stateful mode. Only consider stateless if scaling horizontally later.
**Warning signs:** Sessions not persisting between requests (if accidentally enabled).

## Code Examples

### Complete Server Configuration
```python
# Source: https://gofastmcp.com/integrations/github
# src/sketchpad/server.py
import os
from pathlib import Path
from fastmcp import FastMCP
from fastmcp.server.auth.providers.github import GitHubProvider
from key_value.aio.stores.filetree import (
    FileTreeStore,
    FileTreeV1KeySanitizationStrategy,
    FileTreeV1CollectionSanitizationStrategy,
)
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from cryptography.fernet import Fernet

from sketchpad.config import (
    GITHUB_CLIENT_ID,
    GITHUB_CLIENT_SECRET,
    SERVER_URL,
    JWT_SIGNING_KEY,
    STORAGE_ENCRYPTION_KEY,
    STATE_DIR,
)
from sketchpad.tools import register_tools

# Persistent encrypted storage for OAuth state
state_dir = Path(STATE_DIR)
state_dir.mkdir(parents=True, exist_ok=True)

store = FileTreeStore(
    data_directory=state_dir,
    key_sanitization_strategy=FileTreeV1KeySanitizationStrategy(state_dir),
    collection_sanitization_strategy=FileTreeV1CollectionSanitizationStrategy(state_dir),
)
encrypted_store = FernetEncryptionWrapper(
    key_value=store,
    fernet=Fernet(STORAGE_ENCRYPTION_KEY),
)

# GitHub OAuth provider -- handles all OAuth 2.1 endpoints
auth = GitHubProvider(
    client_id=GITHUB_CLIENT_ID,
    client_secret=GITHUB_CLIENT_SECRET,
    base_url=SERVER_URL,
    jwt_signing_key=JWT_SIGNING_KEY,
    client_storage=encrypted_store,
)

mcp = FastMCP(name="Sketchpad", auth=auth)
register_tools(mcp)

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
```

### Config Module
```python
# src/sketchpad/config.py
import os

# Required -- no defaults, fail fast if missing
GITHUB_CLIENT_ID = os.environ["GITHUB_CLIENT_ID"]
GITHUB_CLIENT_SECRET = os.environ["GITHUB_CLIENT_SECRET"]
JWT_SIGNING_KEY = os.environ["JWT_SIGNING_KEY"]
STORAGE_ENCRYPTION_KEY = os.environ["STORAGE_ENCRYPTION_KEY"]

# Configurable with sensible defaults
SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:8000")
DATA_DIR = os.environ.get("DATA_DIR", "./data")
STATE_DIR = os.environ.get("STATE_DIR", "./state")
SKETCHPAD_FILENAME = "sketchpad.md"
SIZE_LIMIT = 50_000  # ~50KB soft limit -- protects context windows
```

### .env.example
```bash
# GitHub OAuth App credentials (from https://github.com/settings/developers)
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# Server URL -- update with cloudflared tunnel URL each dev session
# For local dev: http://localhost:8000
# For tunnel: https://random-words.trycloudflare.com
SERVER_URL=http://localhost:8000

# JWT signing key -- any secret string, FastMCP derives 32-byte key via HKDF
# Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SIGNING_KEY=change-me-to-a-random-string

# Fernet encryption key for OAuth state at rest
# Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
STORAGE_ENCRYPTION_KEY=change-me-to-a-fernet-key

# Paths for data and OAuth state (defaults work for local dev)
DATA_DIR=./data
STATE_DIR=./state
```

### Dockerfile (uv-based, replaces Phase 1 placeholder)
```dockerfile
# Source: https://docs.astral.sh/uv/guides/integration/docker/
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (layer caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --compile-bytecode

# Copy source and install project
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --compile-bytecode

# --- Runtime stage ---
FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Use uvicorn directly for production
CMD ["python", "-m", "sketchpad.server"]
```

### test-oauth.sh Skeleton
```bash
#!/usr/bin/env bash
# End-to-end OAuth flow test for the Sketchpad MCP server.
# Usage: ./test-oauth.sh [SERVER_URL]
# Defaults to http://localhost:8000 if not provided.

set -euo pipefail
SERVER="${1:-http://localhost:8000}"

echo "=== Step 1: Discovery ==="
echo "Fetching OAuth Authorization Server metadata..."
curl -s "$SERVER/.well-known/oauth-authorization-server" | jq .

echo ""
echo "Fetching OAuth Protected Resource metadata..."
curl -s "$SERVER/.well-known/oauth-protected-resource" | jq .

echo ""
echo "=== Step 2: Unauthenticated Request (expect 401) ==="
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$SERVER/mcp")
echo "POST /mcp without token: HTTP $HTTP_CODE"
curl -s -D - -X POST "$SERVER/mcp" 2>&1 | grep -i "www-authenticate"

echo ""
echo "=== Step 3: Dynamic Client Registration ==="
CLIENT_RESPONSE=$(curl -s -X POST "$SERVER/register" \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "test-oauth-script",
    "redirect_uris": ["http://localhost:9999/callback"],
    "grant_types": ["authorization_code", "refresh_token"],
    "response_types": ["code"],
    "token_endpoint_auth_method": "none"
  }')
echo "$CLIENT_RESPONSE" | jq .
CLIENT_ID=$(echo "$CLIENT_RESPONSE" | jq -r '.client_id')
echo "Got client_id: $CLIENT_ID"

echo ""
echo "=== Step 4: Authorization (manual step) ==="
# Generate PKCE code_verifier and code_challenge
CODE_VERIFIER=$(openssl rand -base64 32 | tr -d '=/+' | head -c 43)
CODE_CHALLENGE=$(echo -n "$CODE_VERIFIER" | openssl dgst -sha256 -binary | base64 | tr '+/' '-_' | tr -d '=')
STATE=$(openssl rand -hex 16)

AUTH_URL="$SERVER/authorize?response_type=code&client_id=$CLIENT_ID&redirect_uri=http://localhost:9999/callback&code_challenge=$CODE_CHALLENGE&code_challenge_method=S256&state=$STATE"
echo "Open this URL in your browser:"
echo "$AUTH_URL"
echo ""
echo "After GitHub login, you'll be redirected to localhost:9999/callback"
echo "Copy the 'code' parameter from the redirect URL and paste it here:"
read -r AUTH_CODE

echo ""
echo "=== Step 5: Token Exchange ==="
TOKEN_RESPONSE=$(curl -s -X POST "$SERVER/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=$AUTH_CODE&client_id=$CLIENT_ID&redirect_uri=http://localhost:9999/callback&code_verifier=$CODE_VERIFIER")
echo "$TOKEN_RESPONSE" | jq .
ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')

echo ""
echo "=== Step 6: MCP Tool Calls ==="
echo "Calling tools/list..."
curl -s -X POST "$SERVER/mcp" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' | jq .

echo ""
echo "Calling read_file..."
curl -s -X POST "$SERVER/mcp" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"read_file","arguments":{}},"id":2}' | jq .

echo ""
echo "Calling write_file..."
curl -s -X POST "$SERVER/mcp" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"write_file","arguments":{"content":"Hello from test-oauth.sh!"}},"id":3}' | jq .

echo ""
echo "=== Done ==="
```

### pyproject.toml
```toml
[project]
name = "sketchpad"
version = "0.1.0"
description = "A minimal MCP server with OAuth 2.1 for Claude AI"
requires-python = ">=3.12"
dependencies = [
    "fastmcp>=3.0.2",
]

[tool.uv]
dev-dependencies = []
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SSE transport (GET /mcp) | Streamable HTTP (POST /mcp) | MCP spec 2025-03-26 | SSE deprecated; use `transport="http"` |
| DCR only | DCR + CIMD | FastMCP 3.0.0 (2026-02-18) | CIMD is the modern alternative; DCR still supported and required for Claude AI |
| In-memory OAuth state | FileTreeStore/Redis with encryption | FastMCP 2.13.0 (2025-late) | `jwt_signing_key` + `client_storage` params added |
| FastMCP 2.x | FastMCP 3.x | 2026-02-18 | Per-component auth, provider architecture, CLI enhancements. Non-breaking for basic OAuth |
| DCR required both grant_types | DCR accepts authorization_code only | MCP SDK fix (2026-02) | Issue #2460 resolved; no workaround needed |

**Deprecated/outdated:**
- **SSE transport:** Deprecated since MCP spec 2025-03-26. Use `transport="http"` (Streamable HTTP).
- **FastMCP 2.x:** Superseded by 3.x. Still works but 3.x has bug fixes relevant to this project.
- **`requirements.txt`:** Phase 1 used this. Phase 2 migrates to `pyproject.toml` + `uv`.

## Open Questions

1. **MCP `initialize` Request Handling with Auth**
   - What we know: FastMCP handles `initialize` automatically. The MCP spec requires `tools/list` and `tools/call` to be authenticated but the initialize handshake may have its own flow.
   - What's unclear: Whether FastMCP sends `initialize` response before or after token validation for the first request (spec says POST /mcp must be authenticated but initialize is the first message).
   - Recommendation: Test with curl and MCP Inspector during implementation. FastMCP likely handles this correctly.

2. **GitHubProvider `redirect_path` Default**
   - What we know: Default is `/auth/callback`. GitHub OAuth App must be configured with `{SERVER_URL}/auth/callback`.
   - What's unclear: Whether this default changed between FastMCP versions.
   - Recommendation: Explicitly set `redirect_path="/auth/callback"` if uncertain, and document the GitHub OAuth App callback URL format.

3. **Docker Multi-Stage Build with `--mount=type=cache`**
   - What we know: uv cache mounts speed up builds. GitHub Actions supports BuildKit.
   - What's unclear: Whether the existing GitHub Actions workflow (using `docker/build-push-action@v6`) supports BuildKit cache mounts out of the box.
   - Recommendation: BuildKit is enabled by default in modern Docker and GitHub Actions. Test and fall back to standard COPY if needed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | bash + curl + jq (for `test-oauth.sh`) |
| Config file | none -- script-based testing |
| Quick run command | `curl -s http://localhost:8000/.well-known/oauth-authorization-server \| jq .` |
| Full suite command | `./test-oauth.sh http://localhost:8000` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DISC-01 | OAuth AS metadata endpoint | smoke | `curl -sf http://localhost:8000/.well-known/oauth-authorization-server \| jq -e '.authorization_endpoint'` | Wave 0: test-oauth.sh |
| DISC-02 | Protected resource metadata | smoke | `curl -sf http://localhost:8000/.well-known/oauth-protected-resource \| jq -e '.resource'` | Wave 0: test-oauth.sh |
| DISC-03 | 401 with WWW-Authenticate header | smoke | `curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:8000/mcp` (expect 401) | Wave 0: test-oauth.sh |
| AUTH-01 | DCR returns client_id | smoke | `curl -sf -X POST http://localhost:8000/register -H 'Content-Type: application/json' -d '...' \| jq -e '.client_id'` | Wave 0: test-oauth.sh |
| AUTH-02 | /authorize redirects to GitHub | manual | Open authorize URL in browser, verify GitHub login page | manual-only: requires browser interaction |
| AUTH-03 | GitHub callback -> auth code | manual | Complete GitHub login, verify redirect with code param | manual-only: requires browser interaction |
| AUTH-04 | Token exchange with PKCE | smoke | POST /token with code + code_verifier, expect access_token | Wave 0: test-oauth.sh |
| AUTH-05 | Refresh token issued | smoke | Check token response for refresh_token field | Wave 0: test-oauth.sh |
| AUTH-06 | Refresh token grant | smoke | POST /token with grant_type=refresh_token | Wave 0: test-oauth.sh |
| AUTH-07 | Token expiration | integration | Check expires_in field in token response | Wave 0: test-oauth.sh |
| MCP-01 | Streamable HTTP on /mcp | smoke | POST /mcp with valid token + initialize request | Wave 0: test-oauth.sh |
| MCP-02 | Initialize returns capabilities | smoke | Check initialize response for tools capability | Wave 0: test-oauth.sh |
| MCP-03 | tools/list returns read_file, write_file | smoke | POST /mcp with tools/list, check tool names | Wave 0: test-oauth.sh |
| MCP-04 | tools/call dispatches correctly | smoke | POST /mcp with tools/call for each tool | Wave 0: test-oauth.sh |
| MCP-05 | Bearer token validation | smoke | POST /mcp without token -> 401 | Wave 0: test-oauth.sh |
| TOOL-01 | read_file returns contents | smoke | Call read_file via MCP, check response | Wave 0: test-oauth.sh |
| TOOL-02 | write_file updates contents | smoke | Call write_file then read_file, verify content | Wave 0: test-oauth.sh |

### Sampling Rate
- **Per task commit:** `curl -sf http://localhost:8000/.well-known/oauth-authorization-server | jq .`
- **Per wave merge:** `./test-oauth.sh http://localhost:8000`
- **Phase gate:** Full test-oauth.sh green + MCP Inspector manual verification

### Wave 0 Gaps
- [ ] `test-oauth.sh` -- covers DISC-01 through TOOL-02 (entire flow)
- [ ] `.env` file with valid credentials -- required for any testing
- [ ] Server running locally -- `uv run python -m sketchpad.server`

## Sources

### Primary (HIGH confidence)
- [FastMCP Official Docs - Authentication](https://gofastmcp.com/servers/auth/authentication) - OAuth 2.1 setup, GitHubProvider
- [FastMCP Official Docs - GitHub Integration](https://gofastmcp.com/integrations/github) - Complete GitHubProvider code examples, parameters
- [FastMCP Official Docs - OAuth Proxy](https://gofastmcp.com/servers/auth/oauth-proxy) - Proxy architecture, endpoint paths, security features
- [FastMCP Official Docs - Storage Backends](https://gofastmcp.com/servers/storage-backends) - FileTreeStore, FernetEncryptionWrapper code
- [FastMCP Official Docs - Running Server](https://gofastmcp.com/deployment/running-server) - transport="http", host, port config
- [FastMCP Official Docs - HTTP Deployment](https://gofastmcp.com/deployment/http) - ASGI, uvicorn, stateless mode
- [FastMCP PyPI](https://pypi.org/project/fastmcp/) - Version 3.1.0 (2026-03-03), dependencies
- [uv Docker Guide](https://docs.astral.sh/uv/guides/integration/docker/) - Dockerfile patterns for uv projects
- [MCP Spec - Transports](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports) - Streamable HTTP spec

### Secondary (MEDIUM confidence)
- [GitHub Issue #2460](https://github.com/jlowin/fastmcp/issues/2460) - DCR grant_types bug, CLOSED 2026-02-06
- [GitHub Issue #1400](https://github.com/modelcontextprotocol/python-sdk/issues/1400) - RFC 9728 path bug, FIXED 2025-10-06
- [GitHub Issue #2018](https://github.com/PrefectHQ/fastmcp/issues/2018) - .env auto-loading issue, FIXED 2025-10-09
- [FastMCP 3.0 Release Blog](https://www.jlowin.dev/blog/fastmcp-3-launch) - 3.0 GA features and changes
- [FastMCP Releases](https://github.com/jlowin/fastmcp/releases) - 3.1.0 and 3.0.2 changelogs

### Tertiary (LOW confidence)
- test-oauth.sh script pattern is custom; the MCP JSON-RPC message format for tools/call and tools/list should be verified against actual FastMCP behavior during implementation. The `initialize` handshake sequence over Streamable HTTP may require an initial `initialize` request before `tools/list`.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - FastMCP GitHubProvider is well-documented with code examples in official docs
- Architecture: HIGH - Pattern directly from official docs; FileTreeStore + FernetEncryptionWrapper documented
- Pitfalls: HIGH - Known issues verified against GitHub issues (all resolved); Docker patterns well-established
- Code examples: MEDIUM - Based on official docs but not tested against FastMCP 3.1.0 specifically; import paths and exact API may vary slightly

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (30 days -- FastMCP is actively developed but core OAuth API is stable since 2.13.0)
