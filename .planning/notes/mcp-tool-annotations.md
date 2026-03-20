# MCP Tool Annotations

Spotted during Phase 9 UAT, implemented in `670ac05`.

## What was done

Added `annotations` dict to both `@mcp.tool` decorators in `tools.py`:

| Tool | readOnly | destructive | idempotent | openWorld |
|------|----------|-------------|------------|-----------|
| read_file | True | False | True | False |
| write_file | False | True | False | False |

## Why

MCP clients use these hints for UX decisions (e.g., ChatGPT skips confirmation for read-only tools). Without explicit annotations, defaults are conservative and incorrect (everything shows as destructive, open-world).

## API

FastMCP supports annotations via `@mcp.tool(annotations={...})` dict or `ToolAnnotations` object from `mcp.types`.
