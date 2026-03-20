# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-03-06
**Phases:** 4 | **Plans:** 12 | **Total execution:** 41min

### What Was Built
- OAuth 2.1 MCP server (FastMCP 3.1.0 + GitHubProvider) with DCR and PKCE
- K8s infrastructure: NFS-backed PVCs, Cloudflare Tunnel, GitHub Actions CI
- Two file tools (read_file, write_file) with encrypted persistent storage
- Origin validation middleware on /mcp endpoint
- 5 documentation guides with README index

### What Worked
- **Trivial business logic by design** — single-file read/write meant every failure was auth or infrastructure, never logic. Made debugging unambiguous.
- **Phase ordering** — infrastructure first, local server second, deploy third, harden fourth. Each phase was independently verifiable before the next began.
- **FastMCP 3.1.0** — eliminated ~500 lines of hand-rolled OAuth. DCR and RFC 9728 bugs were already fixed upstream.
- **Yolo mode + fine granularity** — 12 small plans averaged 3.4min each. Fast feedback loops, no plan was too big to fail.

### What Was Inefficient
- **Phase 2 needed 5 plans instead of 3** — gap closure plans (02-04, 02-05) were added after the milestone audit caught DISC-02 URL and missing E2E verification. Earlier verification would have avoided the rework.
- **Phase 3 deploy** (03-03) took 14min — longest plan by far. Dockerfile multi-stage build issues (--no-editable) and K8s Secret mismatches required debugging in-cluster. More local validation before deploy would help.
- **Summary one-liner extraction** — the `summary-extract --fields one_liner` tool returned null for all summaries, suggesting the summary format doesn't include a structured one-liner field. Manual reading was needed.

### Patterns Established
- `@mcp.custom_route` for health endpoints that bypass FastMCP auth
- `OAUTH_PROVIDER` env var + factory pattern for extensible auth providers
- Lazy `get_config()` with `@lru_cache` — imports work without .env, env vars read at startup
- `docker buildx --platform linux/amd64` for Apple Silicon → Talos amd64 cross-compile
- `--no-editable` in `uv sync` for multi-stage Docker builds

### Key Lessons
1. **GitHub doesn't issue refresh tokens** — AUTH-05/AUTH-06 are provider-specific behaviors, not server failures. Document provider quirks, don't test for them.
2. **RFC 9728 path-aware discovery** — `/.well-known/oauth-protected-resource/mcp` (not just `/.well-known/oauth-protected-resource`). The resource path matters.
3. **K8s Secrets need exact key names** — the encryption-key Secret needed `jwt-signing-key` and `storage-encryption-key`, not just `fernet-key`. Match what the app expects.
4. **Origin validation is transparent to CLIs** — CLI clients don't send Origin headers, so pass-through is the right default. Only block explicit mismatches.

### Cost Observations
- Model mix: ~80% opus, ~20% sonnet (research agents)
- Total execution: 41min across 12 plans
- Notable: Average 3.4min/plan. Phase 4 (hardening) was fastest at 2min/plan — well-understood patterns by then.

---

## Milestone: v1.1 -- Multi-Users

**Shipped:** 2026-03-07
**Phases:** 3 | **Plans:** 5 | **Total execution:** 11min

### What Was Built
- Per-user storage isolation via OAuth identity (resolve_user_dir with regex + Path.resolve defense-in-depth)
- Write-time storage limits: per-user (20KB) and global (50MB) with configurable env vars
- Justfile with 10 recipes replacing Makefile, ruff linter/formatter
- CI pipeline with test+lint gates before Docker build+push
- 35 tests (23 isolation + 12 storage limits)

### What Worked
- **TDD red-green pattern** -- writing failing tests first in Phase 5 and 6 caught a plan bug (traversal test expected wrong log message) before production code was written. The test was the spec.
- **Defense-in-depth** -- regex validation + Path.resolve() + is_relative_to() means three independent layers catch traversal. Each is simple; together they're robust.
- **Minimal v1.1 scope** -- 3 phases, 5 plans, 11min total execution. Per-user isolation is the only thing that matters for multi-user; storage limits and build tooling were low-risk additions.
- **Phase 7 independence** -- build tooling migration had no dependency on phases 5-6, could have run in parallel. Clean dependency graph.

### What Was Inefficient
- **Nothing significant** -- the shortest milestone. Every plan executed in 1-3min. No gap closure plans needed (learned from v1.0). The audit passed clean on first run.

### Patterns Established
- TDD red-green: write failing tests first, implement to pass
- Provider-scoped path resolution: `data_dir / provider / sanitized_identifier`
- Pre-write validation: check limits before any disk I/O
- `just <recipe>` for all project commands
- Ruff E4/E7/E9/F/B/I as lint baseline

