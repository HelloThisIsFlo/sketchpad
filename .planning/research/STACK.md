# Stack Research

**Domain:** Per-user storage isolation + Makefile-to-Just migration for existing MCP server
**Researched:** 2026-03-06
**Confidence:** HIGH

## Scope

This research covers ONLY what is new for v1.1. The existing stack (FastMCP 3.1.0, Python 3.12, Kubernetes/Talos, Cloudflare Tunnel, FileTreeStore + Fernet, GitHub Actions CI) is validated and out of scope.

---

## Recommended Stack Additions

### Per-User Identity Extraction (no new dependencies)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `fastmcp.dependencies.TokenClaim` | 3.1.0 (installed) | Extract GitHub username directly as a string into tool handlers | Built into FastMCP 3.1.0. Simplest DI pattern: one default parameter, auto-resolved, hidden from tool JSON schema. Raises `RuntimeError` if claim missing. |
| `fastmcp.dependencies.CurrentAccessToken` | 3.1.0 (installed) | DI-inject the full OAuth `AccessToken` into tool handlers | Available for cases needing multiple claims. Not needed for this project but good to know exists. |
| `fastmcp.server.dependencies.get_access_token` | 3.1.0 (installed) | Imperative function to get token from current context | For helper functions outside tool handler signatures. Returns `None` if unauthenticated. |

**No new Python packages required.** The DI system (`CurrentAccessToken`, `TokenClaim`) is built into FastMCP 3.1.0 via the `uncalled_for` DI engine, which is already an installed transitive dependency.

### Build Tooling Migration

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Just (casey/just) | 1.46.0 | Command runner replacing Makefile | Purpose-built command runner (not a build system). No `.PHONY` needed, better error messages, cross-platform, loads `.env` files natively, supports arguments to recipes. Current Makefile is 6 recipes -- direct 1:1 translation. |

---

## How FastMCP Exposes User Identity

**Confidence: HIGH** -- verified by reading the installed FastMCP 3.1.0 source code directly.

### The GitHub Provider's AccessToken

When `GitHubProvider` verifies a token, it calls `https://api.github.com/user` and creates an `AccessToken` with these claims:

```python
# From fastmcp/server/auth/providers/github.py lines 130-143 (installed 3.1.0)
AccessToken(
    token=token,
    client_id=str(user_data.get("id", "unknown")),  # GitHub numeric user ID
    scopes=token_scopes,
    expires_at=None,
    claims={
        "sub": str(user_data["id"]),       # Numeric GitHub user ID (string)
        "login": user_data.get("login"),    # GitHub username e.g. "hellothisisflo"
        "name": user_data.get("name"),      # Display name
        "email": user_data.get("email"),    # Email (may be None if private)
        "avatar_url": user_data.get("avatar_url"),
        "github_user_data": user_data,      # Full GitHub API response dict
    },
)
```

### Pattern 1: TokenClaim DI (RECOMMENDED for this project)

Use `TokenClaim("login")` to inject the GitHub username directly as a string parameter:

```python
from fastmcp.dependencies import TokenClaim

@mcp.tool
def read_file(username: str = TokenClaim("login")) -> str:
    """Read the user's sketchpad."""
    sketchpad_path = Path(data_dir) / username / "sketchpad.md"
    # ...
```

**Why `login` not `sub`:** The `login` field is the human-readable GitHub username (e.g. `"hellothisisflo"`). The `sub` field is the numeric ID (e.g. `"12345"`). Using `login` makes the filesystem human-readable (`/data/hellothisisflo/sketchpad.md`). The trade-off: GitHub username rename = new sketchpad. PROJECT.md explicitly accepts this.

**Why `TokenClaim` not `CurrentAccessToken`:**
1. Least code -- one default parameter, no `AccessToken` type import
2. FastMCP hides DI parameters from the tool's JSON schema (Claude AI never sees `username`)
3. Raises `RuntimeError` automatically if no token or claim missing -- fail-fast
4. Only the username is needed for per-user file isolation

