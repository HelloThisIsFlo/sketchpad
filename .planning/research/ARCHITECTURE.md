# Architecture Research

**Domain:** MCP tool API hardening (Literal type + docstring changes) on FastMCP 3.1.0
**Researched:** 2026-03-18
**Confidence:** HIGH

## System Overview: How Tool Definitions Become MCP Schemas

```
┌─────────────────────────────────────────────────────────────────┐
│                    tools.py (your code)                         │
│  @mcp.tool                                                      │
│  def write_file(content: str, mode: Literal[...] = "append")   │
│      """docstring"""                                            │
└──────────────┬──────────────────────────────────┬───────────────┘
               │ signature                        │ docstring
               ▼                                  ▼
┌──────────────────────────────┐   ┌──────────────────────────────┐
│  ParsedFunction.from_function│   │  inspect.getdoc(fn)          │
│  → Pydantic TypeAdapter      │   │  → tool.description          │
│  → .json_schema()            │   │  (raw string, no parsing)    │
│  → compress_schema()         │   └──────────────────────────────┘
│  → tool.parameters           │
└──────────────┬───────────────┘
               │ JSON schema dict
               ▼
┌──────────────────────────────────────────────────────────────────┐
│  Tool.to_mcp_tool() → MCPTool(inputSchema=parameters,           │
│                               description=description)           │
│  → Served to Claude AI via MCP protocol                          │
└──────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Integration Point |
|-----------|----------------|-------------------|
| `tools.py` `write_file` | Function signature = schema source of truth | Change `mode: str` to `mode: Literal["append", "replace"]`, change default |
| `tools.py` docstrings | Raw text becomes `tool.description` in MCP | Change text, no structural changes |
| `ParsedFunction.from_function` | Introspects function → Pydantic TypeAdapter → JSON schema | Unchanged. Already handles `Literal` via Pydantic |
| `compress_schema()` | Strips titles, prunes unused `$defs` | Unchanged. `Literal` produces inline `enum`, no `$defs` |
| `FunctionTool.run()` | Calls `type_adapter.validate_python(arguments)` | Unchanged. Will auto-reject invalid mode values |
| `tool.fn` (direct call) | Raw function, no Pydantic validation | Tests calling `tool.fn()` bypass Literal validation |

## What Changes

### Change 1: Literal Type Annotation

**Before:**
```python
def write_file(content: str, mode: str = "replace") -> str:
```

**After:**
```python
from typing import Literal

def write_file(content: str, mode: Literal["append", "replace"] = "append") -> str:
```

**Schema impact (verified):**

Before:
```json
{
  "properties": {
    "mode": { "default": "replace", "type": "string" }
  }
}
```

After:
```json
{
  "properties": {
    "mode": { "default": "append", "enum": ["append", "replace"], "type": "string" }
  }
}
```

- `enum` array added -- Claude AI sees allowed values
- `default` changes from `"replace"` to `"append"`
- No `$defs` or `$ref` introduced -- Literal maps to inline `enum`

### Change 2: Docstring Reframing

**Before:** User-facing notepad language ("your personal sketchpad", "notes, drafts, ideas")
**After:** Inter-agent persistence framing ("shared agent workspace", "read before acting, write to persist")

**Schema impact:** Only `tool.description` changes. No structural impact. FastMCP passes docstring through `inspect.getdoc()` as raw text.

## Validation Architecture

### Two Validation Layers

```
Client sends: {"mode": "invalid"}
         │
         ▼
┌─ Layer 1: MCP SDK (optional) ────────────────────────────────┐
│  validate_input=strict_input_validation (default: False)      │
│  → JSON Schema validation against inputSchema                 │
│  → When enabled: rejects before reaching FastMCP              │
└───────────────────────────────────────────────────────────────┘
         │ (if validation passes or is disabled)
         ▼
