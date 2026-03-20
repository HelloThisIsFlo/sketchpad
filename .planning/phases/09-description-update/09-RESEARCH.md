# Phase 9: Description Update - Research

**Researched:** 2026-03-20
**Domain:** MCP tool descriptions, FastMCP schema generation, agent prompt engineering
**Confidence:** HIGH

## Summary

Phase 9 rewrites `read_file` and `write_file` docstrings and adds `Field(description=...)` annotations so Claude AI (and other MCP clients) understands the Sketchpad as a shared persistence layer with clear usage guardrails. It also folds in a small behavior change: append mode prepends `\n` before new content.

FastMCP 3.1.0 (installed) supports two independent description surfaces: (1) function docstrings become the tool-level `description` in `tools/list`, and (2) `Annotated[Type, Field(description=...)]` annotations surface as `description` fields inside the JSON schema `properties`. Both are verified working with the current codebase. The existing `Args:` docstring section is redundant once `Field()` annotations exist and should be removed.

**Primary recommendation:** Use docstrings for tool-level "what/when/when-not" guidance. Use `Annotated[Type, Field(description=...)]` for parameter-level descriptions. Remove the `Args:` section from docstrings. Add newline separator in append logic. Update one existing test that breaks from the newline change.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use explicit "Do / Do NOT" guardrails in `write_file` description -- agents need firm boundaries or they dump everything here
- **D-02:** Do NOT mention storage limits in descriptions -- if agents hit the limit, the description itself is the problem
- **D-03:** Use "Sketchpad" (capitalized, proper noun) in all descriptions -- matches project name, server name, tool names
- **D-04:** Drop "scratchpad" from the draft todo -- replace all instances with "Sketchpad"
- **D-05:** Append mode always prepends a single `\n` before new content -- simple, predictable
- **D-06:** Mention newline behavior briefly in the `mode` parameter description
- **D-07:** `read_file` description: explain WHAT the Sketchpad contains + explicitly state "read when the user asks you to check for prior context"
- **D-08:** `write_file` description: write ONLY when user explicitly asks -- no proactive agent writes
- **D-09:** Remove "future agent session needs context" as a write trigger from the draft -- user controls all persistence

### Claude's Discretion
- Exact wording of `Field(description=...)` for `content` and `mode` parameters
- Final sentence-level polish of docstrings
- Whether to use bullet lists or prose in the docstring body

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DESC-01 | `read_file` and `write_file` docstrings reframed as inter-agent persistence layer | FastMCP extracts docstrings as tool descriptions; multiline docstrings with bullet lists work cleanly (verified) |
| DESC-02 | `content` and `mode` parameters have `Field(description=...)` annotations visible in JSON schema | `Annotated[Type, Field(description=...)]` produces `description` in JSON schema properties (verified with FastMCP 3.1.0) |
| DESC-03 | Tool descriptions include usage guidelines (when to use) and limitations (when NOT to use) | Multiline docstrings with "Do / Do NOT" format survive extraction intact (verified) |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastMCP | 3.1.0 (installed) | MCP server framework | Already in use; handles docstring extraction and schema generation |
| Pydantic | (bundled with FastMCP) | `Field(description=...)` annotations | Standard way to add metadata to function parameters |

### Supporting
No new dependencies. This phase modifies existing code only.

## Architecture Patterns

### Two Description Surfaces

FastMCP exposes tool metadata to MCP clients through two independent channels:

1. **Tool-level description** (docstring) -- appears as `description` field in `tools/list` response
2. **Parameter-level descriptions** (`Field(description=...)`) -- appear as `description` inside each property in `inputSchema`

Current state (no parameter descriptions):
```json
{
  "content": { "type": "string" },
  "mode": { "default": "append", "enum": ["replace", "append"], "type": "string" }
}
```

Target state (with `Field(description=...)`):
```json
{
  "content": { "description": "The text to write", "type": "string" },
  "mode": { "description": "append adds to end; replace overwrites", "default": "append", "enum": ["replace", "append"], "type": "string" }
}
```

### Pattern: Annotated + Field for Parameter Descriptions

```python
# Source: verified locally against FastMCP 3.1.0
from typing import Annotated, Literal
from pydantic import Field

@mcp.tool
def write_file(
    content: Annotated[str, Field(description="The text to write")],
    mode: Annotated[Literal["replace", "append"], Field(description="...")] = "append"
) -> str:
    """Tool-level description here (no Args section needed)."""
```

