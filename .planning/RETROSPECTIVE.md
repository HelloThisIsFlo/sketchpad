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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Execution Time | Phases | Key Change |
|-----------|---------------|--------|------------|
| v1.0 | 41min | 4 | First milestone — established yolo + fine granularity workflow |

### Cumulative Quality

| Milestone | Requirements | Coverage | Audit Score |
|-----------|-------------|----------|-------------|
| v1.0 | 32/32 | 100% | Passed (0 gaps, 0 tech debt) |

### Top Lessons (Verified Across Milestones)

1. Trivial business logic isolates infrastructure/auth problems — keep spikes simple
2. Gap closure plans are cheaper than shipping with gaps — audit early
