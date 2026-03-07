# Phase 5: Per-User Storage Isolation - Research

**Researched:** 2026-03-06
**Domain:** User identity extraction, filesystem isolation, path security
**Confidence:** HIGH

## Summary

Per-user storage isolation requires three capabilities: (1) extracting the authenticated user's identity from the OAuth token inside tool functions, (2) mapping that identity to a filesystem-safe directory path, and (3) defending against path traversal attacks. All three are well-supported by the existing stack.

FastMCP 3.1.0 provides `get_access_token()` which exposes `token.claims["login"]` -- the GitHub username. GitHub usernames are restricted to `[a-zA-Z0-9-]` (alphanumeric + hyphens, max 39 chars), which means they are **already filesystem-safe** and no slugify library is needed. The only sanitization required is lowercasing (GitHub usernames are case-insensitive but case-preserving) plus a regex validation guard. Path traversal defense uses Python's `Path.resolve()` + `is_relative_to()` pattern, available since Python 3.9 (project requires 3.12+).

**Primary recommendation:** Use `get_access_token().claims["login"].lower()` for the username, validate with regex `^[a-z0-9]([a-z0-9-]*[a-z0-9])?$`, and use `Path.resolve()` + `is_relative_to()` as defense-in-depth against path traversal.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Username sanitization: prefer library (e.g., python-slugify) over hand-rolled -- researcher makes final call on whether library is truly needed or overkill
- Sanitization must be idempotent: `sanitize(sanitize(x)) == sanitize(x)`
- Sanitization must be injective within a provider: two distinct usernames must not map to the same folder
- No dependency aversion -- adding a package is fine if it solves the problem cleanly
- Folder layout: `/data/{provider}/{identifier}/sketchpad.md`
- Phase 5 implements GitHub only, but structures code so adding a new provider is straightforward
- Update tool descriptions to convey: personal to you, shared across all your AI agents
- Username hidden from JSON schema -- extracted server-side from OAuth token
- Tool responses do NOT include the username
- Welcome message stays generic for all users
- Trust FastMCP's auth layer to reject unauthenticated requests
- Add defensive assertion for missing username -- treat as internal error
- Never fall back to anonymous/shared sketchpad
- Path traversal attempts: return generic "Invalid request" error
- Log path traversal attempts at WARNING level server-side

### Claude's Discretion
- Exact tool description wording (within the personal-but-cross-agent framing)
- Internal code structure for provider-to-folder mapping (as long as adding providers is straightforward)
- Whether to use python-slugify or a simpler approach (after research)

### Deferred Ideas (OUT OF SCOPE)
- Test Cursor as a second MCP client (user interest, not part of this phase)
- Google OAuth provider implementation (future phase, folder structure is ready for it)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ISOL-01 | Each authenticated user's sketchpad stored in per-user directory derived from OAuth identity | `get_access_token().claims["login"]` provides GitHub username; folder path becomes `DATA_DIR / provider / sanitized_login / SKETCHPAD_FILENAME` |
| ISOL-02 | Path traversal prevented via `Path.resolve()` + `is_relative_to()` defense-in-depth | Both methods available in Python 3.12+; standard pattern documented below |
| ISOL-03 | User directory auto-created on first `write_file` call | Existing code already uses `mkdir(parents=True, exist_ok=True)` -- extend to deeper path |
| ISOL-04 | Username sanitized to filesystem-safe characters before use as directory name | GitHub usernames are `[a-zA-Z0-9-]` -- already safe; lowercasing + regex guard is sufficient (no library needed) |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastmcp | 3.1.0 | MCP server + OAuth + user identity | Already in use; `get_access_token()` provides token claims |
| pathlib (stdlib) | Python 3.12 | Path construction, traversal defense | `Path.resolve()` + `is_relative_to()` is the standard Python pattern |
| re (stdlib) | Python 3.12 | Username validation regex | Lightweight guard; no external dependency needed |
| logging (stdlib) | Python 3.12 | WARNING-level logging for path traversal attempts | Already used in middleware.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-slugify | 8.0+ | Unicode-to-ASCII slug generation | **NOT recommended for this phase** -- see research below |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Regex + lowercase | python-slugify | python-slugify is NOT injective (violates ISOL-04 hard requirement); GitHub usernames are already filesystem-safe, making slugify unnecessary overhead |
| Regex + lowercase | pathvalidate | pathvalidate sanitizes for OS constraints but doesn't guarantee injectivity either; GitHub's character set makes this unnecessary |

