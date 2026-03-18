# Feature Landscape

**Domain:** MCP tool API hardening and AI-optimized tool descriptions
**Researched:** 2026-03-18
**Milestone:** v1.2 Tool Polish

## Table Stakes

Features that must ship for v1.2 to deliver value. Without these, the milestone is incomplete.

| Feature | Why Expected | Complexity | Dependencies |
|---------|--------------|------------|--------------|
| `Literal["replace", "append"]` type annotation on `mode` param | Prevents silent misuse -- any string currently accepted, bad values fall through to replace path silently | Low | None -- Pydantic + FastMCP already support this |
| Default `mode` changed from `"replace"` to `"append"` | Append is safer default -- agents adding notes shouldn't clobber existing content. Replace requires intent. | Low | Must ship alongside Literal constraint |
| Server-side validation error for invalid mode | Even with schema-level enum, MCP spec says "Servers MUST validate all tool inputs." Defense in depth. | Low | Depends on Literal annotation being in place |
| Tool descriptions reframed for inter-agent persistence | Current descriptions say "personal sketchpad" / "notes, drafts, ideas" -- misframes the tool for AI agents. Agents need to understand this is a shared persistence layer across sessions and clients. | Low-Med | None -- docstring changes only |
| Parameter descriptions via `Annotated[..., Field(description=...)]` | Current `mode` param has no schema-level description -- agent sees only the raw enum values. `content` param also undescribed in schema. | Low | None |

## Differentiators

Features that improve quality beyond minimum viable. Not required for v1.2 but add real value.

| Feature | Value Proposition | Complexity | Dependencies |
|---------|-------------------|------------|--------------|
| Usage guidelines in tool description | Research shows 97% of MCP tool descriptions lack usage guidelines. Adding "when to use" criteria measurably improves agent tool selection (+5.85pp success rate). | Low | Ships with description rewrite |
| Limitations stated in tool description | Document storage limits (20KB), single-file nature, and append-default behavior in the description. Reduces agent confusion and unnecessary retry loops. | Low | Ships with description rewrite |
| `content` param description with format hint | Tell the agent "Markdown recommended" at the schema level, not just the docstring. Schema-level descriptions are more reliably consumed by all MCP clients. | Low | None |
| Test for JSON schema enum constraint | Verify the generated `inputSchema` contains `{"enum": ["replace", "append"]}` for the mode parameter. Catches regressions if type annotation changes. | Low | Literal annotation in place |
| Test for invalid mode rejection | Verify that passing `mode="invalid"` is rejected with a clear error, not silently treated as replace. | Low | Validation logic in place |

## Anti-Features

Features to explicitly NOT build in v1.2. Scope discipline.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Runtime mode validation via manual if/else | FastMCP + Pydantic handle this automatically via Literal type. Manual validation is redundant code that can drift from the schema. | Use `Literal["replace", "append"]` -- Pydantic's TypeAdapter validates before the function body runs |
| Enum class for mode values | Overkill for two values. Pydantic `Literal` generates the same `{"enum": [...]}` JSON Schema without a separate class. Enum members also have `.value` indirection that complicates the function body. | `Literal["replace", "append"]` is sufficient |
| Structured output schema (`outputSchema`) | MCP spec supports it, FastMCP auto-generates it from return types. But the tools return plain strings -- adding outputSchema for `str` adds ceremony without value. Save for vault tools. | Keep returning `str`, no outputSchema |
| Examples in tool descriptions | Research paper found removing examples "does not statistically degrade performance." For two simple tools, examples waste tokens in the agent's context window. | Rely on clear purpose + parameter descriptions |
| Tool annotations (`ToolAnnotations`) | MCP spec supports `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`. Nice-to-have but Claude AI doesn't currently use these for tool selection decisions. Spec says clients MUST treat as untrusted anyway. | Defer to v1.3 or vault project |
| `title` field on tools | MCP spec has optional `title` for human-readable display name. Current tool names (`read_file`, `write_file`) are already clear. | Not needed |

## Feature Dependencies

```
Literal type annotation  -->  Default change to "append"
                          -->  Schema enum test
                          -->  Invalid mode rejection test

Description rewrite (standalone, no code dependencies)
  --> Parameter descriptions via Field()
```

Both tracks (validation + descriptions) are independent of each other and can be implemented in parallel or either order.

## Implementation Details

### Literal Type Annotation

**How it works in the stack:**

