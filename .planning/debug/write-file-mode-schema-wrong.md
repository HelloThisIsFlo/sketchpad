---
status: resolved
trigger: "Investigate why the MCP tools/list schema for write_file shows mode as string with default replace instead of enum with default append"
created: 2026-03-20T17:05:00Z
updated: 2026-03-20T17:15:00Z
---

## Current Focus

hypothesis: Deployed Docker image was built from an older commit (pre-81e7c61) where mode was `str = "replace"`, not `Literal["replace", "append"] = "append"`
test: Compare git history of tools.py — original vs current signature
expecting: Original commit has `mode: str = "replace"`
next_action: Return diagnosis

## Symptoms

expected: MCP `tools/list` returns mode with `enum: ["replace", "append"]` and `default: "append"`
actual: MCP client sees mode as plain `string` type with `default: "replace"`
errors: No runtime errors — schema is structurally valid but missing constraints
reproduction: Call `tools/list` on the deployed server via any MCP client
started: After commit 81e7c61 changed the parameter but before a new Docker image was built/deployed

## Eliminated

- hypothesis: FastMCP doesn't support Literal -> enum schema generation
  evidence: FastMCP 3.1.0 correctly generates enum from Literal (tested locally — Pydantic TypeAdapter produces correct JSON schema)
  timestamp: 2026-03-20T17:08:00Z

- hypothesis: compress_schema strips enum fields
  evidence: compress_schema preserves enum — tested with ParsedFunction.from_function() on same signature, output includes enum
  timestamp: 2026-03-20T17:09:00Z

- hypothesis: Wire serialization (to_mcp_tool / model_dump) loses enum
  evidence: Tested full pipeline: tool.parameters -> to_mcp_tool() -> model_dump() — enum preserved at every stage
  timestamp: 2026-03-20T17:10:00Z

- hypothesis: Schema caching layer serves stale data
  evidence: No schema caching exists in the pipeline. tool.parameters is set at registration time (in-memory), inputSchema is a plain dict passthrough in mcp.types.Tool
  timestamp: 2026-03-20T17:11:00Z

- hypothesis: Difference between tool.parameters (Python) and wire protocol schema
  evidence: They are identical. MCPTool.inputSchema = self.parameters (line 195 of tool.py). model_dump() doesn't transform dict[str, Any] fields.
  timestamp: 2026-03-20T17:12:00Z

## Evidence

- timestamp: 2026-03-20T17:07:00Z
  checked: FastMCP version
  found: 3.1.0 installed locally, 3.1.0 pinned in uv.lock
  implication: Version supports Literal -> enum correctly

- timestamp: 2026-03-20T17:08:00Z
  checked: ParsedFunction.from_function() output for write_file signature
  found: Produces `{"enum": ["replace", "append"], "type": "string", "default": "append"}` — correct
  implication: Schema generation pipeline works correctly in current code

- timestamp: 2026-03-20T17:09:00Z
  checked: Full pipeline test (tool.parameters -> to_mcp_tool -> model_dump)
  found: enum and default preserved identically at every stage
  implication: No schema transformation or loss in the FastMCP/MCP SDK serialization path

- timestamp: 2026-03-20T17:10:00Z
  checked: Git history of src/sketchpad/tools.py
  found: Commit 82cdfb2 (original) had `mode: str = "replace"`. Commit 81e7c61 changed it to `mode: Literal["replace", "append"] = "append"`.
  implication: The deployed server symptom (`string` type, `"replace"` default) exactly matches the OLD code, not the current code

- timestamp: 2026-03-20T17:11:00Z
  checked: Dockerfile build process
  found: Two-stage build with `uv sync --locked`. Uses `COPY . /app` to get source. The CMD is `python -m sketchpad`.
  implication: Docker image is self-contained. If built from old commit, it has old code. No hot-reload mechanism.

- timestamp: 2026-03-20T17:13:00Z
  checked: Both anomalies together (wrong type AND wrong default)
  found: The wrong default ("replace" instead of "append") is the smoking gun. No serialization bug could change the default value. Only running older code produces both symptoms simultaneously.
  implication: Root cause is deployment, not code

## Resolution

root_cause: The deployed Docker image was built from a commit prior to 81e7c61, which still had the original `mode: str = "replace"` signature. The current code (with `Literal["replace", "append"] = "append"`) has never been deployed. This is a stale deployment, not a serialization bug.
fix: Rebuilt and redeployed Docker image from current HEAD (done manually by user)
verification: Confirmed tools/list returns correct enum and default
files_changed: []
