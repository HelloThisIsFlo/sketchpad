# Pitfalls Research: v1.1 Multi-User Isolation

**Domain:** Adding per-user storage isolation and Makefile-to-Just migration to an existing single-user MCP server
**Researched:** 2026-03-06
**Confidence:** HIGH (verified against FastMCP source code in the installed package, official docs, and GitHub issues)

---

## Critical Pitfalls

These will cause security vulnerabilities, data leaks between users, or complete feature failure.

---

### Pitfall 1: Path Traversal via Unsanitized Username in Directory Path

**What goes wrong:**

The current code constructs the sketchpad path as `Path(cfg["DATA_DIR"]) / cfg["SKETCHPAD_FILENAME"]`. The v1.1 change adds a username segment: `Path(cfg["DATA_DIR"]) / username / cfg["SKETCHPAD_FILENAME"]`. If the username is taken directly from the OAuth token claims without sanitization, a malicious or compromised OAuth provider could return a username containing path traversal sequences like `../admin` or `../../etc`, allowing one user to read or overwrite another user's sketchpad -- or worse, write to arbitrary paths on the PVC.

**Why it happens:**

Developers trust that "GitHub usernames are safe" because GitHub restricts them to `[a-zA-Z0-9-]`. This is true *today* for GitHub.com, but: (1) the server already supports Google as an OAuth provider via the `OAUTH_PROVIDER` env var, and Google display names can contain arbitrary Unicode; (2) a future provider switch could introduce unrestricted usernames; (3) defense-in-depth requires validating at the point of use, not at the identity source.

**Consequences:**

- User A reads/writes User B's sketchpad file
- Arbitrary file write on the PVC (could corrupt OAuth state if data and state share a parent)
- Silent data leak with no error or log

**Prevention:**

Validate the username at the point of path construction using Python's `pathlib.Path.resolve()` + `is_relative_to()`:

```python
from pathlib import Path

def get_user_sketchpad_path(data_dir: str, username: str, filename: str) -> Path:
    base = Path(data_dir).resolve()
    user_path = (base / username / filename).resolve()
    if not user_path.is_relative_to(base):
        raise ValueError(f"Invalid username for path construction: {username!r}")
    return user_path
```

Additionally, apply an allowlist regex as the first line of defense:

```python
import re
SAFE_USERNAME = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,38}$')
if not SAFE_USERNAME.match(username):
    raise ValueError(f"Username contains disallowed characters: {username!r}")
```

**Detection:**

- Unit test: attempt path traversal with usernames like `../other-user`, `../../etc/passwd`, `foo/../../bar`
- Log the resolved path and compare against the expected base directory

**Phase to address:** Per-user isolation implementation (first task -- validate before writing any file I/O code)

---

### Pitfall 2: Extracting the Wrong Claim from the OAuth Token

**What goes wrong:**

FastMCP's `GitHubProvider` populates the `AccessToken.claims` dict with GitHub user data. The available claims include `sub` (numeric GitHub user ID as string), `login` (GitHub username), `name` (display name), and `email`. Using the wrong claim key -- e.g., `token.claims.get("username")` instead of `token.claims.get("login")` -- returns `None`, and the code either crashes or falls through to a default, creating all users' files in the same directory.

**Why it happens:**

- Standard OAuth/OIDC uses `sub` for the subject identifier, but GitHub's `sub` is a numeric ID (e.g., `"12345678"`), not a human-readable username
- The claim key is `"login"`, not `"username"` or `"preferred_username"` (which are OIDC standard names)
- Different providers use different claim keys: Google uses `"email"` or `"sub"`, GitHub uses `"login"`

**Consequences:**

- If using `sub`: directories are named `12345678/` instead of `hellothisisflo/` -- functional but unreadable for debugging, and breaks if the user changes their GitHub account ID (impossible) vs. username (possible but rare)
- If using a wrong key like `"username"`: returns `None`, causing a `TypeError` when constructing the path or defaulting all users to the same folder
- If using `"name"`: display names can be `None`, contain spaces, Unicode, etc.

**Prevention:**

Use `"login"` for GitHub and extract it using FastMCP's `TokenClaim` dependency injection, which raises `RuntimeError` if the claim is missing (fail-fast):

```python
from fastmcp.server.dependencies import TokenClaim

@mcp.tool
def read_file(username: str = TokenClaim("login")) -> str:
    # username is automatically extracted from the JWT and validated as non-None
    ...
```

