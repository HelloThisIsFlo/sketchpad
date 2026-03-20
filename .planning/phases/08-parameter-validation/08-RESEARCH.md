# Phase 8: Parameter Validation - Research

**Researched:** 2026-03-20
**Domain:** Python type annotations, FastMCP parameter validation, Pydantic schema generation
**Confidence:** HIGH

## Summary

This phase is straightforward. The change is a 2-line edit to `src/sketchpad/tools.py` (change type annotation + default value) plus new tests.

FastMCP 3.1.0 uses Pydantic under the hood. A `Literal["replace", "append"]` type annotation on the `mode` parameter produces `{"enum": ["replace", "append"]}` in the JSON schema and rejects invalid values via Pydantic validation *before* the function body runs. The error is returned as an MCP `isError: True` response with a clear message. No custom validation code needed.

**Primary recommendation:** Change `mode: str = "replace"` to `mode: Literal["replace", "append"] = "append"` -- that's it. Everything else is testing.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VALID-01 | `write_file` mode constrained to `Literal["replace", "append"]` -- invalid values rejected before function body | Verified: `Literal` annotation + Pydantic validation in FastMCP 3.1.0 handles this automatically |
| VALID-02 | Default mode changed from `"replace"` to `"append"` | Change default param value; all existing tests pass without modification (verified) |
| VALID-03 | JSON schema includes `{"enum": ["replace", "append"]}` for mode | Verified: `Literal` produces flat `enum` in schema (no `$ref`) |
| VALID-04 | Invalid mode rejected with clear error via `tool.run()` | Verified: Pydantic returns `isError: True` with "Input should be 'replace' or 'append'" |
</phase_requirements>

## Standard Stack

### Core

No new dependencies. Everything is already in the project.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `typing.Literal` | stdlib | Constrain parameter values | Pydantic natively validates Literal types; FastMCP generates `enum` schema from them |
| `fastmcp` | 3.1.0 | MCP server framework | Already installed; handles validation + schema generation automatically |
| `pydantic` | 2.12.x | Validation engine (FastMCP dependency) | Validates `Literal` types, generates JSON Schema `enum` |
| `pytest` | 8.0+ | Test framework | Already in dev dependencies |

**No installation needed.**

## Architecture Patterns

### The Change

Single file edit: `src/sketchpad/tools.py`, line 47.

**Before:**
```python
def write_file(content: str, mode: str = "replace") -> str:
```

**After:**
```python
from typing import Literal

def write_file(content: str, mode: Literal["replace", "append"] = "append") -> str:
```

### How Validation Works (FastMCP 3.1.0)

Two code paths exist, validated empirically:

| Call path | Validates? | Used by |
|-----------|-----------|---------|
| `tool.fn(content="x", mode="banana")` | NO -- bypasses Pydantic | Direct function calls, existing tests |
| `tool.run({"content": "x", "mode": "banana"})` | YES -- Pydantic validates | MCP protocol (what Claude AI calls) |
| `client.call_tool("write_file", {...})` | YES -- goes through `tool.run()` | MCP client integration |

**Implication for tests:** VALID-04 (invalid mode rejected) MUST use `tool.run()` or `client.session.call_tool()`, not `tool.fn()`.

### What the MCP Client Sees

When invalid mode is passed through the MCP protocol:

```
isError: True
content: [TextContent(text="1 validation error for call[write_file]\nmode\n  Input should be 'replace' or 'append' [type=literal_error, ...]")]
```

- Server logs: "Error validating tool 'write_file'" + full Pydantic traceback
- Function body: **never reached**
- File on disk: **never modified**

### Docstring Update

The docstring currently says `'replace' (default)`. Must update to `'append' (default)`.

### Anti-Patterns to Avoid
- **Using `Enum` class**: Generates `$ref`/`$defs` schema -- some MCP clients handle poorly. Use `Literal` instead. (Confirmed: out of scope per REQUIREMENTS.md)
- **Adding manual validation in function body**: Pydantic handles it. Adding `if mode not in (...)` is redundant for the MCP path and creates two error formats.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parameter validation | `if mode not in ("replace", "append"): return "Error..."` | `Literal["replace", "append"]` type annotation | Pydantic validates before function body; generates JSON schema `enum` automatically; one source of truth |
| Schema enum constraint | Manual schema override or custom JSON schema generation | `Literal` annotation | FastMCP + Pydantic generate `{"enum": [...]}` automatically from `Literal` |

## Common Pitfalls

### Pitfall 1: Testing with tool.fn() Instead of tool.run()
**What goes wrong:** Tests pass with invalid mode because `tool.fn()` bypasses Pydantic validation
**Why it happens:** Existing test patterns use `tool.fn()` for convenience
**How to avoid:** VALID-04 tests MUST use `asyncio.run(tool.run({...}))` which goes through Pydantic
**Warning signs:** Test for invalid mode passes without raising/catching an error

