---
created: "2026-03-18T15:13:37.727Z"
title: Update tool descriptions to inter-agent persistence framing
area: api
files:
  - src/sketchpad/tools.py:1-55
---

## Problem

Current `read_file` and `write_file` docstrings frame Sketchpad as a user-facing notepad ("Use this for notes, drafts, ideas"). This causes AI agents (especially Claude on claude.ai) to treat Sketchpad as a place to save content **for the user to read** — like a clipboard. The user doesn't read Sketchpad directly; the content is for agents to consume.

Consequences:
- Agents dump user-facing content here instead of using artifacts/files
- Inter-agent context gets overwritten or buried
- Agents say "I've saved it to your Sketchpad" for content the user expected as a downloadable file
- Defeats the purpose of cross-session persistence for agents

## Solution

Replace both tool docstrings with descriptions that encode:
1. Sketchpad is an **inter-agent persistence layer**, not a user-facing notepad
2. Write when future agent sessions need context (project state, decisions, WIP)
3. Write when user explicitly asks
4. Do NOT write to save content for user to read (use artifacts/files)
5. Do NOT write unprompted for every conversation
6. Read at task start if previous session context might be relevant

Draft descriptions are ready — see brief below.

### Draft `read_file` description

```
Read the shared agent scratchpad. This is an inter-agent persistence layer
shared across all AI agents (Claude, Cursor, etc.) on the same GitHub identity.
Use this to check for working context left by a previous agent session —
project state, decisions made, tasks in progress, or notes the user explicitly
asked to be saved here. This is NOT a user-facing notepad; the user reads
artifacts and files, not this scratchpad.
```

### Draft `write_file` description

```
Write to the shared agent scratchpad. This is an inter-agent persistence layer,
NOT a user-facing notepad.

Write here when:
- You need a future agent session to pick up context (project state, decisions,
  work in progress)
- The user explicitly asks you to write something to the scratchpad

Do NOT write here to:
- Save content for the user to read (use artifacts or files instead)
- Store every conversation (only persist genuinely useful cross-session context)

Markdown formatting recommended. Shared across all AI agents on the same
GitHub identity.

Args:
    content: The text to write.
    mode: 'replace' (default) overwrites the file; 'append' adds to the end.
```