Verified in the installed FastMCP 3.1.0 source: `GitHubTokenVerifier.verify_token()` in `fastmcp/server/auth/providers/github.py` line 137 sets `claims={"login": user_data.get("login"), ...}`.

**Detection:**

- Log `token.claims.keys()` during initial testing to see what's actually available
- Unit test: mock an AccessToken with known claims and verify the correct key is used
- Integration test: authenticate via GitHub and log the extracted username

**Phase to address:** User identity extraction (before per-user path logic)

---

### Pitfall 3: Breaking Existing Single-User Functionality During Migration

**What goes wrong:**

The v1.0 tools work without any user context -- `read_file()` and `write_file(content, mode)` take no user parameter. Adding a `username` parameter changes the function signature. If the parameter is not injected via FastMCP's dependency injection (`TokenClaim`) but instead added as a regular parameter, Claude will see it in the tool schema and try to fill it in -- sending a hallucinated or user-chosen username, bypassing the OAuth identity entirely.

**Why it happens:**

FastMCP's `@mcp.tool` decorator exposes all function parameters as tool arguments to the LLM client. The `TokenClaim("login")` dependency is special -- FastMCP knows to inject it from the auth context and hide it from the tool schema. But if you write `def read_file(username: str)` without the `TokenClaim` default, FastMCP exposes `username` as a required argument that Claude must provide.

**Consequences:**

- **Security bypass:** Claude sends `username: "admin"` and reads another user's sketchpad
- **Broken schema:** Existing Claude sessions that cached the old tool schema may fail with unexpected parameter errors
- **Regression:** The tool works differently in v1.1 than v1.0, breaking the existing proven flow

**Prevention:**

Use FastMCP's dependency injection exclusively for user identity:

```python
@mcp.tool
def read_file(username: str = TokenClaim("login")) -> str:
    # `username` is injected by FastMCP from the OAuth token, NOT from Claude
    # FastMCP hides DI parameters from the tool schema
```

Verify by checking the tool's JSON schema after registration -- `username` should NOT appear in the `inputSchema.properties`.

**Detection:**

- After implementing, call `mcp.list_tools()` or inspect the tool schema to confirm `username` is not listed as a parameter
- Test with Claude: ask it to read the sketchpad -- it should not ask for or mention a username

**Phase to address:** Tool refactoring (core implementation step)

---

### Pitfall 4: `lru_cache` on `get_config()` Prevents Per-User Dynamic Config

**What goes wrong:**

The current `config.py` uses `@lru_cache(maxsize=1)` on `get_config()`. This is correct for v1.0 where config is static. But if v1.1 tries to add any per-user or per-request configuration (e.g., per-user storage paths constructed in config), the cache returns the same config dict for every request. More subtly: if code modifies the returned dict (since dicts are mutable), the mutation persists in the cache and affects all subsequent callers.

**Why it happens:**

`lru_cache` returns the same object reference. The config dict is mutable. Any code that does `cfg["DATA_DIR"] = per_user_path` would corrupt the cached config for all users.

**Consequences:**

- All users see the same `DATA_DIR` (the one set by the first request)
- Or: the first user's path leaks to subsequent users via the mutated cache
- Difficult to debug because it depends on request ordering

**Prevention:**

Do NOT modify the cached config dict. Instead, compute per-user paths at the point of use:

```python
cfg = get_config()
base_dir = Path(cfg["DATA_DIR"])
user_dir = base_dir / username  # Compute per-user path from the static base
```

Never do `cfg["DATA_DIR"] = something_different`. The config should remain read-only and static. Per-user variation happens in the tool functions, not in config.

**Detection:**

- Code review: search for any mutation of the config dict
- Test with two different users in sequence -- verify each gets their own directory

**Phase to address:** Per-user isolation implementation (architecture decision -- keep config static, compute per-user paths in tools)

---

## Moderate Pitfalls

---

### Pitfall 5: Directory Auto-Creation Race Condition on First Write

**What goes wrong:**

The current code has `sketchpad_path.parent.mkdir(parents=True, exist_ok=True)` in `write_file()` but not in `read_file()`. When a new user's first action is to read (not write), there is no directory yet and the code tries to read from a nonexistent path. The v1.0 code handles this with a `WELCOME_MESSAGE` fallback, but this logic must survive the refactor. If the path construction changes but the `not sketchpad_path.exists()` check is missed, the server returns an error instead of the welcome message.