1. Python `Literal["replace", "append"]` is a standard `typing` construct
2. FastMCP's `ParsedFunction.from_function()` calls `get_cached_typeadapter(wrapper_fn)` which creates a Pydantic TypeAdapter
3. Pydantic v2 converts `Literal["replace", "append"]` to JSON Schema `{"enum": ["replace", "append"]}` (HIGH confidence -- verified in Pydantic docs and FastMCP source)
4. FastMCP sends this as `inputSchema` in `tools/list` response
5. At call time, `type_adapter.validate_python(arguments)` rejects values not in the Literal before the function body executes
6. MCP spec error handling: invalid arguments should return JSON-RPC error code `-32602`

**Current code (tools.py:47):**
```python
def write_file(content: str, mode: str = "replace") -> str:
```

**Target code:**
```python
from typing import Literal
def write_file(content: str, mode: Literal["replace", "append"] = "append") -> str:
```

**Generated JSON Schema change:**
```json
// Before: mode accepts any string
{"type": "string", "default": "replace"}

// After: mode constrained to enum
{"enum": ["replace", "append"], "default": "append"}
```

**Confidence:** HIGH -- verified by reading FastMCP source (`function_parsing.py` -> Pydantic TypeAdapter -> `json_schema()`), Pydantic v2 docs on Literal->enum conversion, and FastMCP official docs showing Literal example.

### Tool Description Rewrite

**Research-backed principles (from arxiv.org/html/2602.14878v1):**

Six components of effective MCP tool descriptions:
1. **Purpose** -- what the tool does (required)
2. **Guidelines** -- when and how to use it (high impact)
3. **Limitations** -- constraints and failure modes (high impact)
4. **Parameter explanation** -- detailed in schema, not just docstring (high impact)
5. **Length** -- 3-4+ sentences proportional to complexity (moderate impact)
6. **Examples** -- illustrative usage (lowest impact -- can skip)

**Key reframing insight:** Current descriptions say "personal sketchpad" and "notes, drafts, ideas." The actual use case is inter-agent persistence -- Agent A (Claude on phone) writes context, Agent B (Claude Code in terminal) reads it. The description should communicate:

- This is a **shared persistence layer**, not a notepad
- All agents using the same GitHub identity share this file
- Append is the default (preserves existing content from other agents)
- 20KB limit exists
- Markdown recommended for structure

**Confidence:** MEDIUM -- the research paper's findings are solid, but "inter-agent persistence" framing is novel and hasn't been validated with real agent behavior on this specific server.

### Parameter Descriptions via Annotated + Field

**FastMCP supports two approaches (verified in official docs):**

1. Simple string (v2.11.0+): `Annotated[str, "description here"]`
2. Field-based: `Annotated[str, Field(description="description here")]`

Use Field-based since it's the established pattern and allows adding constraints later. The descriptions appear in the `inputSchema` properties, which agents parse for parameter semantics.

**Confidence:** HIGH -- verified in FastMCP docs and source code.

## MVP Recommendation

Ship both tracks together as a single milestone:

1. **Literal type annotation + default change** -- mechanical change, highest safety value
2. **Description rewrite with Field() param descriptions** -- highest agent-behavior value
3. **Two new tests** -- schema enum verification + invalid mode rejection

**Defer:** ToolAnnotations, outputSchema, examples in descriptions, title field.

## Existing Test Impact

- `test_tool_schema_excludes_username` already verifies `write_file` params are `{"content", "mode"}` -- will continue passing
- Storage limit tests use `mode="replace"` and `mode="append"` explicitly -- will continue passing
- Tests calling `write_fn(content="hello")` without mode will now get `"append"` default instead of `"replace"` -- **these tests need updating** to either specify `mode="replace"` explicitly or account for append behavior

## Sources

- [FastMCP Tools Documentation](https://gofastmcp.com/servers/tools) -- Literal type support, parameter descriptions, Field() usage
- [MCP Tool Description Smells (arxiv.org)](https://arxiv.org/html/2602.14878v1) -- six-component framework, 97% smell rate, +5.85pp improvement from augmentation
- [MCP Specification: Tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) -- inputSchema, description field, validation requirements, error handling
- [Pydantic Literal->enum schema](https://github.com/pydantic/pydantic/issues/11277) -- Literal["a", "b"] generates {"enum": ["a", "b"]} in JSON Schema
- [Memorix cross-agent memory bridge](https://github.com/AVIDS2/memorix) -- real-world example of inter-agent persistence MCP tool descriptions
- FastMCP source: `fastmcp/tools/function_parsing.py` (local, verified) -- ParsedFunction -> Pydantic TypeAdapter -> json_schema()
- FastMCP source: `fastmcp/tools/function_tool.py` (local, verified) -- FunctionTool.run() validates via type_adapter.validate_python()