### Key Lessons
1. **GitHub usernames are already filesystem-safe** -- `[a-zA-Z0-9-]`, 1-39 chars. No slugify needed. Know your input domain before adding sanitization libraries.
2. **Assert > Exception for security invariants** -- `assert token is not None` gives a clear crash message and guarantees no code path falls back to shared storage. Exceptions invite `except` handlers that soften the guarantee.
3. **Replace config keys atomically** -- Phase 6 renamed SIZE_LIMIT to MAX_STORAGE_USER/GLOBAL. The plan's test expected the old key removed before the code was updated, causing KeyError. Config changes must be atomic across test mocks and production code.

### Cost Observations
- Model mix: ~80% opus, ~20% sonnet (research agents)
- Total execution: 11min across 5 plans
- Notable: Average 2.2min/plan -- faster than v1.0 (3.4min). TDD plans are highly structured, less ambiguity = faster execution.

---

## Milestone: v1.2 — Tool Polish

**Shipped:** 2026-03-20
**Phases:** 2 | **Plans:** 2 | **Total execution:** 5min

### What Was Built
- write_file mode constrained to Literal["replace", "append"] with Pydantic validation (Phase 8)
- Default mode changed from replace to append — safer for inter-agent persistence
- Tool descriptions reframed as "shared persistence layer for AI agents" with Do/Do NOT guardrails (Phase 9)
- Field(description=...) annotations on content and mode parameters visible in JSON schema
- Newline separator in append mode between successive writes

### What Worked
- **Smallest possible scope** — 2 phases, 2 plans, 5min total. Pure API polish with zero infrastructure changes. Clean audit on first run.
- **Literal over Enum** — research found Enum generates $ref/$defs schemas that some MCP clients handle poorly (SDK #1373). Literal produces flat `enum` directly in the property — better compatibility for less complexity.
- **TDD continued from v1.1** — 15 new tests (4 Phase 8 + 11 Phase 9) caught the exact behaviors before implementation. Both phases hit GREEN on first try.
- **Research-driven scoping** — Phase 9 research found that ToolAnnotations and examples-in-descriptions add no value for Claude AI. Saved time by not implementing them.

### What Was Inefficient
- **ROADMAP progress table stale** — Phase 8 and 9 showed "0/1" and "Not started" in the progress table despite being complete. The executor should update the table on plan completion. Minor discrepancy, caught during milestone completion.

### Patterns Established
- `Annotated[Type, Field(description=...)]` for parameter-level JSON schema descriptions
- Docstrings for tool-level guidance (what/when/when-not), Field for parameter-level descriptions
- `tool.run()` (not `tool.fn()`) for testing Pydantic validation paths

### Key Lessons
1. **Literal > Enum for MCP tool parameters** — Enum generates $ref/$defs JSON schema that not all MCP clients handle well. Literal produces clean inline enum.
2. **Default-safe principle** — changing default mode from replace to append means accidental calls can't destroy data. All existing tests still passed because first-writes to non-existent files behave identically.
3. **Research before building is especially valuable for "should we even build this?"** — Phase 9 research eliminated ToolAnnotations and examples from scope entirely, saving a full phase of work.

### Cost Observations
- Model mix: ~80% opus, ~20% sonnet (research agents)
- Total execution: 5min across 2 plans
- Notable: Average 2.5min/plan — fastest milestone. Well-scoped polish with no unknowns.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Execution Time | Phases | Key Change |
|-----------|---------------|--------|------------|
| v1.0 | 41min | 4 | First milestone — established yolo + fine granularity workflow |
| v1.1 | 11min | 3 | TDD red-green pattern, Nyquist validation, audit-before-ship |
| v1.2 | 5min | 2 | Research-driven scoping eliminated unnecessary work |

### Cumulative Quality

| Milestone | Requirements | Coverage | Audit Score |
|-----------|-------------|----------|-------------|
| v1.0 | 32/32 | 100% | Passed (0 gaps, 0 tech debt) |
| v1.1 | 8/8 | 100% | Passed (0 gaps, 0 tech debt) |
| v1.2 | 7/7 | 100% | Passed (0 gaps, 0 tech debt) |

### Top Lessons (Verified Across Milestones)

1. Trivial business logic isolates infrastructure/auth problems — keep spikes simple
2. Gap closure plans are cheaper than shipping with gaps — audit early
3. TDD plans execute faster (2.2min avg vs 3.4min) — structured approach reduces ambiguity
4. Research-driven scoping saves more time than execution optimization — eliminating a phase is cheaper than making it fast
