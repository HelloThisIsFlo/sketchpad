# Project Research Summary

**Project:** Sketchpad v1.2 — Tool Polish
**Domain:** MCP tool API hardening (Literal validation + agent-optimized descriptions)
**Researched:** 2026-03-18
**Confidence:** HIGH

## Executive Summary

This milestone is a focused API hardening effort on an existing, working MCP server. The two work streams are: (1) adding `Literal["replace", "append"]` type validation to the `write_file` tool's `mode` parameter, and (2) rewriting tool descriptions to frame the server as an inter-agent persistence layer rather than a personal notepad. Both changes are low-complexity, require no new dependencies, and can be implemented in a single sitting.

The recommended approach is to treat the two streams as parallel but deploy them with awareness of their different risk profiles. The parameter validation change is mechanical and safe — Pydantic's TypeAdapter handles it automatically with zero custom code. The description rewrite carries behavioral risk: AI agents treat tool descriptions as programming instructions, and negative phrasing or over-specific scoping can cause agents to refuse valid use cases. The description change needs manual UAT with Claude AI on the live server before the milestone is closed.

The primary pitfall to avoid is the default-change side effect: changing `mode` from `"replace"` to `"append"` will affect every test that omits `mode=`. Analysis shows all existing tests write to empty files, so append-to-empty produces the same result as replace — no test failures expected. But the audit should happen before the default changes, not after.

## Key Findings

### Recommended Stack

No new dependencies. All capabilities needed for v1.2 already exist in the dependency tree: `typing.Literal` and `typing.Annotated` from Python 3.12 stdlib, `pydantic.Field` from Pydantic 2.12.5 (already a FastMCP dependency), and FastMCP 3.1.0's `ParsedFunction` pipeline which automatically converts `Literal` annotations to JSON Schema `enum` constraints.

**Core technologies:**
- `typing.Literal` — constrains `mode` to `["replace", "append"]`; produces `{"enum": [...]}` in JSON Schema via Pydantic TypeAdapter; universally supported by MCP clients (unlike `enum.Enum` which generates `$ref` schemas that some clients handle poorly)
- `typing.Annotated` + `pydantic.Field(description=...)` — attaches parameter-level descriptions to the JSON Schema `properties.*` entries; the only reliable way to get per-parameter descriptions into the schema (FastMCP does NOT parse Google-style `Args:` docstring sections)
- Python docstrings — become `tool.description` verbatim via `inspect.getdoc(fn)`; no special library needed

### Expected Features

**Must have (table stakes):**
- `Literal["replace", "append"]` type annotation on `write_file`'s `mode` param — prevents silent misuse (currently any string accepted; invalid values silently fall through to the replace branch)
- Default `mode` changed from `"replace"` to `"append"` — append is the safer default for an inter-agent persistence tool; replace should require explicit intent
- Server-side Pydantic validation (automatic from Literal annotation) — MCP spec requires servers to validate all tool inputs; Literal satisfies this with no manual code
- Tool descriptions reframed for inter-agent persistence — current "personal sketchpad / notes, drafts, ideas" framing misrepresents the tool's actual purpose to AI agents
- Parameter descriptions via `Annotated[..., Field(description=...)]` — `content` and `mode` both undescribed at schema level currently

**Should have (differentiators):**
- Usage guidelines + limitations in tool description — research shows 97% of MCP descriptions lack guidelines; adding them improves agent tool selection by ~5.85pp
- Test for JSON schema enum constraint — catches regressions if type annotation changes
- Test for invalid mode rejection via `tool.run()` — existing tests all use `tool.fn` which bypasses Pydantic validation

**Defer (v2+):**
- `ToolAnnotations` (`readOnlyHint`, `destructiveHint`, etc.) — Claude AI doesn't currently use these for tool selection; spec says clients must treat as untrusted anyway
- `outputSchema` — tools return plain strings; no value in formalizing that
- Examples in tool descriptions — research found removing examples does not statistically degrade performance; saves context window tokens

### Architecture Approach

The change is entirely localized to `tools.py` function signatures and docstrings. FastMCP's `ParsedFunction` pipeline is already wired to handle `Literal` types — it feeds the signature to Pydantic's `TypeAdapter`, which generates the correct `enum` JSON Schema and validates at call time in `FunctionTool.run()`. Nothing changes in the framework layer.

**Major components:**
1. `tools.py` function signatures — source of truth for JSON Schema; changing `mode: str` to `mode: Literal["replace", "append"]` is the only code change
2. `tools.py` docstrings — become `tool.description` verbatim; rewrite for agent consumption not human readability
3. `FunctionTool.run()` (FastMCP internals, unchanged) — calls `type_adapter.validate_python(arguments)` before function body; Literal validation is automatic here
4. Test suite — existing tests use `tool.fn` (bypasses validation); new tests must use `tool.run()` to exercise the validation layer

### Critical Pitfalls

1. **Default change silently affects tests** — Every `write_fn(content=...)` call without explicit `mode=` will switch from replace to append semantics. Analysis shows writes to empty files produce the same output either way, so no failures expected — but audit callsites first, add explicit `mode="replace"` where intent is replace.