### No New Dependencies Needed

The researcher's recommendation (as authorized by CONTEXT.md) is that **no slugify library is needed**. Reasoning:

1. **GitHub usernames only contain `[a-zA-Z0-9-]`** -- alphanumeric characters and hyphens, max 39 characters. These are already valid on every filesystem (Linux, macOS, Windows).
2. **python-slugify is NOT injective** -- it normalizes Unicode, removes special characters, and lowercases, meaning different inputs can produce identical slugs. This violates the hard requirement that two distinct usernames must not map to the same folder.
3. **Lowercasing IS injective within GitHub** -- GitHub usernames are case-insensitive (you cannot register `Flo` if `flo` exists), so `str.lower()` maps GitHub's case-insensitive namespace to a unique lowercase directory name.
4. **Idempotency is satisfied** -- `"flo".lower() == "flo"` and `"FLO".lower().lower() == "flo"`.

For **future providers** (e.g., Google `sub` claim, which is a numeric string), the provider-specific sanitizer can be different. The architecture should define a per-provider `sanitize_identifier(raw: str) -> str` function.

## Architecture Patterns

### Recommended Project Structure
```
src/sketchpad/
├── __init__.py
├── __main__.py          # Entry point (unchanged)
├── config.py            # Add provider identifier config
├── middleware.py         # Unchanged
├── server.py            # Wire user identity into tools
├── tools.py             # Accept user identity, build per-user paths
└── user_identity.py     # NEW: sanitize + resolve user path
```

### Pattern 1: User Identity Extraction via get_access_token()
**What:** FastMCP's dependency injection provides the authenticated user's token claims inside any `@mcp.tool` function.
**When to use:** Every tool function that needs to know "who is calling."
**Example:**
```python
# Source: https://gofastmcp.com/servers/authorization
from fastmcp.server.dependencies import get_access_token

@mcp.tool
def read_file() -> str:
    """Read your personal sketchpad..."""
    token = get_access_token()
    if token is None:
        raise RuntimeError("Authentication required")
    login = token.claims.get("login")
    if not login:
        raise RuntimeError("Missing user identity in token")
    # login is the GitHub username, e.g., "Flo" or "octocat"
```

**Key detail:** `get_access_token()` uses Python's `contextvars` -- it works without being passed as a parameter and does NOT appear in the tool's JSON schema. This satisfies the requirement that the username is hidden from Claude AI.

### Pattern 2: Provider-Scoped Directory Resolution
**What:** Map (provider, identifier) to a filesystem path, with path traversal defense.
**When to use:** Before any file I/O in tool functions.
**Example:**
```python
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# GitHub username rules: alphanumeric + hyphens, 1-39 chars,
# no leading/trailing hyphens, no consecutive hyphens
GITHUB_USERNAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")

def resolve_user_dir(
    data_dir: str,
    provider: str,
    raw_identifier: str,
) -> Path:
    """Resolve a user's data directory with sanitization and traversal defense.

    Raises ValueError for invalid identifiers or path traversal attempts.
    """
    # Step 1: Provider-specific sanitization
    if provider == "github":
        identifier = raw_identifier.lower()
        if not GITHUB_USERNAME_RE.match(identifier) or len(identifier) > 39:
            logger.warning("Invalid GitHub username attempted: %s", raw_identifier)
            raise ValueError("Invalid request")
    else:
        raise ValueError(f"Unknown provider: {provider}")

    # Step 2: Construct path
    base = Path(data_dir).resolve()
    user_dir = (base / provider / identifier).resolve()

    # Step 3: Defense-in-depth -- verify path stays within base
    if not user_dir.is_relative_to(base):
        logger.warning("Path traversal attempt: %s", raw_identifier)
        raise ValueError("Invalid request")

    return user_dir
```