Key findings:
- `Annotated[Literal[...], Field(description=...)]` produces BOTH `enum` and `description` in the JSON schema
- `get_type_hints(fn)` (without `include_extras=True`) strips the `Annotated` wrapper, so the existing `test_literal_type_annotation` test still passes
- The `Args:` docstring section becomes redundant and should be removed -- parameter descriptions now live in the schema

### Anti-Patterns to Avoid
- **Duplicating parameter docs in docstring AND Field():** FastMCP includes the full docstring (including `Args:` sections) as the tool description. Having `Args:` in the docstring AND `Field(description=...)` means agents see parameter descriptions twice -- once in prose, once in schema. Remove the `Args:` section.
- **Mentioning storage limits in descriptions (D-02):** If an agent hits the limit, the tool returns an error message. Putting limits in the description just adds noise and causes agents to overthink writes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parameter descriptions in JSON schema | Custom schema post-processing | `Annotated[Type, Field(description=...)]` | Pydantic + FastMCP handle it natively |
| Tool description extraction | Manual `tools/list` overrides | Function docstrings | FastMCP extracts them automatically |

## Common Pitfalls

### Pitfall 1: Existing test breaks from newline separator
**What goes wrong:** `test_default_mode_is_append` asserts `result == "first second"` after writing `"first"` then `" second"`. With the newline separator, the result becomes `"first\n second"`.
**Why it happens:** The test was written for direct concatenation behavior.
**How to avoid:** Update the test to expect the newline separator, or restructure the test data.
**Warning signs:** Test failure after modifying append logic.

### Pitfall 2: Newline prepended on first write to empty file
**What goes wrong:** If newline is always prepended, the first append to a non-existent file starts with `\n`.
**Why it happens:** Not checking whether existing content is empty before prepending.
**How to avoid:** Only prepend `\n` when the file already has content (existing content is non-empty).
**Warning signs:** Welcome message replacement starts with a blank line.

### Pitfall 3: Double newlines when existing content ends with newline
**What goes wrong:** If existing content ends with `\n` and we prepend another `\n`, there's a double newline gap.
**Why it happens:** Not checking trailing character of existing content.
**How to avoid:** Decision D-05 says "always prepends a single `\n`" -- this means always add one, keeping behavior simple and predictable. Double newlines are acceptable (they just create a blank line, which is valid Markdown paragraph separation). Alternatively, only add `\n` if existing content doesn't end with one.
**Warning signs:** Extra blank lines in sketchpad content.

### Pitfall 4: Annotated type breaks existing type hint introspection
**What goes wrong:** Tests using `get_type_hints(fn)` to check `Literal["replace", "append"]` might fail.
**Why it happens:** `Annotated` wraps the type.
**How to avoid:** Already verified: `get_type_hints(fn)` (default, without `include_extras=True`) strips `Annotated` and returns the bare `Literal` type. Existing test passes unchanged.
**Warning signs:** `test_literal_type_annotation` failure (should NOT happen).

## Code Examples

### Current tool signatures (before)

```python
# Source: src/sketchpad/tools.py lines 34-57
@mcp.tool
def read_file() -> str:
    """Read your personal sketchpad. This is your private Markdown file,
    shared across all your AI agents (Claude, Cursor, etc.) that use
    the same GitHub identity."""

@mcp.tool
def write_file(content: str, mode: Literal["replace", "append"] = "append") -> str:
    """Write to your personal sketchpad. Use this for notes, drafts,
    ideas -- Markdown formatting recommended but not required. Your
    sketchpad is shared across all your AI agents that use the same
    GitHub identity.

    Args:
        content: The text to write.
        mode: 'append' (default) adds to the end; 'replace' overwrites the file.
    """
```

### Target pattern (after)

```python
# Verified: this exact pattern produces correct JSON schema with FastMCP 3.1.0
from typing import Annotated, Literal
from pydantic import Field

@mcp.tool
def read_file() -> str:
    """Read the Sketchpad -- a shared persistence layer for AI agents
    on the same GitHub identity.

    [Usage guidance per D-07]"""

@mcp.tool
def write_file(
    content: Annotated[str, Field(description="The text to write. Markdown recommended.")],
    mode: Annotated[
        Literal["replace", "append"],
        Field(description="append (default) adds to end with a newline separator; replace overwrites the file.")
    ] = "append",
) -> str:
    """Write to the Sketchpad -- a shared persistence layer for AI agents
    on the same GitHub identity.

    [Do/Do NOT guardrails per D-01, D-08, D-09]"""
```

### Newline separator implementation