### Pattern 2: CurrentAccessToken DI (for reference)

```python
from fastmcp.dependencies import CurrentAccessToken
from fastmcp.server.auth import AccessToken

@mcp.tool
def read_file(token: AccessToken = CurrentAccessToken()) -> str:
    """Read the user's sketchpad."""
    username = token.claims.get("login", "unknown")
    sketchpad_path = Path(data_dir) / username / "sketchpad.md"
    # ...
```

### Pattern 3: get_access_token() imperative (for helper functions)

```python
from fastmcp.server.dependencies import get_access_token

def get_username() -> str:
    token = get_access_token()
    if token is None:
        raise RuntimeError("Not authenticated")
    return token.claims.get("login", "unknown")
```

---

## Just (casey/just) Migration Details

**Confidence: HIGH** -- version verified via Homebrew formulae page.

### Installation

```bash
# macOS (primary dev machine)
brew install just

# Verify
just --version  # Expected: just 1.46.0

# GitHub Actions CI
# Use the official setup action:
#   - uses: extractions/setup-just@v2
```

### Justfile Equivalent of Current Makefile

Current Makefile has 6 recipes: `build`, `push`, `deploy`, `restart`, `all`, `status`. Direct translation:

```just
# Project variables
image  := "ghcr.io/hellothisisflo/sketchpad"
sha    := `git rev-parse --short HEAD`
tag    := "sha-" + sha
ns     := "sketchpad"

# Default recipe (runs when you type `just` with no arguments)
default: status

# Build container image for linux/amd64
build:
    docker buildx build --platform linux/amd64 -t {{image}}:{{tag}} -t {{image}}:latest --load .

# Push image to registry
push:
    docker push {{image}}:{{tag}}
    docker push {{image}}:latest

# Deploy to Kubernetes
deploy:
    kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml -n {{ns}}
    kubectl rollout status deployment/sketchpad -n {{ns}} --timeout=120s

# Restart deployment
restart:
    kubectl rollout restart deployment/sketchpad -n {{ns}}
    kubectl rollout status deployment/sketchpad -n {{ns}} --timeout=120s

# Build, push, and deploy
all: build push deploy

# Show pod and service status
status:
    kubectl get pods -n {{ns}}
    kubectl get svc -n {{ns}}
```

### Key Syntax Differences from Make