### Pattern 3: Extracting Identity Without Schema Exposure
**What:** Tool functions call `get_access_token()` internally -- the username never appears as a tool parameter.
**When to use:** Always -- the user decided username must be invisible to Claude AI.
**Example:**
```python
@mcp.tool
def read_file() -> str:
    """Read your personal sketchpad. This is your private Markdown file..."""
    token = get_access_token()
    # token is injected by FastMCP's context system
    # It does NOT appear in the tool's JSON schema
    login = token.claims["login"]
    user_dir = resolve_user_dir(cfg["DATA_DIR"], cfg["OAUTH_PROVIDER"], login)
    sketchpad_path = user_dir / cfg["SKETCHPAD_FILENAME"]
    ...
```

### Anti-Patterns to Avoid
- **Username as tool parameter:** Never add `username` to the tool function signature -- it would appear in the JSON schema and Claude AI could override it.
- **Falling back to shared storage:** Never use a default/anonymous path when authentication is missing. Raise an error instead.
- **Case-sensitive directory names:** Always lowercase GitHub usernames before using as directory names. `Flo/` and `flo/` would be the same user on GitHub but different dirs on Linux.
- **Trusting raw claims blindly:** Even though GitHub's character set is safe, validate with regex as defense-in-depth. A bug in FastMCP or a misconfigured provider could inject unexpected characters.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth user identity extraction | Custom JWT parsing, GitHub API calls | `get_access_token().claims["login"]` | FastMCP already fetches GitHub user info and stores it in token claims |
| Path traversal prevention | Custom string sanitization of `../` | `Path.resolve()` + `is_relative_to()` | Handles all edge cases: encoded sequences, symlinks, Unicode normalization |
| OAuth authentication check | Manual token validation in tools | FastMCP's auth layer (trusted per CONTEXT.md) | Auth happens before tool functions are called |

**Key insight:** The two hardest problems (OAuth identity extraction and path traversal defense) are both solved by existing stdlib/framework features. The only custom code needed is the ~20-line `resolve_user_dir()` function that ties them together.

## Common Pitfalls

### Pitfall 1: Case-Sensitive Directory Names on Linux
**What goes wrong:** User "Flo" and "flo" are the same GitHub account but create different directories on case-sensitive filesystems (Linux ext4, NFS).
**Why it happens:** GitHub API returns the case-preserved `login` value (e.g., "Flo" not "flo").
**How to avoid:** Always lowercase the login before using as directory name: `login.lower()`.
**Warning signs:** User can't find their data after GitHub display name case change.

### Pitfall 2: Forgetting Defense-in-Depth on Path Traversal
**What goes wrong:** Relying only on regex validation, which might have edge cases (Unicode normalization, null bytes).
**Why it happens:** "GitHub usernames are safe" feels sufficient.
**How to avoid:** Always apply BOTH regex validation AND `Path.resolve()` + `is_relative_to()` check. Belt and suspenders.
**Warning signs:** Any path that resolves outside `DATA_DIR` is a bug.

### Pitfall 3: Single-Character GitHub Usernames
**What goes wrong:** Regex `^[a-z0-9]([a-z0-9-]*[a-z0-9])?$` -- the middle group is optional, so single-char usernames like `"a"` match correctly. But make sure to test this edge case.
**Why it happens:** GitHub allows single-character usernames (e.g., user `"a"` exists).
**How to avoid:** Write explicit test for single-character username.
**Warning signs:** Regex fails to match valid single-char login.

