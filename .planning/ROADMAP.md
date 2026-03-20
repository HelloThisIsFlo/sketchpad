# Roadmap: Sketchpad

## Milestones

- SHIPPED **v1.0 MVP** -- Phases 1-4 (shipped 2026-03-06)
- SHIPPED **v1.1 Multi-Users** -- Phases 5-7 (shipped 2026-03-07)
- ACTIVE **v1.2 Tool Polish** -- Phases 8-9

## Phases

<details>
<summary>v1.0 MVP (Phases 1-4) -- SHIPPED 2026-03-06</summary>

- [x] Phase 1: Infrastructure (2/2 plans) -- completed 2026-03-04
- [x] Phase 2: MCP Server + OAuth (5/5 plans) -- completed 2026-03-04
- [x] Phase 3: Deploy + Integration (3/3 plans) -- completed 2026-03-05
- [x] Phase 4: Hardening (2/2 plans) -- completed 2026-03-05

</details>

<details>
<summary>v1.1 Multi-Users (Phases 5-7) -- SHIPPED 2026-03-07</summary>

- [x] Phase 5: Per-User Storage Isolation (2/2 plans) -- completed 2026-03-06
- [x] Phase 6: Storage Limits (1/1 plan) -- completed 2026-03-06
- [x] Phase 7: Build Tooling Migration (2/2 plans) -- completed 2026-03-06

</details>

### v1.2 Tool Polish (Active)

**Milestone Goal:** Harden the tool API -- validate inputs and clarify tool descriptions for agent consumption.

- [ ] **Phase 8: Parameter Validation** - Constrain write_file mode to allowed values with safe default
- [ ] **Phase 9: Description Update** - Reframe tool descriptions for inter-agent persistence consumption

## Phase Details

### Phase 8: Parameter Validation
**Goal**: Invalid mode values are rejected before the function body runs, and the default mode is safe for persistence use cases
**Depends on**: Phase 7 (v1.1 complete)
**Requirements**: VALID-01, VALID-02, VALID-03, VALID-04
**Success Criteria** (what must be TRUE):
  1. Calling `write_file` with `mode="invalid"` returns a clear error without modifying the file
  2. Calling `write_file` without specifying `mode` appends content (not replaces)
  3. The JSON schema returned by `tools/list` shows `{"enum": ["replace", "append"]}` for the mode parameter
  4. All existing tests pass without modification (or with minimal explicit `mode=` additions where intent is replace)
**Plans:** 1 plan

Plans:
- [ ] 08-01-PLAN.md — Literal type annotation + append default + validation tests (VALID-01..04)

### Phase 9: Description Update
**Goal**: AI agents reading tool descriptions understand the sketchpad as a shared persistence layer and know when to use (and not use) each tool
**Depends on**: Phase 8
**Requirements**: DESC-01, DESC-02, DESC-03
**Success Criteria** (what must be TRUE):
  1. Claude AI on the live server reads and writes the sketchpad without unexpected refusals after description change
  2. The JSON schema for `content` and `mode` parameters includes human-readable `description` fields
  3. Tool descriptions include explicit usage guidelines (when to persist) and limitations (what NOT to store)
**Plans**: TBD

Plans:
- [ ] 09-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 8 -> 9

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Infrastructure | v1.0 | 2/2 | Complete | 2026-03-04 |
| 2. MCP Server + OAuth | v1.0 | 5/5 | Complete | 2026-03-04 |
| 3. Deploy + Integration | v1.0 | 3/3 | Complete | 2026-03-05 |
| 4. Hardening | v1.0 | 2/2 | Complete | 2026-03-05 |
| 5. Per-User Storage Isolation | v1.1 | 2/2 | Complete | 2026-03-06 |
| 6. Storage Limits | v1.1 | 1/1 | Complete | 2026-03-06 |
| 7. Build Tooling Migration | v1.1 | 2/2 | Complete | 2026-03-06 |
| 8. Parameter Validation | v1.2 | 0/1 | Not started | - |
| 9. Description Update | v1.2 | 0/? | Not started | - |

_Full v1.0 details: `.planning/milestones/v1.0-ROADMAP.md`_
_Full v1.1 details: `.planning/milestones/v1.1-ROADMAP.md`_