**Why it happens:**

Refactoring the path construction is the focus; the edge case of "first read before first write" is easy to overlook.

**Consequences:**

- New user's first `read_file()` call returns an error instead of the welcome message
- Minor but breaks the clean first-use experience

**Prevention:**

The `read_file()` function already handles the missing-file case. Ensure this logic is preserved during the refactor:

```python
if not sketchpad_path.exists():
    return WELCOME_MESSAGE
```

Add a test case: new user, read before write, verify welcome message.

**Detection:**

- Test: authenticate as a new user, call `read_file()` immediately, assert `WELCOME_MESSAGE`

**Phase to address:** Tool refactoring

---

### Pitfall 6: NFS Permission Issues with Per-User Subdirectories

**What goes wrong:**

The PVC is backed by NFS via `nfs-subdir-external-provisioner` on a Synology NAS. When the Python process calls `mkdir(parents=True, exist_ok=True)` to create a per-user subdirectory, NFS may reject the operation if the NFS export's permission settings are too restrictive. The container process runs as a non-root user (or the NFS export uses `root_squash`), and the process cannot create subdirectories in the PVC mount.

**Why it happens:**

In v1.0, the single `sketchpad.md` file was written directly in the PVC root (`/data/sketchpad.md`). This worked because the provisioner created the directory with appropriate permissions. In v1.1, the process needs to create subdirectories (`/data/hellothisisflo/sketchpad.md`), which requires write permission on the PVC root -- which may not be available if NFS permissions are restrictive.

**Consequences:**

- `PermissionError: [Errno 13] Permission denied: '/data/hellothisisflo'`
- Affects only the first write for each new user (after that, the directory exists)
- May work in local testing but fail in production on NFS

**Prevention:**

- Verify the NFS export allows the container's UID/GID to create subdirectories
- Set `securityContext.fsGroup` in the K8s deployment to match the NFS export's expected group
- Test directory creation on the actual NFS mount, not just local filesystem
- Consider adding a startup check that verifies write permissions on the data directory

**Detection:**

- Deploy v1.1, authenticate as a new user, attempt a write
- Check container logs for `PermissionError`
- Pre-flight check: `kubectl exec` into the pod and try `mkdir /data/test-dir`

**Phase to address:** Kubernetes deployment update (verify before release)

---

### Pitfall 7: Makefile `$(shell ...)` Becomes Backtick Evaluation in Just

**What goes wrong:**

