# Feature Landscape

**Domain:** Per-user storage isolation and build tooling migration for existing MCP server
**Researched:** 2026-03-06
**Confidence:** HIGH (FastMCP official docs verified, GitHub API constraints confirmed, Just manual reviewed)

**Scope note:** This research covers only v1.1 features. All v1.0 features (OAuth 2.1, MCP tools, K8s deployment) are already shipped and working.

---

## Table Stakes

Features required for the milestone to be considered complete. Missing any = milestone fails.

| Feature | Why Expected | Complexity | Dependencies |
|---------|--------------|------------|--------------|
| **User identity extraction from OAuth token** | Cannot isolate per-user without knowing who the user is. FastMCP exposes `get_access_token()` with `token.claims.get("login")` for GitHub username | LOW | Existing OAuth flow (v1.0) |
| **Per-user directory creation** | Each user needs their own storage folder. `DATA_DIR/<username>/sketchpad.md` is the natural path | LOW | User identity extraction |
| **Scoped read_file to authenticated user** | `read_file` must only read the calling user's file, not a shared file | LOW | Per-user directory structure |
| **Scoped write_file to authenticated user** | `write_file` must only write to the calling user's file, not a shared file | LOW | Per-user directory structure |
| **Path traversal prevention** | A username-derived path must be validated against directory escape. Even though GitHub usernames are safe (alphanumeric + hyphen only, 1-39 chars), defense in depth requires `Path.resolve()` validation against the base directory | LOW | Per-user directory structure |
| **Justfile replacing Makefile** | PROJECT.md lists Makefile-to-Just migration as a v1.1 requirement | LOW | Just installed on dev machine |

### Implementation Details

#### User Identity Extraction

FastMCP's `get_access_token()` is the API. Available via `from fastmcp.server.dependencies import get_access_token`. The GitHubProvider stores the full GitHub `/user` API response in `token.claims`.

Key claims from GitHub:
- `login` -- the GitHub username (use this for directory names)
- `name` -- display name (may be null)
- `email` -- email (may be null if user hides it)
- `id` -- numeric GitHub user ID (stable across renames)

**Recommendation:** Use `login` for directory names. It is human-readable and filesystem-safe by GitHub's own constraints (alphanumeric + single hyphens, no leading/trailing hyphens, max 39 chars). The PROJECT.md already decided this and notes "Username rename = new sketchpad (acceptable)."

**Confidence:** HIGH -- verified via FastMCP official docs at gofastmcp.com/integrations/github and gofastmcp.com/servers/authorization.

#### Per-User Directory Layout

Current (v1.0):
```
DATA_DIR/
  sketchpad.md          # single shared file
```

Target (v1.1):
```
DATA_DIR/
  hellothisisflo/
    sketchpad.md        # Flo's sketchpad
  another-user/
    sketchpad.md        # another user's sketchpad
```

The tools create the user directory on first write via `mkdir(parents=True, exist_ok=True)` -- already used in v1.0 for the data dir itself.

#### Path Traversal Defense

Even though GitHub usernames cannot contain `/`, `..`, or other traversal characters, the server should validate the resolved path:

```python
user_dir = (Path(data_dir) / username).resolve()
base_dir = Path(data_dir).resolve()
if not str(user_dir).startswith(str(base_dir)):
    raise ValueError("Path traversal detected")
```

This is defense-in-depth. If the identity provider ever changes (PROJECT.md already supports Google), the username format may differ.

**Confidence:** HIGH -- standard Python security pattern, documented by OpenStack and PortSwigger.

#### Justfile Migration

The current Makefile has 6 targets: `build`, `push`, `deploy`, `restart`, `all`, `status`. Direct translation to Just:

| Makefile Pattern | Justfile Equivalent |
|------------------|---------------------|
| `VAR := $(shell cmd)` | `` VAR := `cmd` `` (backtick evaluation) |
| `.PHONY: target` | Not needed (Just is a command runner, not a build system) |
| `target: dep1 dep2` | `target: dep1 dep2` (same syntax) |
| `$(VAR)` in recipe | `{{VAR}}` in recipe |
| Tabs required | Spaces or tabs accepted |

