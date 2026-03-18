# Stack Research

**Domain:** MCP tool API hardening (Literal validation + agent-optimized descriptions)
**Researched:** 2026-03-18
**Confidence:** HIGH

## Key Finding: No New Dependencies Required

Both v1.2 features are achievable with zero stack changes. Everything needed is already in the dependency tree via FastMCP 3.1.0 -> Pydantic 2.12.5 -> Python 3.12 stdlib.

## What's Already Available

### Literal Type Validation

| Component | Version | Provides | Verified |
|-----------|---------|----------|----------|
| `typing.Literal` | Python 3.12 stdlib | Type annotation constraining values to a fixed set | Tested in-repo |
| Pydantic TypeAdapter | 2.12.5 (via FastMCP) | Converts `Literal["a", "b"]` to JSON Schema `{"enum": ["a", "b"], "type": "string"}` | Tested in-repo |
| FastMCP `ParsedFunction` | 3.1.0 | Calls Pydantic's `get_cached_typeadapter()` on tool functions, auto-generating `inputSchema` | Verified in source |

**How it works end-to-end:**
1. You annotate `mode: Literal["replace", "append"] = "append"` in the function signature
2. FastMCP's `ParsedFunction.from_function()` feeds it to Pydantic's `TypeAdapter`
3. Pydantic generates `{"enum": ["replace", "append"], "type": "string", "default": "append"}`
4. FastMCP compresses the schema (strips titles) and serves it as the tool's `inputSchema`
5. At call time, Pydantic's `TypeAdapter.validate_python()` rejects invalid values with `literal_error`

**Verified output (tested against installed packages):**
```json
{
  "properties": {
    "mode": {
      "default": "append",
      "enum": ["replace", "append"],
      "type": "string"
    }
  }
}
```

**Validation error for invalid input (tested):**
```
Input should be 'replace' or 'append' [type=literal_error, input_value='delete', input_type=str]
```

No manual `if mode not in (...)` guard needed. Pydantic handles it before the function body runs.

### Parameter-Level Descriptions

| Component | Version | Provides | Verified |
|-----------|---------|----------|----------|
| `typing.Annotated` | Python 3.12 stdlib | Attaches metadata to type annotations | Tested in-repo |
| `pydantic.Field` | 2.12.5 (via FastMCP) | `description` kwarg propagates to JSON Schema `description` field | Tested in-repo |
| FastMCP `compress_schema` | 3.1.0 | Preserves `description` fields while stripping `title` | Verified in source |

**Usage pattern:**
```python
from typing import Annotated, Literal
from pydantic import Field

def write_file(
    content: Annotated[str, Field(description="Text to persist. Supports Markdown.")],
    mode: Annotated[
        Literal["replace", "append"],
        Field(description="replace: overwrite file; append: add to end")
    ] = "append",
) -> str:
    """Persist text to the user-scoped sketchpad file."""
```

**Verified output:**
```json
{
  "properties": {
    "content": {
      "description": "Text to persist. Supports Markdown.",
      "type": "string"
    },
    "mode": {
      "default": "append",
      "description": "replace: overwrite file; append: add to end",
      "enum": ["replace", "append"],
      "type": "string"
    }
  }
}
```

### Tool Description (Docstring)

- FastMCP extracts the function docstring via `inspect.getdoc(fn)` in `ParsedFunction.from_function()`
- The docstring becomes the `description` field on the MCP `Tool` object
- No special library needed -- just write a better docstring

## Alternatives Considered

| Approach | Recommended | Why Not (if not recommended) |
|----------|-------------|------------------------------|
| `Literal["replace", "append"]` | **Yes** | N/A -- best fit |
| Python `enum.Enum` | No | MCP SDK issue #1373: Enum generates `$ref` schema that some clients handle poorly. Literal embeds `enum` constraint inline, which is universally supported. |
| Manual validation (`if mode not in ...`) | No | Redundant. Pydantic rejects invalid values before function body executes. Adding manual checks means two validation paths to maintain. |
| `pydantic.Field(pattern=...)` on `str` | No | Regex is less expressive for discrete values. `Literal` produces `enum` in schema which LLMs understand natively. |
| `Annotated[str, Field(description=...)]` for param docs | **Yes** | N/A -- best fit |
| Docstring `Args:` section for param docs | No | FastMCP does not parse Google/Numpy-style docstring sections into per-parameter descriptions. Only `Annotated[..., Field(description=...)]` propagates to JSON Schema. |

## What NOT to Add

| Avoid | Why | Current Stack Handles It |
|-------|-----|--------------------------|
| Any new pip dependency | Both features use stdlib + existing Pydantic | `typing.Literal`, `typing.Annotated`, `pydantic.Field` |
| `enum` stdlib module | Generates `$ref`-based schemas; Literal is simpler and better supported by MCP clients | `Literal` type annotation |
| Custom validation middleware | Pydantic's TypeAdapter already validates Literal constraints before the tool function runs | FastMCP's built-in validation pipeline |
| `jsonschema` library | Schema generation is Pydantic's job; no need for separate validation | Pydantic 2.12.5 |
| Description templating library | Tool descriptions are simple strings; no templating needed | Python docstrings + `Field(description=...)` |

## Imports Needed (No Install Required)

```python
# All from stdlib or existing dependencies
from typing import Annotated, Literal
from pydantic import Field
```

## Version Compatibility

| Package | Installed | Required | Notes |
|---------|-----------|----------|-------|
| Python | 3.12.8 | >=3.8 for `Literal`, >=3.9 for `Annotated` | Well within range |
| Pydantic | 2.12.5 | >=2.0 for TypeAdapter + Literal schema gen | Well within range |
| FastMCP | 3.1.0 | >=2.0 for ParsedFunction pipeline | Well within range |

No version bumps or updates needed.

## Sources

- FastMCP 3.1.0 source code (installed at `.venv/lib/python3.12/site-packages/fastmcp/`) -- `tools/function_parsing.py`, `tools/function_tool.py`, `tools/tool.py` verified directly
- In-repo testing of `Literal`, `Annotated`, `Field` schema generation against installed FastMCP+Pydantic -- HIGH confidence
- [FastMCP Tools documentation](https://gofastmcp.com/servers/tools) -- confirms Literal support, Annotated+Field for param descriptions
- [MCP Python SDK Issue #1373](https://github.com/modelcontextprotocol/python-sdk/issues/1373) -- documents Enum `$ref` schema issues vs Literal inline `enum`
- [MCP Specification: Tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) -- `inputSchema` is JSON Schema; `enum` constraint is standard
- [Writing Effective Tools for Agents](https://modelcontextprotocol.info/docs/tutorials/writing-effective-tools/) -- tool description best practices for LLM consumption

---
*Stack research for: Sketchpad v1.2 Tool Polish*
*Researched: 2026-03-18*