| Concept | Make | Just |
|---------|------|------|
| Variables | `SHA := $(shell git rev-parse --short HEAD)` | `sha := \`git rev-parse --short HEAD\`` |
| Variable reference | `$(IMAGE)` | `{{image}}` |
| Shell execution | `$(shell ...)` | Backticks: `` \`...\` `` |
| Phony targets | `.PHONY: build push` | Not needed (all recipes are commands) |
| Recipe dependencies | `all: build push deploy` | `all: build push deploy` (same syntax) |
| Tab indentation | Required (tabs only) | Spaces or tabs (4 spaces recommended) |
| Default target | First target in file | `default:` recipe, or first recipe if no `default` |
| Recipe arguments | Complex `$(1)` pattern | Native: `recipe arg1 arg2:` |
| String concatenation | Not native | `tag := "sha-" + sha` |

### CI Impact

The GitHub Actions CI workflow currently calls `make build` etc. After migration:
1. Add `extractions/setup-just@v2` step before build steps
2. Replace `make build` with `just build`, `make push` with `just push`, etc.
3. Delete the `Makefile`

---

## What NOT to Add

| Avoid | Why | Notes |
|-------|-----|-------|
| Database (SQLite, PostgreSQL) | Overkill for per-user single-file storage | Filesystem directories are the right abstraction: one folder per user, one file per folder |
| User management library | No admin UI, no user CRUD | Users are self-service via GitHub OAuth. No user table needed. |
| Session middleware | FastMCP handles sessions | The AccessToken DI already provides per-request user identity |
| Path sanitization library | stdlib `pathlib` is sufficient | GitHub usernames are alphanumeric + hyphens, already filesystem-safe. Basic validation (`/` and `..` rejection) is trivial to add defensively. |
| httpx (as direct dep) | Already a transitive dep of FastMCP | Used internally by GitHubTokenVerifier. Do not add to pyproject.toml. |
| New Python packages | Nothing needed | `TokenClaim` / `CurrentAccessToken` / `get_access_token` are all built into FastMCP 3.1.0 |
| `just` in Docker image | It is a dev/CI tool only | The container runs `python -m sketchpad`, not `just`. Do not install `just` in the Dockerfile. |

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `TokenClaim("login")` for username | `CurrentAccessToken()` + manual claim extraction | When you need multiple claims (name, email, avatar) in a single tool. Not needed here -- only username matters. |
| `TokenClaim("login")` (GitHub username) | `TokenClaim("sub")` (numeric GitHub ID) | When stable identity across username renames is critical. PROJECT.md explicitly accepts username rename = new sketchpad. |
| Just (casey/just) | Task (go-task/task) | If team already uses Task. Just has simpler syntax closer to Make, easier migration. |
| Just (casey/just) | Keep Makefile | If the Makefile were complex with real build DAG dependencies. 6 phony recipes gain nothing from Make's DAG. |
| Filesystem dirs | SQLite per-user DB | If multi-file per user with search/indexing. Single file per user = filesystem is perfect. |

---

## Version Compatibility

| Package | Version | Compatible With | Notes |
|---------|---------|-----------------|-------|
| FastMCP | 3.1.0 (installed) | Python >=3.10 | `CurrentAccessToken` / `TokenClaim` DI verified importable. `uncalled_for` DI engine included as transitive dep. |
| Just | 1.46.0 (Homebrew current) | Any OS | Standalone Rust binary, no runtime dependencies. Dev/CI tool only, not in container. |
| Python | 3.12 (installed) | FastMCP 3.1.0 | Already validated in v1.0. No change needed. |

---

## Sources

- **FastMCP 3.1.0 installed source** (`fastmcp/server/auth/providers/github.py`) -- verified `AccessToken.claims` structure with `login`, `sub`, `name`, `email`, `avatar_url`, `github_user_data` fields. **HIGH confidence.**
- **FastMCP 3.1.0 installed source** (`fastmcp/server/dependencies.py` lines 1318-1340, 1370-1399) -- verified `CurrentAccessToken()` and `TokenClaim()` DI patterns, including docstrings with usage examples. **HIGH confidence.**
- **FastMCP 3.1.0 installed source** (`fastmcp/dependencies.py`) -- verified public re-exports of `CurrentAccessToken`, `TokenClaim`, `get_access_token`. **HIGH confidence.**
- **FastMCP 3.1.0 installed source** (`fastmcp/server/auth/auth.py` line 54-57) -- verified `AccessToken` extends SDK `_SDKAccessToken` with `claims: dict[str, Any]` field. **HIGH confidence.**
- **Runtime verification** -- `python -c "from fastmcp.dependencies import CurrentAccessToken, TokenClaim"` succeeds on installed 3.1.0. **HIGH confidence.**
- [Homebrew just formula](https://formulae.brew.sh/formula/just) -- version 1.46.0 confirmed. **HIGH confidence.**
- [casey/just GitHub](https://github.com/casey/just) -- feature overview, syntax reference. **HIGH confidence.**
- [Just official site](https://just.systems/) -- cross-platform command runner description. **HIGH confidence.**
- [MCP SDK issue #1414](https://github.com/modelcontextprotocol/python-sdk/issues/1414) -- confirmed Context-based token access is the standard pattern. **MEDIUM confidence.**
- [FastMCP auth docs](https://gofastmcp.com/python-sdk/fastmcp-server-auth-auth) -- general auth architecture reference. **MEDIUM confidence.**

---
*Stack research for: Sketchpad v1.1 (per-user isolation + Just migration)*
*Researched: 2026-03-06*
