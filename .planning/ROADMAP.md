# Roadmap: Sketchpad

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-03-06)
- 🚧 **v1.1 Multi-Users** — Phases 5-7 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-4) — SHIPPED 2026-03-06</summary>

- [x] Phase 1: Infrastructure (2/2 plans) — completed 2026-03-04
- [x] Phase 2: MCP Server + OAuth (5/5 plans) — completed 2026-03-04
- [x] Phase 3: Deploy + Integration (3/3 plans) — completed 2026-03-05
- [x] Phase 4: Hardening (2/2 plans) — completed 2026-03-05

</details>

### 🚧 v1.1 Multi-Users (In Progress)

**Milestone Goal:** Each authenticated user gets their own isolated sketchpad, segregated by OAuth username.

- [ ] **Phase 5: Per-User Storage Isolation** - Scope read/write tools to per-user directories derived from OAuth identity
- [ ] **Phase 6: Storage Limits** - Enforce per-user and global size limits on writes
- [ ] **Phase 7: Build Tooling Migration** - Replace Makefile with Justfile and update CI

## Phase Details

### Phase 5: Per-User Storage Isolation
**Goal**: Each authenticated user reads and writes only their own sketchpad, isolated by OAuth username
**Depends on**: Phase 4 (v1.0 shipped)
**Requirements**: ISOL-01, ISOL-02, ISOL-03, ISOL-04
**Success Criteria** (what must be TRUE):
  1. Two different GitHub users each see only their own sketchpad content -- one user's writes are invisible to the other
  2. A crafted username containing path traversal sequences (e.g., `../`) cannot escape the data directory
  3. A user's directory is created automatically on their first write -- no manual setup needed
  4. Usernames with unexpected characters are sanitized to filesystem-safe names before directory creation
  5. The OAuth username is never exposed in the tool's JSON schema -- Claude AI cannot override it
**Plans:** 2 plans

Plans:
- [ ] 05-01-PLAN.md — TDD: user identity resolution module with sanitization and path traversal defense
- [ ] 05-02-PLAN.md — Wire user identity into read/write tools with per-user paths

### Phase 6: Storage Limits
**Goal**: Write operations are bounded by configurable per-user and global size limits
**Depends on**: Phase 5 (per-user paths must exist for per-user limits)
**Requirements**: STOR-01, STOR-02
**Success Criteria** (what must be TRUE):
  1. A write exceeding the per-user size limit is rejected with a clear error message
  2. A write that would push the total data directory past the global limit is rejected with a clear error message
  3. Both limits are configurable via environment variables without code changes
**Plans**: TBD

Plans:
- [ ] 06-01: TBD

### Phase 7: Build Tooling Migration
**Goal**: Makefile is replaced by Justfile with identical functionality and CI updated to match
**Depends on**: Phase 4 (independent of Phases 5-6)
**Requirements**: BUILD-01, BUILD-02
**Success Criteria** (what must be TRUE):
  1. Every Makefile recipe has a working equivalent in the Justfile (`just --list` shows all recipes)
  2. `just build`, `just deploy`, and other recipes produce the same results as their `make` equivalents
  3. GitHub Actions CI runs successfully using `setup-just` action instead of `make`
  4. The Makefile is deleted -- no stale build file left behind
**Plans**: TBD

Plans:
- [ ] 07-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order. Phase 7 is independent of 5-6 and could run in parallel.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Infrastructure | v1.0 | 2/2 | Complete | 2026-03-04 |
| 2. MCP Server + OAuth | v1.0 | 5/5 | Complete | 2026-03-04 |
| 3. Deploy + Integration | v1.0 | 3/3 | Complete | 2026-03-05 |
| 4. Hardening | v1.0 | 2/2 | Complete | 2026-03-05 |
| 5. Per-User Storage Isolation | v1.1 | 0/2 | Planned | - |
| 6. Storage Limits | v1.1 | 0/? | Not started | - |
| 7. Build Tooling Migration | v1.1 | 0/? | Not started | - |

_Full v1.0 details: `.planning/milestones/v1.0-ROADMAP.md`_