### Pitfall 4: get_access_token() Returns None in STDIO Mode
**What goes wrong:** During local development with STDIO transport, `get_access_token()` returns `None` because there's no OAuth in STDIO mode.
**Why it happens:** Auth is only available with HTTP transport.
**How to avoid:** The defensive assertion for missing username (required by CONTEXT.md) handles this: raise RuntimeError, never fall back.
**Warning signs:** Tool function silently uses shared storage instead of per-user.

### Pitfall 5: lru_cache on get_config() and Provider Switching
**What goes wrong:** `get_config()` is cached with `@lru_cache(maxsize=1)`. The `OAUTH_PROVIDER` value is baked in at first call. This is fine for production (single provider per deployment) but be aware in tests.
**Why it happens:** Cache was designed for single-deployment use.
**How to avoid:** No action needed for this phase. Just be aware when writing tests -- may need to clear cache.
**Warning signs:** Tests interfering with each other due to cached config.

## Code Examples

Verified patterns from official sources:

### Accessing User Identity in a Tool
```python
# Source: https://gofastmcp.com/servers/authorization
# Source: https://gofastmcp.com/integrations/github
from fastmcp.server.dependencies import get_access_token

@mcp.tool
def read_file() -> str:
    """Read your personal sketchpad. This is your private Markdown file,
    shared across all your AI agents (Claude, Cursor, etc.) that use
    the same GitHub identity."""
    token = get_access_token()
    assert token is not None, "Internal error: missing authentication context"
    login = token.claims.get("login")
    assert login, "Internal error: missing user identity in token"
    # login is case-preserved, e.g., "Flo"
    ...
```

### Path Traversal Defense
```python
# Source: https://docs.python.org/3.12/library/pathlib.html
from pathlib import Path

def safe_user_path(data_dir: str, provider: str, identifier: str, filename: str) -> Path:
    base = Path(data_dir).resolve()
    target = (base / provider / identifier / filename).resolve()

    if not target.is_relative_to(base):
        raise ValueError("Invalid request")

    return target
```

