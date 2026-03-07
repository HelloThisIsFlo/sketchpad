---
created: "2026-03-07T20:34:43.761Z"
title: Validate write_file mode parameter
area: api
files:
  - src/sketchpad/tools.py:47-99
---

## Problem

The `write_file` tool's `mode` parameter accepts any string without validation. Invalid values (e.g., `mode="banana"`) silently fall through to the `else` branch and behave like `"replace"`, because the logic is `if mode == "append" ... else ...`. The response even echoes back the invalid mode: `"File updated (banana mode)."`.

Additionally, the default should be changed from `"replace"` to `"append"` — appending is the safer default (won't accidentally overwrite content).

## Solution

- Validate `mode` against allowed values (`"replace"`, `"append"`) and return an error for anything else
- Change the default from `mode: str = "replace"` to `mode: str = "append"`
- Consider using `Literal["replace", "append"]` type annotation so FastMCP can validate before the function runs
