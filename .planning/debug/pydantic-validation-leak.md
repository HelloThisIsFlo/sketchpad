---
status: resolved
trigger: "Investigate how Pydantic validation errors are surfaced to MCP clients when write_file is called with an invalid mode value"
created: 2026-03-20T00:00:00Z
updated: 2026-03-20T00:00:00Z
---

## Current Focus

hypothesis: Pydantic ValidationError's str() representation is sent verbatim to MCP clients via two catch-all exception handlers
test: Traced full call chain from tool invocation through wire response
expecting: Confirm exact error message format reaching client
next_action: Return diagnosis

## Symptoms

expected: Clean, user-friendly error message when invalid mode value is provided
actual: Error message includes Pydantic internals (type=literal_error, input_value, input_type, pydantic.dev URL)
errors: "1 validation error for call[write_file]\nmode\n  Input should be 'replace' or 'append' [type=literal_error, input_value='banana', input_type=str]\n    For further information visit https://errors.pydantic.dev/2.12/v/literal_error"
reproduction: Call write_file with mode="banana"
started: Since Literal type was added (phase 08-01)

## Eliminated

(none needed -- root cause found on first hypothesis)

## Evidence

- timestamp: 2026-03-20T00:01:00Z
  checked: FunctionTool.run() in fastmcp/tools/function_tool.py:253-296
  found: Pydantic TypeAdapter.validate_python() is called with the arguments dict. For invalid Literal values, this raises pydantic_core.ValidationError BEFORE the function body executes. No try/except around it in run().
  implication: The ValidationError propagates up uncaught from FunctionTool.run()

- timestamp: 2026-03-20T00:02:00Z
  checked: FastMCP server.call_tool() in fastmcp/server/server.py:986-993
  found: |
    Lines 991-993:
    ```
    except (ValidationError, PydanticValidationError):
        logger.exception(f"Error validating tool {name!r}")
        raise
    ```
    PydanticValidationError is re-raised without transformation.
  implication: FastMCP intentionally lets validation errors propagate unchanged

- timestamp: 2026-03-20T00:03:00Z
  checked: MCP SDK call_tool handler in mcp/server/lowlevel/server.py:521-584
  found: |
    Line 583-584:
    ```
    except Exception as e:
        return self._make_error_result(str(e))
    ```
    The catch-all calls str(e) on the PydanticValidationError and wraps it in CallToolResult(isError=True).
  implication: str(PydanticValidationError) includes all Pydantic internals -- this is what reaches the client

- timestamp: 2026-03-20T00:04:00Z
  checked: _make_error_result in mcp/server/lowlevel/server.py:467-474
  found: Creates CallToolResult with isError=True and TextContent containing the raw error string
  implication: No sanitization layer exists between exception and wire response

- timestamp: 2026-03-20T00:05:00Z
  checked: Actual str(PydanticValidationError) output for mode="banana"
  found: |
    "1 validation error for call[write_file]
    mode
      Input should be 'replace' or 'append' [type=literal_error, input_value='banana', input_type=str]
        For further information visit https://errors.pydantic.dev/2.12/v/literal_error"
  implication: Client sees internal function name, error type codes, input type metadata, and pydantic.dev URL

- timestamp: 2026-03-20T00:06:00Z
  checked: strict_input_validation setting
  found: Default is False. When False, the MCP SDK skips JSON Schema validation at lines 528-532. When True, jsonschema.validate() would catch the invalid enum value FIRST and return a cleaner "Input validation error: ..." message.
  implication: Even with strict_input_validation=True, the JSON Schema layer would only add a first line of defense -- Pydantic validation still runs after and could still leak on edge cases

## Resolution

root_cause: |
  Two-layer pass-through with no sanitization:

  1. FastMCP server.call_tool() (line 991-993) catches PydanticValidationError but immediately re-raises it
  2. MCP SDK call_tool handler (line 583-584) catches the re-raised exception via `except Exception as e` and calls `str(e)` to build the error response

  `str(PydanticValidationError)` produces a multi-line string containing:
  - Internal function name: "call[write_file]"
  - Error type code: "type=literal_error"
  - Raw input details: "input_value='banana', input_type=str"
  - Pydantic docs URL: "https://errors.pydantic.dev/2.12/v/literal_error"

  The useful part ("Input should be 'replace' or 'append'") is buried in this noise.

fix: Discarded — accepted as framework behavior (FastMCP/MCP SDK responsibility, not worth wrapping)
verification: N/A
files_changed: []
