# Requirements: Sketchpad

**Defined:** 2026-03-18
**Core Value:** OAuth 2.1 authentication (DCR + PKCE) works correctly between Claude AI and my server

## v1.2 Requirements

Requirements for v1.2 Tool Polish. Each maps to roadmap phases.

### Parameter Validation

- [ ] **VALID-01**: `write_file` mode parameter constrained to `Literal["replace", "append"]` -- invalid values rejected before function body
- [ ] **VALID-02**: Default mode changed from `"replace"` to `"append"` -- safer default for persistence use case
- [ ] **VALID-03**: JSON schema includes `{"enum": ["replace", "append"]}` for mode parameter -- verified by test
- [ ] **VALID-04**: Invalid mode value rejected with clear error via `tool.run()` -- verified by test

### Tool Descriptions

- [ ] **DESC-01**: `read_file` and `write_file` docstrings reframed as inter-agent persistence layer
- [ ] **DESC-02**: `content` and `mode` parameters have `Field(description=...)` annotations visible in JSON schema
- [ ] **DESC-03**: Tool descriptions include usage guidelines (when to use) and limitations (when NOT to use)

## Future Requirements

None -- this is a polish milestone.

## Out of Scope

| Feature | Reason |
|---------|--------|
| ToolAnnotations (readOnlyHint, destructiveHint) | Claude AI doesn't use these for tool selection; spec says clients must treat as untrusted |
| outputSchema | Tools return plain strings; no value in formalizing |
| Examples in descriptions | Research found removing examples doesn't degrade performance; saves tokens |
| Enum class for mode | Generates $ref schemas that some MCP clients handle poorly (SDK #1373) |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| VALID-01 | Phase 8 | Pending |
| VALID-02 | Phase 8 | Pending |
| VALID-03 | Phase 8 | Pending |
| VALID-04 | Phase 8 | Pending |
| DESC-01 | Phase 9 | Pending |
| DESC-02 | Phase 9 | Pending |
| DESC-03 | Phase 9 | Pending |

**Coverage:**
- v1.2 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0

---
*Requirements defined: 2026-03-18*
*Last updated: 2026-03-18 after roadmap creation*
