# Pitfalls Research

**Domain:** MCP tool API hardening -- parameter validation and description changes on a live server
**Researched:** 2026-03-18
**Confidence:** HIGH (verified against FastMCP 3.1.0 source and runtime behavior)

## Critical Pitfalls

### Pitfall 1: Default change (replace -> append) silently breaks existing tests

**What goes wrong:**
35 tests call `write_fn(content="...")` without explicit `mode=`. Currently defaults to `"replace"`. After changing to `"append"`, every test that expects `write_file` to overwrite content will silently append instead. Tests still pass (no assertion on exact content in many cases), but behavior is wrong. Worse: tests that DO assert exact content (e.g., `test_read_after_write` expects `"my notes"`, not `"Welcome...my notes"`) will fail with confusing diffs.

**Why it happens:**
- Default parameter changes propagate to every callsite that omits the argument
- Tests calling `write_fn(content="hello")` currently get replace semantics
- After default change, same call gets append semantics
- On a fresh test dir (no prior file), append to empty == replace, so some tests pass by accident

**How to avoid:**
1. Audit every test callsite of `write_fn()` -- grep for calls without explicit `mode=`
2. Add explicit `mode="replace"` to every test that intends replace behavior
3. Run full test suite BEFORE AND AFTER the default change
4. Add a dedicated test for the new default: `write_fn(content="hello")` then `write_fn(content="world")` should produce `"helloworld"`, not `"world"`

**Warning signs:**
- Tests pass but integration behavior changes
- `test_auto_create_dir` and `test_read_after_write` may fail with unexpected content
- Any test pre-populating files then calling `write_fn` without `mode=` will accumulate content

**Phase to address:** First phase (parameter validation) -- audit tests BEFORE changing the default

---

### Pitfall 2: Pydantic ValidationError leaks framework internals to AI agent

**What goes wrong:**
When `Literal["replace", "append"]` rejects invalid input, Pydantic raises `ValidationError` with a raw error like:
```
1 validation error for call[write_file]
mode
  Input should be 'replace' or 'append' [type=literal_error, input_value='banana', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/literal_error
```
FastMCP catches this and returns it as `isError=true` in the MCP response. The AI agent sees Pydantic's internal error format, not a user-friendly message.

**Why it happens:**
- FastMCP 3.1.0 validates via `type_adapter.validate_python(arguments)` before calling the function
- The `ValidationError` is caught at the server level and serialized as a `ToolError`
- No opportunity for the tool to provide a custom error message
- This is actually FastMCP working correctly -- but the error UX is rough

**How to avoid:**
- Accept this as the validation layer. The error IS informative (tells the agent exactly what values are allowed)
- Do NOT add redundant manual validation inside the function body -- it will never fire because Pydantic validates first
- Verify the error format is acceptable for Claude AI as a client (it is -- Claude understands Pydantic errors)
- If custom error messages are needed later, use `Annotated[str, Field(pattern=...)]` with custom `json_schema_extra` instead of Literal

**Warning signs:**
- Writing duplicate validation code inside `write_file` that can never execute
- Tests expecting a custom error message from the function when Pydantic intercepts first

**Phase to address:** Parameter validation phase -- verify error format once, then accept it

---

### Pitfall 3: Docstring changes alter AI agent behavior in unpredictable ways

**What goes wrong:**
Tool descriptions are the primary interface for AI agents. Changing from "Use this for notes, drafts, ideas" to "This is an inter-agent persistence layer, NOT a user-facing notepad" fundamentally changes WHEN and HOW Claude decides to use the tool. The new framing includes negative instructions ("Do NOT write here to save content for the user to read") which Claude may over-apply, refusing to write even when the user explicitly asks.

**Why it happens:**
- AI agents treat tool descriptions as behavioral instructions
- Negative instructions ("Do NOT") are notoriously tricky -- agents may over-generalize
- No way to regression-test agent decision-making with unit tests
- Description changes are invisible in code review (just docstrings)