### Pitfall 2: Forgetting the Docstring
**What goes wrong:** Docstring says `'replace' (default)` but actual default is `'append'`
**How to avoid:** Update the docstring Args section when changing the default
**Warning signs:** `tools/list` description contradicts schema default

### Pitfall 3: Enum Instead of Literal
**What goes wrong:** Schema contains `$ref` + `$defs` instead of flat `enum`
**Why it happens:** `Enum` class is the "obvious" Python choice
**How to avoid:** Use `Literal["replace", "append"]` -- confirmed to produce flat schema in FastMCP 3.1.0
**Warning signs:** Schema has `$defs` key

## Code Examples

### The Implementation Change (Verified)
```python
# Source: empirical verification against FastMCP 3.1.0
from typing import Literal

def write_file(content: str, mode: Literal["replace", "append"] = "append") -> str:
    """Write to your personal sketchpad. ...

    Args:
        content: The text to write.
        mode: 'append' (default) adds to the end; 'replace' overwrites the file.
    """
```

### Testing Schema (VALID-03)
```python
# Source: empirical verification
async def _check():
    tool = await mcp.get_tool("write_file")
    schema = tool.parameters
    mode_schema = schema["properties"]["mode"]
    assert mode_schema["enum"] == ["replace", "append"]
    assert mode_schema["default"] == "append"
```

### Testing Validation via tool.run() (VALID-04)
```python
# Source: empirical verification
import asyncio
from pydantic import ValidationError

tool = asyncio.run(mcp.get_tool("write_file"))
with pytest.raises(ValidationError, match="literal_error"):
    asyncio.run(tool.run({"content": "hello", "mode": "banana"}))
```

### Testing Default Mode (VALID-02)
```python
# Source: empirical verification -- append to non-existent file produces content as-is
write_fn(content="first")   # default mode=append, file doesn't exist -> "first"
write_fn(content=" second") # default mode=append, file exists -> "first second"
result = read_fn()
assert result == "first second"
```

## Existing Test Impact Analysis

**5 calls in `test_user_isolation.py` lack explicit `mode=` and rely on the current default `"replace"`:**

| Test | Line | What it does | Breaks? |
|------|------|-------------|---------|
| `test_auto_create_dir` | 170 | First write to fresh dir, checks `== "hello"` | NO -- append to non-existent file = same result |
| `test_read_after_write` | 184 | First write to fresh dir, reads back | NO -- same reason |
| `test_two_users_isolated_via_tools` | 197, 202 | First write per user to fresh dir | NO -- same reason |
| `test_response_excludes_username` | 237 | First write to fresh dir | NO -- same reason |

**All 5 are first-writes to non-existent files.** Append mode on non-existent file: `existing = ""`, writes `"" + content` = same as replace. **Verified: all 35 existing tests pass without modification.**

**`test_storage_limits.py`:** All 12 calls already specify `mode=` explicitly. No impact.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ (via `uv run pytest`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -x` |
| Full suite command | `uv run pytest tests/ -v` (or `just test`) |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VALID-01 | mode constrained to Literal["replace", "append"] | unit | `uv run pytest tests/test_parameter_validation.py::test_literal_type_annotation -x` | Wave 0 |
| VALID-02 | default mode is append (not replace) | unit | `uv run pytest tests/test_parameter_validation.py::test_default_mode_is_append -x` | Wave 0 |
| VALID-03 | JSON schema shows enum for mode | unit | `uv run pytest tests/test_parameter_validation.py::test_schema_enum -x` | Wave 0 |
| VALID-04 | invalid mode rejected via tool.run() | unit | `uv run pytest tests/test_parameter_validation.py::test_invalid_mode_rejected -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x`
- **Per wave merge:** `just test && just lint`
- **Phase gate:** Full suite green before verify

### Wave 0 Gaps
- [ ] `tests/test_parameter_validation.py` -- covers VALID-01 through VALID-04
- No framework install needed (pytest already configured)
- No fixture gaps (existing `conftest.py` + per-file helpers sufficient)

## Sources

### Primary (HIGH confidence)
- **Empirical verification** against FastMCP 3.1.0 installed in project (all code examples tested live)
  - `Literal` -> flat `enum` schema: verified
  - `Enum` -> `$ref`/`$defs` schema: verified (confirms out-of-scope decision)
  - `tool.fn()` bypasses validation: verified
  - `tool.run()` validates via Pydantic: verified
  - `isError: True` returned for invalid values: verified
  - All 35 existing tests pass with new default: verified
  - Append to non-existent file == replace: verified

### Secondary (MEDIUM confidence)
- Pydantic 2.12 docs on Literal validation: https://errors.pydantic.dev/2.12/v/literal_error

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, verified against installed versions
- Architecture: HIGH -- empirically tested every claim against the running codebase
- Pitfalls: HIGH -- each pitfall discovered through hands-on testing

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable -- no moving parts, all verified against pinned versions)