### Provider-Specific Identifier Strategy
```python
# Extensible pattern for future providers
PROVIDER_CONFIGS = {
    "github": {
        "claim_key": "login",       # GitHub API field
        "sanitize": lambda raw: raw.lower(),
        "validate": lambda s: bool(GITHUB_USERNAME_RE.match(s)) and len(s) <= 39,
    },
    # Future: "google": {"claim_key": "sub", "sanitize": ..., "validate": ...}
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual JWT decoding in tools | `get_access_token()` dependency injection | FastMCP 3.0.0+ (mid-2025) | No need to parse JWTs manually |
| AccessToken without claims | AccessToken.claims dict | FastMCP PR #1399 (Aug 2025) | GitHub user info available in tool functions |
| Custom path sanitization | `Path.resolve()` + `is_relative_to()` | Python 3.9+ (2020) | stdlib solution, no custom traversal defense needed |

**Deprecated/outdated:**
- Accessing user info via custom middleware or request parsing -- use `get_access_token()` instead
- `TokenClaim("login")` mentioned in REQUIREMENTS.md -- this is not a real FastMCP API. The correct API is `get_access_token().claims["login"]`

## Open Questions

1. **NFS subdirectory permissions on Synology NAS**
   - What we know: The project uses NFS-backed PVCs on Kubernetes. Data is written to `/data/`.
   - What's unclear: Whether the NFS server allows the container's UID to create subdirectories (`/data/github/flo/`) at runtime.
   - Recommendation: This cannot be resolved by research -- must be tested empirically during deployment. If permissions fail, the container's entrypoint or PVC config may need adjustment. Flagged in STATE.md as existing blocker.

2. **Exact token.claims keys from GitHub**
   - What we know: `login`, `name`, `email` are documented. The `login` field is the GitHub username.
   - What's unclear: Whether FastMCP passes through ALL GitHub `/user` API fields or only a subset.
   - Recommendation: Only `login` is needed. If it's missing, the defensive assertion will catch it immediately. LOW risk.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (not yet configured) |
| Config file | none -- see Wave 0 |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ISOL-01 | User's sketchpad stored in per-user directory | unit | `uv run pytest tests/test_user_isolation.py::test_user_path_resolution -x` | No -- Wave 0 |
| ISOL-01 | Two users see different sketchpads | unit | `uv run pytest tests/test_user_isolation.py::test_two_users_isolated -x` | No -- Wave 0 |
| ISOL-02 | Path traversal blocked by resolve+is_relative_to | unit | `uv run pytest tests/test_user_isolation.py::test_path_traversal_blocked -x` | No -- Wave 0 |
| ISOL-02 | Traversal attempt logged at WARNING | unit | `uv run pytest tests/test_user_isolation.py::test_traversal_logged -x` | No -- Wave 0 |
| ISOL-03 | User dir auto-created on first write | unit | `uv run pytest tests/test_user_isolation.py::test_auto_create_dir -x` | No -- Wave 0 |
| ISOL-04 | Username lowercased for directory | unit | `uv run pytest tests/test_user_isolation.py::test_username_lowercased -x` | No -- Wave 0 |
| ISOL-04 | Invalid username rejected | unit | `uv run pytest tests/test_user_isolation.py::test_invalid_username_rejected -x` | No -- Wave 0 |
| ISOL-04 | Sanitization is idempotent | unit | `uv run pytest tests/test_user_isolation.py::test_sanitize_idempotent -x` | No -- Wave 0 |
| ISOL-04 | Sanitization is injective | unit | `uv run pytest tests/test_user_isolation.py::test_sanitize_injective -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/` directory -- does not exist yet
- [ ] `tests/test_user_isolation.py` -- covers ISOL-01 through ISOL-04
- [ ] `tests/conftest.py` -- shared fixtures (tmp data dir, mock token, mock config)
- [ ] pytest configuration in `pyproject.toml`: `[tool.pytest.ini_options]` with `testpaths = ["tests"]`
- [ ] pytest dependency: add `pytest` to dev dependencies (or inline script metadata for uv)

## Sources

### Primary (HIGH confidence)
- [FastMCP Authorization docs](https://gofastmcp.com/servers/authorization) -- `get_access_token()` API, AccessToken class structure
- [FastMCP GitHub Integration](https://gofastmcp.com/integrations/github) -- GitHubProvider claims: `login`, `name`, `email`
- [FastMCP Issue #1398 / PR #1399](https://github.com/jlowin/fastmcp/issues/1398) -- JWT claims added to AccessToken, merged Aug 2025
- [Python pathlib docs](https://docs.python.org/3.12/library/pathlib.html) -- `Path.resolve()`, `is_relative_to()` available since 3.9
- [GitHub username rules](https://docs.github.com/en/enterprise-cloud@latest/admin/managing-iam/iam-configuration-reference/username-considerations-for-external-authentication) -- `[a-zA-Z0-9-]`, max 39 chars, no leading/trailing/consecutive hyphens

### Secondary (MEDIUM confidence)
- [GitHub username regex (npm)](https://github.com/shinnn/github-username-regex) -- confirms `^[a-z\d](?:[a-z\d]|-(?=[a-z\d])){0,38}$` pattern
- [GitHub API case sensitivity](https://github.com/integrations/terraform-provider-github/issues/196) -- usernames are case-insensitive but case-preserving
- [python-slugify PyPI](https://pypi.org/project/python-slugify/) -- NOT injective by design (collisions expected)

### Tertiary (LOW confidence)
- None -- all findings verified with primary or secondary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- FastMCP 3.1.0 API verified via official docs and issue tracker
- Architecture: HIGH -- Pattern uses stdlib + existing framework features, no novel design
- Pitfalls: HIGH -- GitHub username rules well-documented, path traversal defense is a standard Python pattern
- Sanitization recommendation: HIGH -- GitHub's restricted character set makes the decision clear-cut

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (stable domain -- GitHub username rules and Python pathlib are not changing)
