# Phase 2: MCP Server + OAuth - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

A locally running FastMCP server that correctly implements the full OAuth 2.1 protocol (discovery endpoints, Dynamic Client Registration, PKCE, GitHub identity provider) and two file tools (read_file, write_file) — validated with curl and MCP Inspector before any Kubernetes complexity is involved.

</domain>

<decisions>
## Implementation Decisions

### Local Testing Workflow
- Use `cloudflared tunnel --url http://localhost:8000` for ephemeral quick tunnels during dev — random `*.trycloudflare.com` URL, zero dashboard config, zero stale state
- Update GitHub OAuth App callback URL each dev session with the new tunnel URL (acceptable friction)
- Primary test client: runnable `test-oauth.sh` script that exercises the full OAuth flow end-to-end (discovery -> register -> authorize -> token -> MCP tool calls) with clear output and comments at each step
- Secondary test tool: MCP Inspector as a guided exploration bonus — include a section in docs with "fun things to try" so the user can learn the tool. Not a requirement, a learning opportunity
- Claude Code CLI remains the primary integration test client (Claude.ai web has known `about:blank` bug per issue #11814)

### File Tool Behavior
- Welcome message on first read (file doesn't exist yet) — something like "Welcome to Sketchpad! Write something here."
- write_file supports both replace (default) and append modes via a `mode` parameter
- Content is plain text with zero validation — tool description nudges the agent toward Markdown but accepts anything
- Soft size limit on the file to protect context windows — Claude picks the exact threshold (something reasonable for a sketchpad, not a novel). Read response includes a warning if exceeded, not a hard block
- Edge cases (concurrent writes, etc.) throw errors — deferred to future milestone

### Project Structure
- Minimal Python package layout (not a single file) — separate files for server wiring, tools, config for navigability
- `uv` for dependency management (`uv init`, `uv add fastmcp`, `uv run`)
- Dockerfile included in Phase 2 alongside the code — test containerized version locally before K8s in Phase 3

### Config & Secrets
- `.env` file in project root (gitignored) for local dev — `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `SERVER_URL`, encryption key, etc.
- `.env.example` committed with placeholder values — makes required config discoverable
- Server reads `.env` on startup

### Claude's Discretion
- Server URL handling for changing tunnel URLs (CLI arg override, .env update, or other approach — minimize friction)
- Soft size limit threshold for the sketchpad file
- Exact package layout (file names, module organization within the minimal package pattern)
- MCP Inspector "things to try" content
- Welcome message exact wording
- test-oauth.sh script structure and error handling

</decisions>

<specifics>
## Specific Ideas

- "I want to learn MCP Inspector through this project" — include guided exploration, not just validation. Frame it as "here are fun things you can try" rather than test steps
- "Structure is easier to navigate than one big file" — user prefers separate files even for a spike, for readability
- "Any edge case just throws an error and keep it simple" — this is a spike, don't over-engineer error handling
- "No validation, plain text, but a nice nudge to the agent that this is meant for Markdown" — tool description suggests markdown, server doesn't enforce it

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — project is a blank slate, no code exists yet

### Established Patterns
- None from code, but Phase 1 established:
  - NFS-backed PVC for persistence (server will write to a PVC-mounted path in production)
  - K8s Secrets for credentials (server reads env vars injected from Secrets in production)
  - cloudflared as ingress (server binds to a ClusterIP Service)

### Integration Points
- GitHub OAuth App created in Phase 1 — credentials available as K8s Secret and in local `.env`
- Public hostname `sketchpad.kempenich.ai` configured via Cloudflare Tunnel in Phase 1
- PVC at a known mount path provides persistent file storage in K8s
- FastMCP 3.0.2 with GitHubProvider — the core framework (decided during project init)
- FileTreeStore + FernetEncryptionWrapper for OAuth state persistence (decided during project init)

### Known Issues to Handle
- FastMCP DCR `grant_types` bug (issue #2460) — may need workaround during registration
- RFC 9728 `/.well-known/oauth-protected-resource` path bug in FastMCP (issue #1052) — verify and work around if needed

</code_context>

<deferred>
## Deferred Ideas

- Concurrent write handling / race conditions — future milestone
- File versioning or history — out of scope, belongs in Obsidian vault project
- Multiple files — that's literally the Obsidian vault project

</deferred>

---

*Phase: 02-mcp-server-oauth*
*Context gathered: 2026-03-03*