Just advantages over Make for this project:
- `just --list` shows all recipes with descriptions (no grepping)
- No `.PHONY` boilerplate
- Cleaner variable syntax
- Recipe parameters (useful for future `deploy TAG` patterns)
- Same syntax across macOS and Linux

**Confidence:** HIGH -- verified via Just manual at just.systems/man/en/ and cheat sheet.

---

## Differentiators

Features that add value beyond the core requirements. Not required for the milestone but worth considering.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Numeric ID fallback for directory naming** | GitHub's numeric `id` is stable across username renames. Could use `id` as the actual directory name with a `login` symlink or metadata file | MEDIUM | Adds complexity for a rare edge case. PROJECT.md explicitly accepts "rename = new sketchpad." Skip unless multiple users are expected |
| **`whoami` tool** | A tool that returns the authenticated user's GitHub login, so Claude can confirm identity in conversations | LOW | Trivial to implement: `return token.claims.get("login")`. Useful for debugging and user confirmation |
| **Storage quota per user** | Cap total file size per user to prevent PVC exhaustion | LOW | Already have `SIZE_LIMIT` config (50KB). Just enforce it at write time. More important with multiple users sharing a PVC |
| **Justfile recipe for local dev** | `just dev` to run the server locally with hot reload | LOW | Useful for development workflow. `just dev` = `uv run fastmcp dev src/sketchpad/server.py` |
| **Justfile recipe for running tests** | `just test` to run the test suite | LOW | `just test` = `uv run pytest` |
| **Justfile `--list` descriptions** | Add comment annotations to recipes for `just --list` output | LOW | Just supports `# comment above recipe` for descriptions |

---

## Anti-Features

Features to explicitly NOT build in v1.1. These are scope traps.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Cross-user file sharing** | PROJECT.md: "User collaboration/sharing -- each user's sketchpad is fully isolated" | Complete isolation. No mechanism to read another user's files |
| **User management admin UI** | PROJECT.md: "No admin UI, users are self-service via OAuth" | Users self-provision by authenticating. Directory created on first write |
| **File listing / multi-file support** | PROJECT.md: "Obsidian vault logic (search, listing, multiple files) -- that's the next project" | Single file per user, same as v1.0 but scoped |
| **Migration of v1.0 shared file** | PROJECT.md: "Fresh start for v1.1. No migration of v1.0 single-user data" | Clean slate. Old `DATA_DIR/sketchpad.md` can be deleted or ignored |
| **Database-backed user registry** | Overkill. Users exist implicitly by having a directory. No need to track users in a DB | Directory existence = user exists. `os.listdir(DATA_DIR)` = list of users |
| **Per-user quotas with enforcement** | Unnecessary complexity for a personal server with a few users | The existing `SIZE_LIMIT` warning is sufficient. No hard enforcement needed |
| **Role-based access control (RBAC)** | All authenticated users have equal access to their own sketchpad. No admin/viewer distinction needed | Flat permission model: authenticated = full access to own sketchpad |
| **Consent screen per user** | PROJECT.md: "Consent UI / approval screen -- single-user personal server" -- still applies even with multi-user, since this is personal infra | Auto-approve. Any valid GitHub user who completes OAuth gets a sketchpad |
| **CI/CD changes for Just** | GitHub Actions CI already works with `docker buildx`. Just is for local dev workflow only. The CI pipeline does not use Make either | Keep CI as-is. Justfile is local-only |
| **Username allowlisting** | Tempting but unnecessary. The server is behind Cloudflare Tunnel on a personal domain. OAuth with GitHub is sufficient access control | If access restriction is ever needed, add it as a separate feature |

---

## Feature Dependencies