2. **`tool.fn` tests don't exercise Literal validation** — Existing test pattern calls the raw function, bypassing Pydantic. False confidence. Add at least one test via `await tool.run({"mode": "invalid"})` that expects rejection.

3. **Description changes alter AI agent behavior unpredictably** — Negative instructions ("Do NOT write here for user-facing content") can cause agents to over-refuse. Deploy descriptions separately from parameter changes, test with Claude AI on the live server, monitor first sessions for unexpected refusals.

4. **MCP schema caching on active clients** — Clients call `tools/list` once at session start; connected clients won't see the new `enum` constraint until they reconnect. Server-side validation is correct regardless. Document in release notes: reconnect after deployment.

5. **Duplicate validation is dead code** — With `Literal` in place, Pydantic validates before the function body runs. Any manual `if mode not in (...)` guard inside `write_file` will never execute. Don't add it.

## Implications for Roadmap

Based on research, two-phase structure is the right call. The changes are independent but have different risk profiles that warrant separate deployment awareness.

### Phase 1: Parameter Validation

**Rationale:** Mechanical change, highest safety value, no behavioral risk. Establishes the Literal type and default change before touching descriptions.
**Delivers:** `mode` parameter constrained to `["replace", "append"]` in JSON Schema; invalid inputs rejected by Pydantic with clear error; default changed to `"append"`; new schema and validation tests
**Addresses:** Must-have features — Literal annotation, default change, server-side validation, schema enum test, invalid mode test
**Avoids:** Default-change test breakage (audit first), test-helper bypass pitfall (add `tool.run()` tests)

### Phase 2: Description Update

**Rationale:** Higher behavioral risk due to AI agent impact; must be deployed and UAT'd separately from parameter changes to isolate regressions.
**Delivers:** Both `read_file` and `write_file` descriptions reframed as inter-agent persistence; parameter descriptions added via `Annotated + Field(description=...)`; manual UAT confirming Claude AI reads/writes appropriately
**Addresses:** Must-have features — description rewrite, parameter descriptions; differentiator — usage guidelines + limitations
**Avoids:** Agent over-refusal pitfall (manual UAT required before milestone close); schema caching pitfall (document reconnect requirement)

### Phase Ordering Rationale

- Parameter validation first because it's mechanical and reversible; description changes have subtler behavioral effects that are harder to diagnose if both land simultaneously
- Description and parameter descriptions together in Phase 2 because they're both about what the agent sees and reads naturally as a unit
- Two phases keeps the blast radius small — if Claude starts refusing writes after Phase 2, it's obviously the description change, not the validation change

### Research Flags

Phases with standard patterns (skip research-phase):
- **Phase 1:** Well-documented FastMCP + Pydantic patterns, verified against installed source. Implementation is straightforward.
- **Phase 2:** Description text is novel (inter-agent framing) but the mechanism (docstring + Field) is verified. No research needed — the text itself just needs to be written and manually tested.

No phases need deeper research during planning. Both are ready to implement.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified against installed FastMCP 3.1.0 source and runtime — `Literal` and `Annotated+Field` tested directly |
| Features | HIGH | Literal and Field patterns are verified; description framing is MEDIUM (novel, unvalidated with real agent behavior) |
| Architecture | HIGH | FastMCP pipeline fully traced; test impact analysis is complete and verified |
| Pitfalls | HIGH | Verified against installed source; default-change impact analyzed against full test suite |

**Overall confidence:** HIGH

### Gaps to Address

- **Inter-agent description framing:** The "shared persistence layer" framing is novel and untested against real Claude AI behavior. The risk is agents over-refusing or under-using the tool. Mitigate by treating Phase 2 as requiring manual UAT before milestone close — this is not a "ship and observe" situation.
- **Error format acceptability:** Pydantic's `ValidationError` text is returned to AI agents verbatim. Confirmed it's informative, but the actual Claude AI client response to seeing this error in practice hasn't been tested. Low risk — Claude understands Pydantic errors — but worth a quick manual check.

## Sources

### Primary (HIGH confidence)
- FastMCP 3.1.0 source (installed at `.venv/lib/python3.12/site-packages/fastmcp/`) — `function_parsing.py`, `function_tool.py`, `tool.py` verified directly
- In-repo runtime testing of `Literal`, `Annotated`, `Field` schema generation against installed stack
- [FastMCP Tools documentation](https://gofastmcp.com/servers/tools) — Literal support, parameter descriptions, Field() usage
- [MCP Specification: Tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) — inputSchema, validation requirements, error handling

### Secondary (MEDIUM confidence)
- [MCP Tool Description Smells (arxiv.org/html/2602.14878v1)](https://arxiv.org/html/2602.14878v1) — six-component framework, 97% smell rate, +5.85pp improvement from description augmentation
- [MCP Python SDK Issue #1373](https://github.com/modelcontextprotocol/python-sdk/issues/1373) — `enum.Enum` generates `$ref` schema issues vs `Literal` inline `enum`

### Tertiary (LOW confidence)
- [Memorix cross-agent memory bridge](https://github.com/AVIDS2/memorix) — real-world example of inter-agent persistence MCP tool descriptions (framing reference only)

---
*Research completed: 2026-03-18*
*Ready for roadmap: yes*
