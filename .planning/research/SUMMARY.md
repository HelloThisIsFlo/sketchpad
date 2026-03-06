# Project Research Summary

**Project:** Sketchpad v1.1 Multi-Users
**Domain:** Per-user storage isolation + build tooling migration for existing MCP server
**Researched:** 2026-03-06
**Confidence:** HIGH

## Executive Summary

Sketchpad v1.1 adds per-user storage isolation to an already-working MCP server. The core change is small: extract the GitHub username from the OAuth token via FastMCP's built-in dependency injection (`TokenClaim("login")`), then scope file paths to `DATA_DIR/{username}/sketchpad.md` instead of a shared file. All four research tracks converge on the same conclusion -- this is a ~55 lines-of-code change concentrated in a single file (`tools.py`), with a parallel Makefile-to-Just migration that has zero functional overlap with the isolation work.

The recommended approach uses FastMCP 3.1.0's `TokenClaim("login")` dependency injection, which is already installed and verified working. This pattern injects the GitHub username as a hidden parameter that never appears in the tool's JSON schema (Claude AI cannot see or override it). No new Python packages are required. The Justfile is a direct 1:1 syntax translation of the existing 6-recipe Makefile with cleaner syntax and no `.PHONY` boilerplate.

The primary risk is path traversal via unsanitized usernames. Although GitHub usernames are restricted to `[a-zA-Z0-9-]` today, defense-in-depth requires `Path.resolve()` + `is_relative_to()` validation at the point of path construction. The second risk is NFS permission issues when creating per-user subdirectories on the production PVC, which worked for the v1.0 single-file layout but needs verification for subdirectory creation. Both risks have straightforward mitigations documented in the research.

## Key Findings

### Recommended Stack

No new dependencies. Everything needed is already installed.

**Core technologies:**
- **`TokenClaim("login")`** (FastMCP 3.1.0): Injects GitHub username into tool handlers via DI, hidden from tool schema, raises `RuntimeError` if claim missing
- **`pathlib.Path.resolve()` + `is_relative_to()`** (Python 3.12 stdlib): Defense-in-depth path traversal prevention at the point of filesystem access
- **Just 1.46.0** (casey/just): Purpose-built command runner replacing Makefile; no `.PHONY`, cleaner variable syntax, `just --list` for discoverability

### Expected Features

**Must have (table stakes):**
- User identity extraction from OAuth token via `TokenClaim("login")`
- Per-user directory creation: `DATA_DIR/{username}/sketchpad.md`
- Scoped `read_file` and `write_file` to authenticated user only
- Path traversal prevention with `resolve()` + `is_relative_to()`
- Justfile replacing Makefile with 1:1 recipe translation

**Should have (low effort, high value):**
- `whoami` tool (~5 LOC) for debugging multi-user identity
- `just dev` and `just test` convenience recipes

**Defer (v2+):**
- Numeric ID-based directories for username-rename resilience
- Per-user storage quotas with enforcement
- Username allowlisting
- Cross-user sharing, admin UI, multi-file support

### Architecture Approach

The change is surgically scoped: only `tools.py` gains user awareness. The existing OAuth flow, FastMCP middleware, server factory, config system, and Kubernetes infrastructure remain untouched. Per-user isolation is a tool-level concern, not a server-level concern. The `config.py` stays read-only and static; per-user paths are computed at the point of use inside tool handlers. User directories are created lazily on first write via the existing `mkdir(parents=True, exist_ok=True)` call.

**Major components (what changes):**
1. **`tools.py`** -- Adds `username: str = TokenClaim("login")` to tool handlers, changes path from `DATA_DIR/sketchpad.md` to `DATA_DIR/{username}/sketchpad.md`
2. **`justfile`** (new) -- 1:1 translation of Makefile recipes with Just syntax
3. **`Makefile`** (deleted) -- Removed in same commit as justfile creation

**Everything else unchanged:** `server.py`, `config.py`, `middleware.py`, K8s manifests, PVCs, Dockerfile, CI workflow.

### Critical Pitfalls

1. **Path traversal via unsanitized username** -- Validate with `Path.resolve()` + `is_relative_to()` and an allowlist regex `^[a-zA-Z0-9][a-zA-Z0-9-]{0,38}$` before any filesystem operation. Defense-in-depth against future OAuth provider changes.
2. **Wrong claim key from OAuth token** -- The key is `"login"`, not `"username"` or `"preferred_username"`. Use `TokenClaim("login")` which fails fast with `RuntimeError` if the claim is missing.
3. **Username exposed in tool schema** -- If `username` is added as a regular parameter (not via DI), Claude AI can send arbitrary usernames, bypassing OAuth. Must use `TokenClaim("login")` default to hide from schema.
4. **Mutating cached config dict** -- `get_config()` uses `@lru_cache`. Never write `cfg["DATA_DIR"] = per_user_path`. Compute per-user paths in tool functions from the static base `DATA_DIR`.
5. **NFS permission denied for subdirectory creation** -- v1.0 only wrote to the PVC root. v1.1 creates subdirectories, which may fail on NFS. Verify with `kubectl exec` before release.

## Implications for Roadmap

Based on research, this milestone naturally splits into two independent workstreams plus validation. The total change is ~55 LOC -- do not over-phase this.