```
OAuth token (existing v1.0)
  └── get_access_token() in tool function
        └── Extract username from token.claims["login"]
              └── Construct per-user directory path: DATA_DIR/<username>/
                    ├── read_file reads DATA_DIR/<username>/sketchpad.md
                    └── write_file writes DATA_DIR/<username>/sketchpad.md

Path traversal validation
  └── Applied BEFORE any filesystem operation
        └── Validates resolved path is within DATA_DIR

Justfile (independent of above)
  └── Translates existing Makefile targets 1:1
        └── No functional change, only DX improvement
```

### Dependency Notes

- **User identity is the keystone.** Everything depends on extracting the username from the OAuth token. If `get_access_token()` does not return the GitHub `login` claim, nothing else works. This is verified to work in FastMCP with GitHubProvider.
- **Directory creation is implicit.** No setup step needed. `mkdir(parents=True, exist_ok=True)` on first write creates the user's directory.
- **Just migration is independent.** It has zero interaction with the per-user isolation work. Can be done in parallel or in any order.
- **PVC is shared.** Both user directories live on the same PersistentVolumeClaim (`sketchpad-data`). No K8s changes needed -- the PVC already mounts at `DATA_DIR`.

---

## MVP Recommendation

### Must Ship (v1.1 milestone requirements)

1. **User identity extraction** -- `get_access_token()` + `token.claims.get("login")` in tool functions
2. **Per-user directory scoping** -- `DATA_DIR/<username>/sketchpad.md` path construction
3. **Path traversal guard** -- `resolve()` + prefix check before any filesystem access
4. **Justfile** -- 1:1 translation of existing Makefile targets

### Should Ship (low effort, high value)

5. **`whoami` tool** -- 5 lines of code, useful for debugging multi-user
6. **`just dev` and `just test` recipes** -- improve developer workflow

### Defer

- **Numeric ID-based directories** -- only matters if username renames become a problem
- **Storage quotas** -- only matters if PVC usage becomes a concern
- **Username allowlisting** -- only matters if unwanted users become a problem

---

## Complexity Assessment

| Feature | Lines of Code (est.) | Risk | Notes |
|---------|---------------------|------|-------|
| User identity extraction | ~5 | LOW | Well-documented FastMCP API |
| Per-user directory scoping | ~10 | LOW | Change path construction in `read_file` and `write_file` |
| Path traversal guard | ~5 | LOW | Standard `Path.resolve()` pattern |
| Justfile | ~30 | LOW | Direct syntax translation from existing Makefile |
| `whoami` tool | ~5 | LOW | New tool, trivial implementation |

**Total estimated change:** ~55 lines of code. This is a small, well-scoped milestone.

---

## Sources

- FastMCP Authorization docs: https://gofastmcp.com/servers/authorization -- HIGH confidence
- FastMCP GitHub Integration: https://gofastmcp.com/integrations/github -- HIGH confidence
- FastMCP get_access_token() API: https://gofastmcp.com/servers/authorization -- HIGH confidence
- FastMCP JWT claims issue (resolved): https://github.com/jlowin/fastmcp/issues/1398 -- HIGH confidence
- GitHub username constraints: https://github.com/shinnn/github-username-regex -- HIGH confidence
- GitHub REST API /user fields: https://docs.github.com/en/rest/users -- HIGH confidence
- Just task runner manual: https://just.systems/man/en/ -- HIGH confidence
- Just vs Make comparison: https://spin.atomicobject.com/just-task-runner/ -- MEDIUM confidence
- Justfile cheat sheet: https://cheatography.com/linux-china/cheat-sheets/justfile/ -- MEDIUM confidence
- Path traversal prevention (Python): https://salvatoresecurity.com/preventing-directory-traversal-vulnerabilities-in-python/ -- HIGH confidence
- OpenStack path security guide: https://security.openstack.org/guidelines/dg_using-file-paths.html -- HIGH confidence
- MCP multi-tenant patterns: https://bix-tech.com/multi-user-ai-agents-with-an-mcp-server-a-practical-blueprint-for-secure-scalable-collaboration/ -- MEDIUM confidence

---
*Feature research for: Sketchpad v1.1 -- Per-user isolation and Just migration*
*Researched: 2026-03-06*
