# Milestones

## v1.2 Tool Polish (Shipped: 2026-03-20)

**Phases:** 2 | **Plans:** 2 | **Tasks:** 4 | **Timeline:** 3 days (2026-03-18 → 2026-03-20)
**Files modified:** 3 | **Lines of code:** 2,152 Python
**Commits:** 23

**Delivered:** Hardened tool API with input validation (Literal type + Pydantic) and inter-agent persistence framing with Do/Do NOT guardrails.

**Key accomplishments:**
1. Constrained write_file mode to `Literal["replace", "append"]` with Pydantic validation before function body
2. Changed default mode from replace to append — safer for inter-agent persistence use cases
3. Reframed tool descriptions as "shared persistence layer for AI agents" with Do/Do NOT guardrails
4. Added `Field(description=...)` annotations on content and mode parameters (visible in JSON schema)
5. Added newline separator in append mode between successive writes

**Git range:** 0839c8c → 522e28b

---

## v1.1 Multi-Users (Shipped: 2026-03-07)

**Phases:** 3 | **Plans:** 5 | **Tasks:** 10 | **Timeline:** 2 days (2026-03-06 -> 2026-03-07)
**Files modified:** 44 | **Lines of code:** 1,816 Python
**Commits:** 36

**Delivered:** Per-user storage isolation via OAuth identity, write-time storage limits, and Justfile/ruff build tooling with CI gates.

**Key accomplishments:**

1. Per-user storage isolation -- each OAuth user gets their own sketchpad directory via resolve_user_dir()
2. TDD test suite -- 35 tests covering path traversal defense, tool isolation, auth enforcement, schema safety
3. Per-user (20KB) and global (50MB) write-time storage limits with configurable env vars
4. Justfile replaces Makefile -- 10 recipes with ruff linter/formatter (E4/E7/E9/F/B/I rules)
5. CI pipeline with test+lint gates before Docker build+push

**Git range:** 6eb8833 -> de2efbe

---

## v1.0 MVP (Shipped: 2026-03-06)

**Phases:** 4 | **Plans:** 12 | **Timeline:** 4 days (2026-03-02 → 2026-03-06)
**Files modified:** 85 | **Lines of code:** 1,022 Python

**Delivered:** A minimal remote MCP server with OAuth 2.1 authentication, deployed on Kubernetes behind Cloudflare Tunnel, proven end-to-end from Claude AI on phone.

**Key accomplishments:**

1. K8s infrastructure with Cloudflare Tunnel, NFS-backed PVCs, and GitHub Actions CI
2. FastMCP 3.1.0 server with OAuth 2.1 (DCR + PKCE) via GitHubProvider
3. Encrypted OAuth state persistence (FileTreeStore + Fernet) surviving pod restarts
4. Full E2E OAuth handshake confirmed from Claude AI (CLI + phone)
5. Origin validation middleware blocking disallowed Origins on /mcp endpoint
6. Complete documentation suite (5 numbered guides + README index)

**Git range:** initial commit → 42cd142

---