```python
# In write_file, replace line 94:
#   sketchpad_path.write_text(existing + content, encoding="utf-8")
# With:
if existing:
    sketchpad_path.write_text(existing + "\n" + content, encoding="utf-8")
else:
    sketchpad_path.write_text(content, encoding="utf-8")
```

Note: size check on line 69 (`existing_size + content_bytes`) should account for the extra newline byte. The 1-byte difference is negligible for limit enforcement but should be correct for consistency.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (installed) |
| Config file | none (uses defaults, tests/ directory) |
| Quick run command | `python3 -m pytest tests/ -x -q` |
| Full suite command | `python3 -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DESC-01 | Docstrings reframed as persistence layer | unit | `python3 -m pytest tests/test_descriptions.py::test_read_file_description -x` | Wave 0 |
| DESC-01 | Docstrings reframed as persistence layer | unit | `python3 -m pytest tests/test_descriptions.py::test_write_file_description -x` | Wave 0 |
| DESC-02 | Field(description) visible in JSON schema | unit | `python3 -m pytest tests/test_descriptions.py::test_content_param_has_description -x` | Wave 0 |
| DESC-02 | Field(description) visible in JSON schema | unit | `python3 -m pytest tests/test_descriptions.py::test_mode_param_has_description -x` | Wave 0 |
| DESC-03 | Descriptions include usage guidelines | unit | `python3 -m pytest tests/test_descriptions.py::test_write_description_has_guardrails -x` | Wave 0 |
| D-05 | Newline separator in append mode | unit | `python3 -m pytest tests/test_descriptions.py::test_append_newline_separator -x` | Wave 0 |
| D-05 | No leading newline on first write | unit | `python3 -m pytest tests/test_descriptions.py::test_first_append_no_leading_newline -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/ -x -q`
- **Per wave merge:** `python3 -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_descriptions.py` -- new file covering DESC-01, DESC-02, DESC-03 and newline behavior
- [ ] Update `tests/test_parameter_validation.py::test_default_mode_is_append` -- assertion needs updating for newline separator

## Existing Test Impact

Tests that WILL break from the newline separator change:
- `test_default_mode_is_append` (test_parameter_validation.py:87) -- asserts `"first second"`, will become `"first\n second"` after change

Tests that will NOT break:
- `test_literal_type_annotation` -- `get_type_hints()` strips `Annotated`, still returns bare `Literal`
- `test_schema_enum` -- `enum` field still present in schema; `description` field is additive
- `test_append_exceeds_user_limit` -- size math shifts by 1 byte, still exceeds limit
- All replace-mode tests -- unaffected by append newline logic

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Args:` in docstring for param docs | `Field(description=...)` in type annotations | FastMCP 2.x+ | Structured schema descriptions instead of prose parsing |
| Single description surface | Tool-level + parameter-level descriptions | MCP spec | Agents see guidance at both tool selection and parameter filling stages |

## Open Questions

1. **Newline on content that already ends with newline**
   - What we know: D-05 says "always prepends a single `\n`"
   - What's unclear: Does "always" mean even when existing content ends with `\n`? (produces blank line)
   - Recommendation: Simplest interpretation -- always prepend `\n` if file has content. Blank lines are valid Markdown. Keep it predictable.

## Sources

### Primary (HIGH confidence)
- FastMCP 3.1.0 source code -- `/Users/flo/Work/Private/Dev/Agentic/Capacities/sketchpad/.venv/lib/python3.12/site-packages/fastmcp/tools/function_parsing.py` -- schema generation via Pydantic TypeAdapter
- Local verification -- `Annotated[Literal[...], Field(description=...)]` tested against installed FastMCP, produces correct JSON schema
- Local verification -- `get_type_hints(fn)` strips `Annotated`, existing tests unaffected
- [FastMCP Tools docs](https://gofastmcp.com/servers/tools) -- docstring extraction, Field description usage, Annotated shorthand

### Secondary (MEDIUM confidence)
- [Blog: Stricter MCP schemas and agent reliability](https://blog.pamelafox.org/2026/03/do-stricter-mcp-tool-schemas-increase.html) -- parameter descriptions help with ambiguous parameters; frontier models handle most cases well regardless

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- FastMCP 3.1.0 verified locally, all patterns tested
- Architecture: HIGH -- both description surfaces verified with actual schema output
- Pitfalls: HIGH -- existing tests analyzed line-by-line, breaking test identified
- Newline behavior: HIGH -- implementation location identified (line 94), edge cases documented

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable -- FastMCP major version unlikely to change)