### Phase 1: Per-User Storage Isolation
**Rationale:** This is the core feature and the only code change with security implications. It must come first so tests can be written and validated before anything else.
**Delivers:** User-isolated sketchpads -- each authenticated user reads/writes only their own file.
**Addresses:** User identity extraction, per-user directory scoping, path traversal prevention, scoped `read_file` and `write_file`.
**Avoids:** Path traversal (Pitfall 1), wrong claim key (Pitfall 2), username in tool schema (Pitfall 3), config mutation (Pitfall 4), welcome message regression (Pitfall 5).
**Stack:** `TokenClaim("login")` from FastMCP 3.1.0, `pathlib` for path safety. No new deps.
**Estimated size:** ~15-20 lines changed in `tools.py`, plus tests.

### Phase 2: Makefile to Just Migration
**Rationale:** Completely independent of Phase 1 -- zero code overlap. Can be done in parallel or after Phase 1.
**Delivers:** Cleaner build tooling with `just --list` discoverability, no `.PHONY` boilerplate, recipe arguments for future use.
**Addresses:** Justfile creation, Makefile deletion, optional `just dev` and `just test` recipes.
**Avoids:** Variable syntax errors (Pitfalls 7, 8), stale Makefile left behind (Pitfall 12).
**Stack:** Just 1.46.0 (`brew install just`).
**Estimated size:** ~30 lines in new justfile, delete Makefile.

### Phase 3: Validation and Deployment
**Rationale:** Depends on both Phase 1 and Phase 2. Verifies the full chain works end-to-end, including NFS permissions on the production cluster.
**Delivers:** Deployed v1.1 with verified multi-user isolation on production infrastructure.
**Addresses:** NFS permission verification (Pitfall 6), tool schema verification, end-to-end test from Claude AI.
**Avoids:** "Looks done but isn't" -- the PITFALLS.md checklist provides 10 specific verification items.

### Phase Ordering Rationale

- **Phase 1 before Phase 3** because deployment depends on the code changes being complete and tested.
- **Phase 2 is independent** and can run in parallel with Phase 1, or be sequenced after it. No dependency either way.
- **Phase 3 is the gate** -- it validates both workstreams on production infrastructure before the milestone is marked complete.
- The total estimated change is ~55 LOC across the entire milestone. This is small enough that 3 phases may even be compressed into 2 if the roadmapper prefers.

### Research Flags

Phases with standard patterns (skip `/gsd:research-phase`):
- **Phase 1:** FastMCP's `TokenClaim` DI is thoroughly documented in the research with verified source code examples. Path traversal prevention uses standard `pathlib` patterns. No further research needed.
- **Phase 2:** Direct syntax translation from Make to Just. The research includes a complete working justfile. No further research needed.

Phases that may need attention during planning:
- **Phase 3:** NFS permission behavior on the Synology NAS with `nfs-subdir-external-provisioner` is the one area where the research flags uncertainty. Best resolved empirically with a `kubectl exec` test during implementation, not with more research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies verified against installed source code. No new dependencies. `TokenClaim` import confirmed working at runtime. |
| Features | HIGH | Feature set is small and explicitly defined in PROJECT.md. Every feature has a clear implementation path with estimated LOC. |
| Architecture | HIGH | Single-file change (`tools.py`). Architecture verified by reading existing codebase and FastMCP internals. |
| Pitfalls | HIGH | Critical pitfalls verified against FastMCP source. Mitigations use standard Python patterns. NFS pitfall is the only one needing empirical validation. |

**Overall confidence:** HIGH

### Gaps to Address

- **NFS subdirectory permissions:** The research flags this as the most likely production surprise. Cannot be resolved with more research -- needs a `kubectl exec` test on the actual NFS mount. Plan for this in Phase 3.
- **`async` requirement for TokenClaim:** ARCHITECTURE.md notes tool handlers may need to become `async` for FastMCP's DI system. Needs verification during implementation -- may work with sync functions too. Low risk either way.

## Sources

### Primary (HIGH confidence)
- FastMCP 3.1.0 installed source (`fastmcp/server/auth/providers/github.py`, `fastmcp/server/dependencies.py`, `fastmcp/dependencies.py`) -- verified `TokenClaim`, `CurrentAccessToken`, `AccessToken.claims` structure
- FastMCP runtime verification -- `python -c "from fastmcp.dependencies import CurrentAccessToken, TokenClaim"` succeeds
- Python 3.12 `pathlib` docs -- `Path.resolve()`, `Path.is_relative_to()`
- Just 1.46.0 official manual (just.systems/man/en/)
- Homebrew just formula -- version 1.46.0 confirmed
- Project source files (`tools.py`, `config.py`, `server.py`, `Makefile`, K8s manifests)

### Secondary (MEDIUM confidence)
- FastMCP GitHub Integration docs (gofastmcp.com/integrations/github)
- FastMCP Authorization docs (gofastmcp.com/servers/authorization)
- GitHub username regex constraints (github.com/shinnn/github-username-regex)
- NFS permissions in K8s (kubernetes-sigs/nfs-subdir-external-provisioner#158)
- MCP SDK issue #1414 on Context-based token access
- Just vs Make comparison (spin.atomicobject.com)
- Path traversal prevention guides (salvatoresecurity.com, security.openstack.org)

---
*Research completed: 2026-03-06*
*Ready for roadmap: yes*
