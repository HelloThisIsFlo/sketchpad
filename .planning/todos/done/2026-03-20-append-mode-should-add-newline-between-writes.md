---
created: "2026-03-20T17:02:00.049Z"
title: Append mode should add newline between writes
area: api
files:
  - src/sketchpad/tools.py
---

## Problem

When `write_file` is called in append mode (now the default), content is concatenated directly without any separator. Writing "hello" then " world" produces "hello world", but writing "first entry" then "second entry" produces "first entrysecond entry" with no newline between them.

For a persistence layer used by AI agents, each write is typically a discrete chunk of information. Appending without a newline makes the file harder to parse and loses the boundary between entries.

## Solution

Add a newline before appended content in `write_file` when mode is "append" — if the file already has content and doesn't end with a newline, prepend one. Quick change in `tools.py`.