The current Makefile uses `$(shell git rev-parse --short HEAD)` for dynamic variables. Just uses backticks for command evaluation: `` SHA := `git rev-parse --short HEAD` ``. If the developer translates `$(shell ...)` to `{{...}}` (Just's interpolation syntax), the command is treated as a variable reference, not a shell command. The build tag becomes a literal string like `sha-` (empty) instead of `sha-abc1234`.

**Why it happens:**

Makefile and Justfile use different syntax for different operations:
- Makefile: `$(shell cmd)` = execute command, `$(VAR)` = expand variable
- Justfile: `` `cmd` `` = execute command, `{{var}}` = expand variable

Muscle memory from Makefile leads to using `{{...}}` where backticks are needed.

**Consequences:**

- Docker image tagged as `sha-` (empty SHA) instead of `sha-abc1234`
- Pushes to registry overwrite the wrong tag
- Deploy command applies the wrong image

**Prevention:**

Direct translation of the existing Makefile:

```just
IMAGE  := "ghcr.io/hellothisisflo/sketchpad"
SHA    := `git rev-parse --short HEAD`
TAG    := "sha-" + SHA
NS     := "sketchpad"

build:
    docker buildx build --platform linux/amd64 -t {{IMAGE}}:{{TAG}} -t {{IMAGE}}:latest --load .
```

Note: strings in Just variable assignments need quotes. The backtick expression for `SHA` does not.

**Detection:**

- After conversion, run `just --evaluate` to see all computed variable values
- Verify `SHA` and `TAG` have correct values before running `build`

**Phase to address:** Makefile-to-Just migration

---

### Pitfall 8: Just Variable Syntax Requires Quotes for String Literals

**What goes wrong:**

In Makefile, `IMAGE := ghcr.io/hellothisisflo/sketchpad` works without quotes. In Just, unquoted values are parsed differently -- string literals must be quoted. Writing `IMAGE := ghcr.io/hellothisisflo/sketchpad` in a Justfile causes a parse error because `/` is not valid in a bare identifier.

**Why it happens:**

Just has stricter parsing than Make. Make treats everything after `:=` as a string. Just requires explicit string delimiters.

**Consequences:**

- Justfile fails to parse with a cryptic error
- All recipes are unavailable

**Prevention:**

Quote all string literal assignments:

```just
# Makefile (no quotes needed)
IMAGE := ghcr.io/hellothisisflo/sketchpad

# Justfile (quotes required)
IMAGE := "ghcr.io/hellothisisflo/sketchpad"
```

**Detection:**

- Run `just --list` immediately after conversion to verify the file parses
- Run `just --evaluate` to verify all variable values

**Phase to address:** Makefile-to-Just migration

---

### Pitfall 9: Just Recipes Run Each Line in a Separate Shell

**What goes wrong:**

By default, Just runs each line of a recipe in a separate shell invocation. This means `cd` in one line has no effect on the next line, and shell variables set in one line are not available in the next. This differs from Make, which also runs each line separately but where developers typically work around it with `&&` chains or backslash continuations.

The Makefile's `deploy` recipe uses two sequential commands (`kubectl apply` then `kubectl rollout status`). In Just, these work fine as independent commands because they don't share state. But if future recipes need `cd` or shell variable state across lines, this will bite.

**Why it happens:**

Just's design choice: each line is an independent shell invocation for reproducibility. Make does the same thing, so this is not actually a new behavior -- but developers who were using Make incorrectly (relying on implicit state sharing) will be surprised.

**Consequences:**

- For the current Makefile: no impact -- all recipes use independent commands
- For future recipes that need state across lines: unexpected behavior

**Prevention:**

For recipes needing shared state, use `set shell` or multi-line `&&` chains, or prefix the recipe with `#!/usr/bin/env bash` to run as a script.

The current Makefile recipes are simple enough that a direct translation works without changes.

**Detection:**

- Run each recipe after conversion and verify identical behavior
- Compare `just build` output to `make build` output

**Phase to address:** Makefile-to-Just migration

---

### Pitfall 10: GitHub Username Rename Orphans User Data

**What goes wrong:**

Per-user directories are named by GitHub `login` (e.g., `/data/hellothisisflo/`). If a user renames their GitHub account, their next authentication produces a different `login` claim. The old directory remains but is no longer accessible -- the user gets a fresh empty sketchpad.

**Why it happens:**

GitHub allows username changes. The `login` field in the API response reflects the current username, not the original. The numeric `sub` (user ID) is stable across renames, but numeric IDs are not human-readable for debugging.

**Consequences:**

- User loses access to their existing sketchpad data
- Old data is orphaned on disk (wasted space, potential confusion)
- No error -- the user simply sees a fresh welcome message

**Prevention:**

The PROJECT.md already documents this as an accepted trade-off: "Username rename = new sketchpad (acceptable)." This is the right call for a spike/personal project.

If this ever needs to be addressed:
- Use `sub` (numeric ID) for the directory name
- Store a `sub` -> `login` mapping file for human-readable display
- Or detect the orphan by checking for directories on disk that don't match any current user

For v1.1: accept the trade-off. Document it explicitly.

**Detection:**

- N/A for v1.1 (accepted behavior)

**Phase to address:** Out of scope for v1.1 (documented trade-off)

---

## Minor Pitfalls

---

### Pitfall 11: Just Not Installed on CI or Team Members' Machines

**What goes wrong:**

The project has GitHub Actions CI that currently does not use the Makefile (CI uses its own workflow). But if any contributor or automated process tries to run `just build` without `just` installed, they get `command not found`. Unlike `make`, which is pre-installed on most Unix systems, `just` requires explicit installation.

**Why it happens:**

`just` is not a standard Unix tool. It must be installed via `cargo install just`, `brew install just`, or a package manager.

**Consequences:**

- New contributors cannot run build commands without installing just
- CI pipelines break if they reference just commands without the install step

**Prevention:**

- Add a `just` installation step to CI if needed (or keep CI independent of the task runner)
- Document the install in the project README or contributing guide
- Consider keeping `Makefile` as a thin wrapper that delegates to `just` during transition (not recommended for this project -- clean cut is better)

**Detection:**

- Try running `just --list` on a fresh machine or in CI

**Phase to address:** Makefile-to-Just migration (documentation step)

---

### Pitfall 12: Removing `.PHONY` But Forgetting to Remove Makefile

**What goes wrong:**

After creating the Justfile, the old Makefile is left in the repo. Developers (or CI, or muscle memory) run `make build` instead of `just build`. Both work, but the Makefile stops getting updated while the Justfile evolves. Eventually they diverge, and someone runs the stale Makefile thinking it's current.

**Why it happens:**

Gradual migration -- "I'll delete it later."

**Consequences:**

- Confusion about which file is authoritative
- Stale Makefile produces incorrect builds

**Prevention:**

Delete the Makefile in the same commit that adds the Justfile. Clean cut. If you want a transition period, rename it to `Makefile.old` or add a deprecation message at the top.

**Detection:**

- Git: verify Makefile is removed in the migration commit

**Phase to address:** Makefile-to-Just migration (same commit as Justfile creation)

---

### Pitfall 13: `$` in Justfile Recipes Needs Escaping (for Environment Variables)

**What goes wrong:**

In Makefile recipes, you use `$$VAR` to reference shell environment variables (because `$VAR` is interpreted by Make). In Justfile recipes, `$VAR` is passed directly to the shell -- no doubling needed. If a developer converts the Makefile by removing the double-`$` (correct) but also adds double-`$` where it was not needed (incorrect), the recipe breaks.

**Why it happens:**

Inconsistent mental model during conversion. Make's `$$` -> shell's `$` mapping does not apply in Just.

**Consequences:**

- Shell commands that reference environment variables fail silently or expand incorrectly

**Prevention:**

The current Makefile does NOT use `$$` anywhere (all variable references use Make's `$(VAR)` syntax). So this is not an issue for the existing recipes -- but good to know for future recipes that reference environment variables.

**Detection:**

- Review: search for `$$` in the Justfile (should not exist unless intentional)

**Phase to address:** Makefile-to-Just migration (awareness only)

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| User identity extraction | Wrong claim key (Pitfall 2) | Use `TokenClaim("login")`, verify with logged claims |
| Per-user path construction | Path traversal (Pitfall 1) | `resolve()` + `is_relative_to()`, allowlist regex |
| Tool refactoring | Username exposed in tool schema (Pitfall 3) | Use DI, verify schema output |
| Tool refactoring | Welcome message regression (Pitfall 5) | Preserve `if not exists` check, add test |
| Config architecture | Mutating cached config (Pitfall 4) | Keep config static, compute per-user paths in tools |
| K8s deployment | NFS permission denied (Pitfall 6) | Test `mkdir` on NFS mount before release |
| Makefile to Just | Variable syntax (Pitfalls 7, 8) | Use `just --evaluate` to verify |
| Makefile to Just | Stale Makefile left behind (Pitfall 12) | Delete in same commit |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| FastMCP `TokenClaim` | Using `token.claims["username"]` (key does not exist for GitHub) | Use `TokenClaim("login")` -- the key is `"login"` for GitHubProvider |
| FastMCP DI | Adding `username` as a regular tool parameter | Use `= TokenClaim("login")` default to inject from auth context and hide from tool schema |
| `pathlib` path safety | String-checking for `../` in usernames | Use `Path.resolve()` + `is_relative_to()` -- handles symlinks and encoded traversals |
| NFS permissions | Assuming `mkdir` works because it worked locally | NFS exports have separate permission rules; test on actual mount |
| Just variable assignment | Writing `VAR := value` without quotes | Justfile requires `VAR := "value"` for string literals |
| Just command capture | Using `{{$(shell cmd)}}` like Makefile | Use backticks: `` VAR := `cmd` `` |
| Config mutation | Writing `cfg["DATA_DIR"] = per_user` on cached dict | Never mutate the config dict; compute derived paths in calling code |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| No path sanitization on username | Path traversal -> read/write any user's data | `resolve()` + `is_relative_to()` + allowlist regex |
| Using `name` claim instead of `login` | Display names contain spaces, Unicode, None | Always use `login` for GitHub, validate format |
| Exposing username as tool parameter | Claude sends arbitrary usernames, bypassing OAuth | Use FastMCP DI (`TokenClaim`), verify schema |
| Trusting that `get_access_token()` always returns a token | Returns `None` in STDIO mode or when auth is misconfigured | Use `TokenClaim` (raises `RuntimeError` if None) or check explicitly |
| Skipping path validation because "GitHub usernames are safe" | Works until you switch OAuth provider or GitHub changes rules | Always validate at point of use, defense-in-depth |

---

## "Looks Done But Isn't" Checklist

- [ ] **Tool schema:** `read_file` and `write_file` tool schemas do NOT list `username` as a parameter -- verify with `mcp.list_tools()` or schema inspection
- [ ] **Correct claim key:** Log `token.claims` during first test to confirm `"login"` contains the expected username
- [ ] **Path safety:** Unit test with `../other-user` as username -- must raise `ValueError`, not create the directory
- [ ] **Welcome message:** New user's first `read_file()` returns the welcome message, not an error
- [ ] **Directory creation:** First `write_file()` for a new user creates the user directory and file without errors
- [ ] **User isolation:** Two users authenticated with different GitHub accounts get different sketchpads
- [ ] **Justfile parses:** `just --list` succeeds and shows all recipes
- [ ] **Justfile equivalence:** `just build`, `just push`, `just deploy` produce identical results to the old `make` commands
- [ ] **Makefile removed:** Old Makefile is deleted or renamed
- [ ] **NFS permissions:** `write_file()` succeeds on the NFS-backed PVC in production, not just local testing

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Path traversal vulnerability discovered in production | MEDIUM | Add `resolve()` + `is_relative_to()` check; audit existing directories for suspicious names |
| Wrong claim key, all users share one directory | LOW | Fix claim key; existing single-directory data is only from one user anyway |
| Username exposed in tool schema | LOW | Add `TokenClaim` default; Claude will stop sending username on next session |
| NFS permission denied | LOW | Fix `securityContext.fsGroup` or NFS export permissions; redeploy |
| Justfile syntax errors | LOW | Fix syntax; no production impact (task runner is local only) |
| Config dict mutation | MEDIUM | Fix to compute paths in tools; restart server to clear LRU cache; verify no cross-user data corruption |

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Use `login` (mutable) instead of `sub` (stable) for directories | Human-readable directory names, easy debugging | Username rename orphans data | Acceptable for personal spike (documented in PROJECT.md) |
| Skip per-user disk quotas | No quota management code | One user could fill the PVC | Acceptable for personal server with 2-3 users |
| No migration of v1.0 data | Clean v1.1 start, no migration code | v1.0 sketchpad data is abandoned | Acceptable (documented as "fresh start" in PROJECT.md) |
| No username->sub mapping file | Simpler implementation | Cannot trace orphaned directories | Acceptable for spike |

---

## Sources

- FastMCP GitHubProvider source: `fastmcp/server/auth/providers/github.py` lines 130-143 (installed package, HIGH confidence -- directly verified claim keys)
- FastMCP `TokenClaim` dependency: `fastmcp/server/dependencies.py` lines 1370-1399 (installed package, HIGH confidence)
- FastMCP `get_access_token()` function: `fastmcp/server/dependencies.py` lines 469-480 (installed package, HIGH confidence)
- [FastMCP Authorization docs](https://gofastmcp.com/servers/authorization) -- HIGH confidence (official docs, verified against source)
- [FastMCP JWT Claims issue #1398](https://github.com/jlowin/fastmcp/issues/1398) -- HIGH confidence (closed/resolved, confirmed claims are available)
- [GitHub username regex](https://github.com/shinnn/github-username-regex) -- HIGH confidence (matches GitHub's documented rules: alphanumeric + hyphens, max 39 chars)
- [Python pathlib `is_relative_to`](https://docs.python.org/3/library/pathlib.html) -- HIGH confidence (official Python docs, Python 3.9+)
- [Preventing Directory Traversal in Python](https://salvatoresecurity.com/preventing-directory-traversal-vulnerabilities-in-python/) -- MEDIUM confidence (verified against pathlib docs)
- [NFS permissions in Kubernetes](https://github.com/kubernetes-sigs/nfs-subdir-external-provisioner/issues/158) -- MEDIUM confidence (community issue with verified workarounds)
- [Just manual](https://just.systems/man/en/) -- HIGH confidence (official docs)
- [Makefile to Justfile conversion issue #448](https://github.com/casey/just/issues/448) -- MEDIUM confidence (community experience)

---
*Pitfalls research for: v1.1 Multi-User Isolation (per-user storage, user identity extraction, Makefile-to-Just migration)*
*Researched: 2026-03-06*