**How to avoid:**
1. Ship description changes and parameter validation as separate deployments -- isolate which change caused behavioral shifts
2. Test the new descriptions manually with Claude AI on the actual deployed server
3. Start with shorter, directive descriptions. Avoid long negative lists
4. Keep "The user explicitly asks you to write something" as the first positive trigger
5. Monitor first few sessions after deployment for unexpected refusals

**Warning signs:**
- Claude says "I shouldn't save that to the scratchpad" when user explicitly asks
- Claude stops reading scratchpad at session start (over-interprets "only if relevant")
- Claude writes nothing, ever, because it's uncertain whether context qualifies

**Phase to address:** Description update phase -- deploy separately from parameter changes, manual UAT required

---

### Pitfall 4: Literal type changes the JSON Schema, possibly breaking cached tool schemas on clients

**What goes wrong:**
The current schema has `mode` as `{"type": "string", "default": "replace"}`. After the change, it becomes `{"type": "string", "default": "append", "enum": ["replace", "append"]}`. If Claude AI or other MCP clients cache tool schemas (and they do -- `tools/list` is called once at connection start), a client connected before the deployment will have the old schema. The client might:
- Send `mode="replace"` (old default) when the user expects append
- Not present the enum constraint to the agent, allowing invalid values

**Why it happens:**
- MCP clients call `tools/list` once during session initialization
- Schema changes require a new MCP session (reconnection) to take effect
- No MCP notification mechanism for "schema changed" in the current protocol
- Cached schemas can persist across server restarts if the client maintains the session

**How to avoid:**
- Accept this as a limitation: active sessions use old schema until reconnection
- The server-side behavior is correct regardless (Literal validates even if client sends old values)
- If client sends no `mode` param, old schema's default was "replace" but server now defaults to "append" -- this is the desired behavior change
- Document in release notes: "Reconnect MCP clients after deployment"

**Warning signs:**
- Users report "my scratchpad got overwritten" in sessions started before deployment
- Test by connecting Claude, deploying the update, and calling write_file in the same session

**Phase to address:** Deployment planning -- accept the transient inconsistency, document it

---

### Pitfall 5: Test helper `_get_tool_fn` bypasses Pydantic validation

**What goes wrong:**
The test pattern `tool.fn` calls the raw function directly, bypassing FastMCP's `tool.run()` which does Pydantic validation. Tests using `_get_tool_fn` will NOT trigger Literal validation. This means:
- Tests pass with invalid mode values even after adding `Literal`
- No test coverage for the actual validation behavior
- False confidence that validation works

**Why it happens:**
- `_get_tool_fn` extracts `tool.fn` -- the unwrapped Python function
- `tool.run()` is the method that calls `type_adapter.validate_python(arguments)`
- Existing tests were written when there was no type validation to test
- The pattern was correct for testing business logic but not for validation

**How to avoid:**
1. Add NEW tests that call `tool.run()` (async) to verify Literal validation fires
2. Keep existing `tool.fn` tests for business logic (they test the function, not the framework)
3. New validation tests should verify: invalid mode raises error, valid modes work, default is "append"
4. Use `pytest.raises(ValidationError)` or check `ToolResult.is_error` depending on test level

**Warning signs:**
- "All tests pass" but deploying to production shows validation errors for the first time
- No test that explicitly sends `mode="banana"` and expects rejection

