# Architecture: Per-User Storage Isolation

**Domain:** Per-user sketchpad isolation + Makefile-to-Just migration for existing FastMCP 3.1.0 MCP server
**Researched:** 2026-03-06
**Confidence:** HIGH (verified against installed FastMCP 3.1.0 source code and existing project files)

---

## System Overview (v1.1 changes highlighted)

```
Internet
    |
    v
Cloudflare Edge (unchanged)
    |
    v
cloudflared Pod (unchanged)
    |
    v
ClusterIP Service (unchanged)
    |
    v
MCP Server Pod
    |
    +-- FastMCP + GitHubProvider (unchanged)
    |
    +-- Bearer token middleware (unchanged)
    |
    +-- Tool handlers: read_file / write_file
    |       |
    |       +-- [NEW] Extract GitHub username from AccessToken.claims["login"]
    |       |
    |       +-- [CHANGED] File path: /data/{username}/sketchpad.md
    |       |   (was: /data/sketchpad.md)
    |       |
    |       v
    +-- PVC: sketchpad-data
            |
            +-- /data/
                +-- hellothisisflo/
                |   +-- sketchpad.md
                +-- other-user/
                    +-- sketchpad.md
```

The architecture change is minimal: the tool handlers gain username awareness. Everything else (OAuth flow, middleware, K8s infrastructure, PVCs) is unchanged.

---

## Integration Point: User Identity in Tool Handlers

### How It Works

FastMCP 3.1.0 provides two dependency injection mechanisms for accessing the authenticated user's identity inside `@mcp.tool` handlers:

**Option A: `CurrentAccessToken()` dependency (recommended)**

```python
from fastmcp.server.auth import AccessToken
from fastmcp.server.dependencies import CurrentAccessToken

@mcp.tool
async def read_file(token: AccessToken = CurrentAccessToken()) -> str:
    username = token.claims["login"]  # GitHub username
    # ...
```

**Option B: `TokenClaim()` dependency (cleanest)**

```python
from fastmcp.server.dependencies import TokenClaim

@mcp.tool
async def read_file(username: str = TokenClaim("login")) -> str:
    # username is automatically injected from the token
    # ...
```

Both approaches are invisible to the MCP client (Claude AI). FastMCP's dependency injection system strips injected parameters from the tool's JSON schema, so Claude never sees `token` or `username` as a parameter it needs to provide.

### What Claims Are Available

When a tool handler runs, FastMCP's `load_access_token` flow:
1. Verifies the FastMCP JWT signature
2. Looks up the upstream GitHub token via JTI mapping
3. Calls `GitHubTokenVerifier.verify_token`, which hits `api.github.com/user`
4. Returns an `AccessToken` with these claims:

| Claim | Type | Example | Use |
|-------|------|---------|-----|
| `sub` | `str` | `"12345678"` | GitHub numeric user ID (immutable) |
| `login` | `str` | `"hellothisisflo"` | GitHub username (human-readable, can change) |
| `name` | `str\|None` | `"Flo"` | Display name |
| `email` | `str\|None` | `"flo@example.com"` | Primary email |
| `avatar_url` | `str` | `"https://..."` | Avatar URL |
| `github_user_data` | `dict` | `{...}` | Full GitHub API response |

**Confidence:** HIGH -- verified by reading `GitHubTokenVerifier.verify_token` at line 130-143 of the installed `fastmcp/server/auth/providers/github.py`.

### Which Claim to Use as Folder Name

**Use `login` (GitHub username), not `sub` (numeric ID).**

Rationale:
- `login` is human-readable: `/data/hellothisisflo/sketchpad.md` vs `/data/12345678/sketchpad.md`
- GitHub usernames are already filesystem-safe: alphanumeric + hyphens only, 1-39 chars, no consecutive hyphens, no leading/trailing hyphens
- No sanitization needed -- the username can be used directly as a directory name
- Username rename = new sketchpad is acceptable (documented in PROJECT.md as a key decision)
- `sub` would survive username renames but produces opaque folder names that are painful to debug on the NFS share

---

## Modified Components

### 1. `src/sketchpad/tools.py` (MODIFIED)

The only source file that changes. Tool handlers gain a `username` parameter via `TokenClaim("login")` and construct per-user paths.