┌─ Layer 2: Pydantic (always active) ──────────────────────────┐
│  FunctionTool.run() → type_adapter.validate_python(arguments) │
│  → Pydantic sees Literal["append", "replace"]                 │
│  → Raises ValidationError for "invalid"                       │
│  → Error: "Input should be 'append' or 'replace'"             │
└───────────────────────────────────────────────────────────────┘
```

**Key finding:** Pydantic validation in `FunctionTool.run()` is the primary enforcement. The `Literal` type annotation provides server-side validation automatically -- no custom `if mode not in (...)` code needed.

**Error propagation:** `ValidationError` bubbles up through MCP protocol as an error response. If `ErrorHandlingMiddleware` is active, it maps `ValueError`/`TypeError` to JSON-RPC error code `-32602` (Invalid params). Without that middleware, the raw `ValidationError` propagates.

### What Happens to Invalid Modes Today

- **Current code:** `mode: str = "replace"` accepts ANY string
- If `mode` is not `"append"`, the `else` branch treats it as replace
- Any typo silently does a full replace -- data loss risk
- **After change:** Pydantic rejects invalid modes before the function body runs

## Test Impact Analysis

### Tests That Call `write_fn(content=...)` Without `mode=`

These tests rely on the default mode. Currently they implicitly use `mode="replace"`.

| Test | File | Current Behavior | After Change |
|------|------|------------------|--------------|
| `test_auto_create_dir` | test_user_isolation.py:170 | `write_fn(content="hello")` → replace | → append |
| `test_read_after_write` | test_user_isolation.py:184 | `write_fn(content="my notes")` → replace | → append |
| `test_two_users_isolated_via_tools` | test_user_isolation.py:197,202 | `write_fn(content=...)` → replace | → append |
| `test_response_excludes_username` | test_user_isolation.py:237 | `write_fn(content="test")` → replace | → append |

**Impact:** These tests write to a fresh file (no pre-existing content). Append to empty file produces the same result as replace on empty file. **No test failures expected.**

Why: The first write to a new file path triggers `sketchpad_path.parent.mkdir(parents=True, exist_ok=True)`. In append mode, `existing` will be `""` (file doesn't exist), so `"" + content` = `content`. Same result.

### Tests That Explicitly Pass `mode=`

| Test | File | `mode=` | Impact |
|------|------|---------|--------|
| `test_replace_exceeds_user_limit` | test_storage_limits.py:109 | `mode="replace"` | None -- explicit |
| `test_append_exceeds_user_limit` | test_storage_limits.py:134 | `mode="append"` | None -- explicit |
| `test_at_user_limit_accepted` | test_storage_limits.py:151 | `mode="replace"` | None -- explicit |
| All other storage tests | test_storage_limits.py | `mode="replace"` | None -- explicit |

**Impact: None.** All storage tests pass `mode=` explicitly.

### Schema Test

| Test | File | Impact |
|------|------|--------|
| `test_tool_schema_excludes_username` | test_user_isolation.py:241 | Checks `write_params == {"content", "mode"}` -- **still passes** |

The schema test checks parameter **names**, not types or values. Adding `enum` to the mode property doesn't change the parameter names.

### Critical: `tool.fn` Direct Calls Bypass Validation

Existing tests call `tool.fn(content=..., mode=...)` directly, NOT `await tool.run({...})`.

- `tool.fn` = the raw Python function. No Pydantic validation.
- `tool.run()` = the Pydantic-validated execution path (what MCP clients hit).
- **Consequence:** Existing tests will NOT exercise Literal validation. New tests needed.

## New Test Requirements

### Must Add

1. **Invalid mode rejection** -- call `write_fn(content="x", mode="invalid")` through `tool.run()`, expect `ValidationError`
2. **Schema enum assertion** -- verify `mode` property has `"enum": ["append", "replace"]` in `tool.parameters`
3. **Default value assertion** -- verify `mode` property has `"default": "append"` in `tool.parameters`

### Consideration: Test via `tool.fn` vs `tool.run()`

| Approach | Validates Literal? | Matches Production? | Existing Pattern? |
|----------|-------------------|--------------------|--------------------|
| `tool.fn(mode="invalid")` | NO -- bypasses Pydantic | No | Yes (current tests) |
| `await tool.run({"mode": "invalid"})` | YES -- Pydantic validates | Yes | No (new pattern) |
| Schema assertion on `tool.parameters` | N/A -- checks contract | Checks what Claude sees | Partially (existing schema test) |

**Recommendation:** Add schema-level assertions (cheapest, most aligned with what Claude AI actually sees) + one `tool.run()` validation test as integration proof.

## Data Flow Changes

### Before (mode: str)

```
Claude sends: {"content": "hello", "mode": "typo"}
  → Pydantic coerces: mode = "typo" (valid string)
  → if mode == "append": ... else: ...
  → "typo" hits else branch → silent replace