**Phase to address:** Parameter validation phase -- add validation-level tests alongside the Literal change

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip validation tests, rely on Pydantic | Fewer tests to write | False confidence, regressions invisible | Never -- add at least one validation test |
| Deploy both changes at once | Single deployment | Can't isolate behavioral regressions | Acceptable if UAT covers both, but risky |
| Duplicate validation (Literal + manual if/else) | Belt and suspenders | Dead code confusion, maintenance burden | Never -- Literal is sufficient |
| Hardcode mode values in test assertions | Quick to write | Breaks if enum expands later | Acceptable for now (only 2 values) |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| FastMCP Literal types | Adding manual validation inside the function that never fires | Trust Pydantic, test at the `tool.run()` level |
| Claude AI tool descriptions | Writing prose that reads well to humans but confuses the agent | Write descriptions as if programming the agent -- directive, structured, with explicit triggers |
| MCP schema caching | Assuming clients immediately see schema changes | Accept transient inconsistency, test cross-deployment sessions |
| Pydantic error messages | Trying to customize Pydantic's Literal error text | Accept the default -- it's clear enough for AI agents |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Removing the `else` fallback to replace without adding Literal | Invalid mode silently does nothing (no write) | Literal handles this, but verify with test |
| Description mentioning internal paths or storage details | Information leakage to agent/user | Keep descriptions abstract, no file paths |
| Trusting client-side enum validation | Client might not enforce enum | Server-side Literal validation is the source of truth |

## "Looks Done But Isn't" Checklist

- [ ] **Literal type added:** Verify JSON Schema output actually contains `"enum"` -- run schema dump test
- [ ] **Default changed:** Verify `"default": "append"` in JSON Schema, not just in Python signature
- [ ] **Tests updated:** Every `write_fn(content=...)` call without `mode=` is intentionally using the new default
- [ ] **Validation test exists:** At least one test sends invalid mode via `tool.run()` and expects error
- [ ] **Description updated:** Both `read_file` and `write_file` descriptions changed together
- [ ] **Args in docstring updated:** `mode` description in Args block reflects new default
- [ ] **UAT done:** Claude AI tested on live server with new descriptions, confirmed it reads/writes appropriately
- [ ] **No duplicate validation:** Function body has no manual mode checking (Literal handles it)

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Tests broken by default change | LOW | Add explicit `mode="replace"` to affected tests |
| Agent over-refuses writes | LOW | Soften description, redeploy. No data loss |
| Agent under-uses scratchpad | LOW | Strengthen "read at session start" instruction |
| Cached schema inconsistency | NONE | Self-resolves on next client reconnect |
| Validation bypassed in tests | LOW | Add `tool.run()` level tests, takes 30 min |
| Duplicate validation in function | LOW | Remove manual check, trust Literal |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Default change breaks tests | Phase 1: Parameter validation | `just test` passes, diff shows explicit `mode=` in affected tests |
| Pydantic error leaks | Phase 1: Parameter validation | Manual test with invalid mode, confirm error is acceptable |
| Docstring behavioral regression | Phase 2: Description update | Manual UAT with Claude AI on live server |
| Schema caching stale | Phase 2: Deployment | Reconnect client after deploy, verify new schema |
| Test helper bypasses validation | Phase 1: Parameter validation | New test file or section using `tool.run()` |

## Sources

- FastMCP 3.1.0 source: `fastmcp/tools/function_tool.py` -- `type_adapter.validate_python()` on line 256 confirms Pydantic validates before function call
- FastMCP 3.1.0 source: `fastmcp/tools/function_parsing.py` -- `get_cached_typeadapter()` generates JSON Schema from type hints including Literal
- Runtime verification: `Literal["replace", "append"]` produces `{"enum": ["replace", "append"]}` in JSON Schema (tested locally)
- Runtime verification: Invalid Literal value raises Pydantic `ValidationError`, FastMCP converts to `ToolError` with `isError=true`
- Existing test code: `tests/test_user_isolation.py` and `tests/test_storage_limits.py` -- all use `tool.fn` pattern bypassing validation
- Project TODO: `.planning/todos/pending/2026-03-07-validate-write-file-mode-parameter.md` -- problem statement and solution outline
- Project TODO: `.planning/todos/pending/2026-03-18-update-tool-descriptions-to-inter-agent-persistence-framing.md` -- draft descriptions

---
*Pitfalls research for: MCP tool API hardening (parameter validation + description changes)*
*Researched: 2026-03-18*