**Current code:**
```python
def register_tools(mcp):
    @mcp.tool
    def read_file() -> str:
        cfg = get_config()
        sketchpad_path = Path(cfg["DATA_DIR"]) / cfg["SKETCHPAD_FILENAME"]
        # ...

    @mcp.tool
    def write_file(content: str, mode: str = "replace") -> str:
        cfg = get_config()
        sketchpad_path = Path(cfg["DATA_DIR"]) / cfg["SKETCHPAD_FILENAME"]
        # ...
```

**New code:**
```python
from fastmcp.server.dependencies import TokenClaim

def register_tools(mcp):
    @mcp.tool
    async def read_file(username: str = TokenClaim("login")) -> str:
        cfg = get_config()
        sketchpad_path = Path(cfg["DATA_DIR"]) / username / cfg["SKETCHPAD_FILENAME"]
        # ...

    @mcp.tool
    async def write_file(
        content: str,
        mode: str = "replace",
        username: str = TokenClaim("login"),
    ) -> str:
        cfg = get_config()
        sketchpad_path = Path(cfg["DATA_DIR"]) / username / cfg["SKETCHPAD_FILENAME"]
        # ...
```

**Key changes:**
- Functions become `async` (required by FastMCP's DI system for `TokenClaim`)
- `username` parameter added with `TokenClaim("login")` default -- invisible to Claude AI
- Path changes from `DATA_DIR/sketchpad.md` to `DATA_DIR/{username}/sketchpad.md`
- `write_file` already calls `sketchpad_path.parent.mkdir(parents=True, exist_ok=True)`, so user directories are auto-created on first write

### 2. `Makefile` -> `justfile` (NEW file, old file removed)

**Current Makefile targets:**

| Target | Command |
|--------|---------|
| `build` | `docker buildx build --platform linux/amd64 -t IMAGE:TAG -t IMAGE:latest --load .` |
| `push` | `docker push IMAGE:TAG && docker push IMAGE:latest` |
| `deploy` | `kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml && rollout status` |
| `restart` | `kubectl rollout restart && rollout status` |
| `all` | `build push deploy` |
| `status` | `kubectl get pods && kubectl get svc` |

**New justfile:**

```just
image  := "ghcr.io/hellothisisflo/sketchpad"
sha    := `git rev-parse --short HEAD`
tag    := "sha-" + sha
ns     := "sketchpad"

# Build container image for linux/amd64
build:
    docker buildx build --platform linux/amd64 -t {{image}}:{{tag}} -t {{image}}:latest --load .

# Push image to GHCR
push:
    docker push {{image}}:{{tag}}
    docker push {{image}}:latest

# Apply K8s manifests and wait for rollout
deploy:
    kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml -n {{ns}}
    kubectl rollout status deployment/sketchpad -n {{ns}} --timeout=120s

# Rolling restart
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

**Key syntax differences from Make:**
- Variables use `:=` (same) but are referenced with `{{var}}` (not `$(VAR)`)
- Backtick evaluation for shell commands: `` sha := `git rev-parse --short HEAD` ``
- No `.PHONY` needed -- Just is a command runner, not a build system
- Comments with `#` above recipes serve as documentation (shown in `just --list`)
- No tab-vs-spaces ambiguity -- Just accepts either

### 3. No other files change

| File | Status | Notes |
|------|--------|-------|
| `src/sketchpad/server.py` | Unchanged | `create_app()` already passes `mcp` to `register_tools()` |
| `src/sketchpad/config.py` | Unchanged | `DATA_DIR` config is already correct |
| `src/sketchpad/middleware.py` | Unchanged | Origin validation is path-based, not user-based |
| `src/sketchpad/__main__.py` | Unchanged | App startup is not affected |
| `k8s/deployment.yaml` | Unchanged | PVC mount at `/data` already accommodates subdirectories |
| `k8s/pvc.yaml` | Unchanged | Both PVCs are already sized at 1Gi (ample for multi-user text) |
| `k8s/service.yaml` | Unchanged | |

---

## Data Flow (v1.1 -- changes in steady-state tool calls only)

```
Claude AI
    | POST /mcp  Authorization: Bearer <JWT>
    | Body: { method: "tools/call", params: { name: "read_file" } }
    v
Bearer middleware (FastMCP, unchanged)
    | Validate JWT -> swap for GitHub token -> call api.github.com/user
    | Returns AccessToken with claims: { sub: "12345", login: "hellothisisflo", ... }
    v
FastMCP DI system (unchanged but newly used)
    | Resolves TokenClaim("login") -> "hellothisisflo"
    | Injects as `username` parameter
    v
Tool handler: read_file(username="hellothisisflo")
    | path = /data/hellothisisflo/sketchpad.md     [NEW: was /data/sketchpad.md]
    v
PVC: sketchpad-data (unchanged)
    | file contents from /data/hellothisisflo/sketchpad.md
    v
FastMCP response: { result: "file contents..." }
    v
Claude AI
```

**Security boundary:** Each user can only access their own subdirectory because:
1. The username comes from the validated GitHub OAuth token, not from user input
2. GitHub usernames cannot contain `/`, `..`, or any path traversal characters (alphanumeric + hyphens only)
3. There is no tool parameter for "which user's sketchpad" -- the username is server-side injected

---

## Storage Layout on PVC

```
/data/                          (PVC: sketchpad-data, mounted at /data)
    hellothisisflo/
        sketchpad.md            (auto-created on first write_file call)
    another-github-user/
        sketchpad.md

/state/                         (PVC: sketchpad-state, unchanged)
    <FileTreeStore encrypted OAuth state files>
```

- User directories are created lazily by `write_file` (the existing `sketchpad_path.parent.mkdir(parents=True, exist_ok=True)` already handles this)
- `read_file` for a user who has never written returns the `WELCOME_MESSAGE` (existing behavior via `if not sketchpad_path.exists()`)
- No migration of v1.0 data -- fresh start for v1.1 (confirmed in PROJECT.md key decisions)

---

## Patterns to Follow

### Pattern 1: TokenClaim Dependency Injection

**What:** Use `TokenClaim("login")` to inject the GitHub username into tool handlers without exposing it as a client-visible parameter.

**Why this pattern:**
- Cleanest API: single parameter, auto-injected, type is `str`
- No boilerplate: no need to import `AccessToken`, no need to unwrap `.claims["login"]`
- FastMCP strips DI parameters from the tool's JSON schema -- Claude AI never sees them
- If the claim is missing, FastMCP raises `RuntimeError` with a clear message listing available claims

**When to use:** When you need exactly one claim value (username, user ID, email).

**When NOT to use:** When you need multiple claims -- use `CurrentAccessToken()` instead and access `.claims` dict.

### Pattern 2: Lazy Directory Creation

**What:** Create user directories on first write, not eagerly.

**Why:** Avoid pre-provisioning. The user directory is created by the `write_file` tool's existing `mkdir(parents=True, exist_ok=True)`. For `read_file`, a missing directory simply returns the welcome message.

### Pattern 3: Just as Command Runner (not Build System)

**What:** Replace Make with Just for project commands (build, push, deploy, status).

**Why:**
- Just is a command runner, not a build system -- it does not track file timestamps or dependencies
- This project uses Make purely as a command runner (no file targets, no dependency tracking)
- Just has cleaner syntax: `{{var}}` instead of `$(VAR)`, backtick evaluation, no `.PHONY`, no tab-vs-spaces issue
- Just shows recipe descriptions from comments in `just --list`

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Using `sub` (numeric ID) as folder name

**What:** Using the GitHub numeric user ID (`sub` claim) as the directory name.

**Why bad:** Produces opaque paths like `/data/12345678/sketchpad.md` that are impossible to debug when SSH'ing into the NAS. The numeric ID is stable across username renames, but username renames are a documented acceptable trade-off for this project.

**Do instead:** Use `login` (GitHub username). It is human-readable and filesystem-safe without sanitization.

### Anti-Pattern 2: Sanitizing GitHub usernames for filesystem use

**What:** Adding a sanitization layer (regex replacement, slugification) to GitHub usernames before using them as directory names.

**Why bad:** Unnecessary complexity. GitHub usernames are already restricted to `[a-zA-Z0-9-]` with max 39 chars, no leading/trailing hyphens, no consecutive hyphens. This is already a valid POSIX directory name. Adding sanitization creates a mapping layer that could introduce collisions or confusion.

**Do instead:** Use the username directly. Trust GitHub's existing validation.

### Anti-Pattern 3: Passing username as a tool parameter

**What:** Adding a `username` parameter to the tool's public schema and letting Claude AI provide it.

**Why bad:** Any MCP client could pass any username, accessing other users' data. The username must come from the server-side token, not client input.

**Do instead:** Use `TokenClaim("login")` which is server-injected and invisible to the client.

### Anti-Pattern 4: Modifying server.py or config.py for per-user isolation

**What:** Adding user-awareness to the config system or server factory.

**Why bad:** Per-user isolation is a tool-level concern, not a server-level concern. The server authenticates users and provides identity via DI. The tools decide what to do with that identity. Config and server setup remain user-agnostic.

**Do instead:** All per-user logic lives in `tools.py`. Config stays generic (`DATA_DIR` is just a base path).

---

## Build Order (dependency-aware)

The changes for v1.1 have a natural ordering based on dependencies:

```
1. justfile (no dependencies -- can be done first or in parallel)
      |
      v
2. tools.py (depends on understanding TokenClaim API -- this research)
      |
      v
3. Delete Makefile (after justfile is verified working)
      |
      v
4. Test locally (depends on tools.py changes)
      |
      v
5. Build + deploy via justfile (depends on all above)
```

**Suggested phases:**

| Phase | What | Why This Order |
|-------|------|----------------|
| 1 | Modify `tools.py` with `TokenClaim("login")` and per-user paths | Core feature; smallest change, highest value |
| 2 | Create `justfile` + delete `Makefile` | Independent of Phase 1; can be done in parallel |
| 3 | Test and deploy | Depends on both phases above |

**Phase 1 is ~10 lines of code change** in a single file. Phase 2 is a straightforward syntax translation. Phase 3 is `just all` and manual verification from Claude AI.

---

## Component Boundaries (what owns what)

| Component | Owns | Does NOT own |
|-----------|------|-------------|
| `GitHubProvider` (FastMCP) | OAuth flow, JWT issuance, token validation, GitHub API calls | User directory management, file I/O |
| FastMCP DI system | Resolving `TokenClaim("login")` from the `AccessToken` | Knowing what "login" means semantically |
| `tools.py` | Per-user path construction, file read/write, directory creation | Authentication, token validation |
| `config.py` | Base `DATA_DIR` path | Per-user subdirectory logic |
| PVC `sketchpad-data` | Persistent storage at `/data` | User isolation (that is enforced by code, not filesystem permissions) |

---

## Sources

- FastMCP 3.1.0 `GitHubTokenVerifier.verify_token` -- `/fastmcp/server/auth/providers/github.py` lines 66-150 (installed package, HIGH confidence)
- FastMCP 3.1.0 `get_access_token` -- `/fastmcp/server/dependencies.py` lines 469-534 (installed package, HIGH confidence)
- FastMCP 3.1.0 `CurrentAccessToken` and `TokenClaim` -- `/fastmcp/server/dependencies.py` lines 1286-1399 (installed package, HIGH confidence)
- FastMCP 3.1.0 `AccessToken` class -- `/fastmcp/server/auth/auth.py` lines 54-57 (installed package, HIGH confidence)
- FastMCP 3.1.0 `OAuthProxy.load_access_token` -- `/fastmcp/server/auth/oauth_proxy/proxy.py` lines 1384-1453 (installed package, HIGH confidence)
- [GitHub username format](https://github.com/shinnn/github-username-regex) -- alphanumeric + hyphens, 1-39 chars (MEDIUM confidence, community reference)
- [Just command runner manual](https://just.systems/man/en/) -- official documentation (HIGH confidence)
- Project files: `src/sketchpad/tools.py`, `src/sketchpad/config.py`, `src/sketchpad/server.py`, `Makefile`, `k8s/deployment.yaml`, `k8s/pvc.yaml` (direct source, HIGH confidence)

---

*Architecture research for: Per-user storage isolation integration with FastMCP 3.1.0*
*Researched: 2026-03-06*