```

### After (mode: Literal)

```
Claude sends: {"content": "hello", "mode": "typo"}
  → Pydantic rejects: ValidationError("Input should be 'append' or 'replace'")
  → Error returned to client. Function never executes.

Claude sends: {"content": "hello"}  (no mode)
  → Pydantic fills default: mode = "append"
  → if mode == "append": ... (correct path)
```

### Default Change: "replace" → "append"

```
Claude sends: {"content": "hello"}  (no mode)

BEFORE: default "replace" → full overwrite
AFTER:  default "append"  → adds to end
```

This is a **behavioral change for existing clients** that omit `mode`. Agents currently relying on the default replace behavior will start appending instead. This is the intended design change per the milestone requirements.

## Build Order

Based on dependencies:

1. **Literal type annotation + default change** (tools.py)
   - Smallest change, highest impact
   - Changes: function signature only (one line)
   - Add `from typing import Literal` import
   - Removes need for any manual validation code
   - The existing `if mode == "append": ... else:` logic still works, but the `else` branch now only handles `"replace"` (guaranteed by Pydantic)

2. **Docstring reframing** (tools.py)
   - Both `read_file` and `write_file` docstrings
   - Text-only change, no structural impact
   - Can be done simultaneously with #1

3. **New tests for validation behavior**
   - Schema assertion: `enum` and `default` in `tool.parameters`
   - Validation test: invalid mode through `tool.run()`
   - Depends on #1 being done

4. **Verify existing tests still pass**
   - Run full suite after #1
   - Expected: all 35 tests pass (analysis above)

## Anti-Patterns

### Anti-Pattern 1: Manual Mode Validation Alongside Literal

**What people do:** Add `if mode not in ("append", "replace"): return "Invalid mode"` alongside `Literal` type
**Why it's wrong:** Pydantic already validates before the function body runs. Dead code that will never execute.
**Do this instead:** Trust the `Literal` annotation. Remove any manual validation if it existed.

### Anti-Pattern 2: Testing Literal Validation via tool.fn()

**What people do:** Call `tool.fn(mode="invalid")` and expect it to fail
**Why it's wrong:** `tool.fn` is the raw function -- no Pydantic validation. The test would pass silently with the invalid mode hitting the `else` branch.
**Do this instead:** Test via `tool.run()` for validation behavior, or assert on `tool.parameters` schema for the contract.

### Anti-Pattern 3: Docstring Parsing Assumptions

**What people do:** Assume FastMCP parses Google-style `Args:` sections into per-parameter descriptions in the JSON schema
**Why it's wrong:** FastMCP uses `inspect.getdoc()` and puts the entire docstring into `tool.description` as a raw string. There are no per-parameter description fields in the generated schema.
**Do this instead:** Keep `Args:` section in docstring for human readability and because Claude AI reads the full description. But don't expect it to appear in JSON schema `properties.*.description`.

## Integration Points

### What Claude AI Sees (Before vs After)

| Aspect | Before | After |
|--------|--------|-------|
| `tool.description` | "Write to your personal sketchpad..." | Inter-agent persistence framing |
| `mode` schema | `{"type": "string", "default": "replace"}` | `{"type": "string", "default": "append", "enum": ["append", "replace"]}` |
| Invalid mode behavior | Silently treated as replace | Error: "Input should be 'append' or 'replace'" |
| No-mode behavior | Replace (overwrite) | Append (add to end) |

### Internal Boundaries

| Boundary | Communication | Impact |
|----------|---------------|--------|
| `tools.py` → `ParsedFunction` | Function signature introspection | Automatic -- Literal flows through |
| `tools.py` → `FunctionTool.run()` | Pydantic TypeAdapter validates at call time | Automatic -- validation is free |
| `tools.py` → `compress_schema()` | Schema optimization | No impact -- Literal produces simple inline enum |
| Test fixtures → `tool.fn` | Direct function call | No validation -- tests must account for this |

## Sources

- FastMCP 3.1.0 source (installed in .venv): `function_parsing.py`, `function_tool.py`, `tool.py`
- Pydantic JSON schema generation (verified via `TypeAdapter(Literal[...]).json_schema()`)
- Direct testing of schema output and validation behavior in FastMCP runtime
- Existing test suite analysis: `test_user_isolation.py`, `test_storage_limits.py`

---
*Architecture research for: MCP tool API hardening (Literal type + docstring changes)*
*Researched: 2026-03-18*
