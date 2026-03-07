# Phase 5: Per-User Storage Isolation - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Each authenticated user reads and writes only their own sketchpad, isolated by OAuth username. Two users never see each other's data. Directory structure is provider-scoped for future multi-provider support. No migration of v1.0 single-user data.

</domain>

<decisions>
## Implementation Decisions

### Username sanitization
- Prefer a library (e.g., python-slugify) over hand-rolled sanitization — researcher makes the final call on whether a library is truly needed or overkill
- Sanitization must be idempotent: `sanitize(sanitize(x)) == sanitize(x)`
- Sanitization must be injective within a provider: two distinct usernames must not map to the same folder
- No dependency aversion — adding a package is fine if it solves the problem cleanly

### Provider-scoped folder structure
- Folder layout: `/data/{provider}/{identifier}/sketchpad.md` (e.g., `/data/github/flo/sketchpad.md`)
- Each provider can use its own natural unique identifier (GitHub → `login`, Google → `sub` or email — decided per provider)
- Naming convention is per-provider — no forced universal scheme
- Phase 5 implements GitHub only, but structures code so adding a new provider path is straightforward

### Tool descriptions
- Update descriptions to convey: personal to you, shared across all your AI agents (Claude AI, Cursor, any MCP client with same GitHub identity)
- Drop "single shared" wording — it's now per-user
- Claude's discretion on exact wording as long as it communicates the personal-but-cross-agent nature

### Tool schema and responses
- Username is hidden from the JSON schema — Claude AI cannot see or override it (extracted server-side from OAuth token)
- Tool responses do NOT include the username — keep generic ("File updated (replace mode). Size: 1234 bytes.")
- Welcome message stays the same generic text for all users: "Welcome to Sketchpad! Write something here."

### Error behavior
- Trust FastMCP's auth layer to reject unauthenticated requests before they reach tools
- Add a defensive assertion for missing username — treat as internal error, not user-facing
- Never fall back to anonymous/shared sketchpad
- Path traversal attempts: return generic "Invalid request" error — don't reveal what was detected
- Log path traversal attempts at WARNING level server-side (raw username in pod logs)

### Claude's Discretion
- Exact tool description wording (within the personal-but-cross-agent framing)
- Internal code structure for provider-to-folder mapping (as long as adding providers is straightforward)
- Whether to use python-slugify or a simpler approach (after research)

</decisions>

<specifics>
## Specific Ideas

- The sketchpad is personal to a user but shared across all their AI agents — Claude AI on phone, Claude AI on desktop, Cursor, any MCP client using the same GitHub identity. This is the core value proposition.
- User plans to test with Cursor as a second MCP client to verify cross-agent access with same identity.
- Production-grade security posture: lossy sanitization that allows cross-user data access is unacceptable. Injectivity within a provider is a hard requirement.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tools.py`: `register_tools(mcp)` pattern — add context parameter for user identity
- `config.py`: `DATA_DIR` and `SKETCHPAD_FILENAME` config — reusable, path construction changes
- `middleware.py`: `OriginValidationMiddleware` — no changes needed
- `server.py`: `create_oauth_provider()` factory with `OAUTH_PROVIDER` env var — already extensible

### Established Patterns
- Environment-based config via `get_config()` with `@lru_cache`
- FastMCP tool registration via `@mcp.tool` decorator
- Provider factory pattern (`create_oauth_provider`) — extend for folder strategy

### Integration Points
- `tools.py:14-15`: Path construction `Path(cfg["DATA_DIR"]) / cfg["SKETCHPAD_FILENAME"]` — must become `Path(cfg["DATA_DIR"]) / provider / sanitized_username / cfg["SKETCHPAD_FILENAME"]`
- `server.py:79`: `FastMCP(name="Sketchpad", auth=auth)` — auth context flows to tools via FastMCP's context mechanism
- Need to investigate FastMCP's `TokenClaim("login")` or equivalent for extracting username in tool functions

</code_context>

<deferred>
## Deferred Ideas

- Test Cursor as a second MCP client (user interest, not part of this phase)
- Google OAuth provider implementation (future phase, folder structure is ready for it)

</deferred>

---

*Phase: 05-per-user-storage-isolation*
*Context gathered: 2026-03-06*
