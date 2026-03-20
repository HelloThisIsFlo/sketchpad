# Phase 9: Description Update - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Reframe `read_file` and `write_file` tool descriptions so AI agents understand the Sketchpad as a shared persistence layer, not a user-facing notepad. Add `Field(description=...)` annotations for parameters. Also fix append mode to insert a newline separator between writes (folded from pending todo).

</domain>

<decisions>
## Implementation Decisions

### Description Tone
- **D-01:** Use explicit "Do / Do NOT" guardrails in `write_file` description — agents need firm boundaries or they dump everything here
- **D-02:** Do NOT mention storage limits in descriptions — if agents hit the limit, the description itself is the problem

### Naming
- **D-03:** Use "Sketchpad" (capitalized, proper noun) in all descriptions — matches project name, server name, tool names
- **D-04:** Drop "scratchpad" from the draft todo — replace all instances with "Sketchpad"

### Newline Separator (Folded Todo)
- **D-05:** Append mode always prepends a single `\n` before new content — simple, predictable
- **D-06:** Mention newline behavior briefly in the `mode` parameter description

### Read/Write Agency
- **D-07:** `read_file` description: explain WHAT the Sketchpad contains + explicitly state "read when the user asks you to check for prior context"
- **D-08:** `write_file` description: write ONLY when user explicitly asks — no proactive agent writes
- **D-09:** Remove "future agent session needs context" as a write trigger from the draft — user controls all persistence

### Claude's Discretion
- Exact wording of Field(description=...) for `content` and `mode` parameters
- Final sentence-level polish of docstrings
- Whether to use bullet lists or prose in the docstring body

### Folded Todos
- **Append mode should add newline between writes** (`2026-03-20-append-mode-should-add-newline-between-writes.md`) — prepend `\n` before appended content. Folded because it directly affects what the description says about append behavior.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Tool implementation
- `src/sketchpad/tools.py` — Current tool definitions with docstrings and parameter signatures (lines 34-100)

### Draft descriptions
- `.planning/todos/pending/2026-03-18-update-tool-descriptions-to-inter-agent-persistence-framing.md` — Original draft descriptions (needs revision per decisions D-03, D-04, D-07, D-08, D-09)

### Newline behavior
- `.planning/todos/pending/2026-03-20-append-mode-should-add-newline-between-writes.md` — Problem statement and solution sketch for newline separator

### Requirements
- `.planning/REQUIREMENTS.md` — DESC-01, DESC-02, DESC-03 define the acceptance criteria
- `.planning/REQUIREMENTS.md` §Out of Scope table — ToolAnnotations, outputSchema, examples, Enum class are explicitly excluded

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Literal["replace", "append"]` type annotation already in place on `mode` parameter (Phase 8)
- `_get_user_sketchpad_path()` helper handles auth + path resolution

### Established Patterns
- Tools registered via `@mcp.tool` decorator in `register_tools(mcp)` function
- Docstrings serve as both Python docs and MCP tool descriptions (FastMCP extracts them)
- No `Field()` annotations currently — parameters use plain type hints with defaults
- Args section in docstring provides parameter docs (FastMCP may or may not extract these)

### Integration Points
- `write_file` append logic at line 88-94 — newline separator goes here
- FastMCP's `tools/list` JSON schema generation — `Field(description=...)` annotations will surface in the schema

</code_context>

<specifics>
## Specific Ideas

- User wants full agency control: agents should never proactively read or write the Sketchpad. User initiates all interactions.
- This is a significant departure from the draft todo, which framed the Sketchpad as something agents should autonomously use for cross-session persistence.
- The "Do NOT write here to save content for the user to read" guardrail stays — that's about misuse, not agency.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-description-update*
*Context gathered: 2026-03-20*
