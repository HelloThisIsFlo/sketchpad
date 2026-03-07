---
created: "2026-03-05T18:29:55.922Z"
title: Per-user sketchpad segregation
area: auth
files:
  - src/sketchpad/server.py
  - src/sketchpad/tools.py
---

## Problem

Currently all authenticated users share the same single sketchpad file. Any user who completes the OAuth flow can read and write the same content. This is fine for personal use but prevents sharing the server URL with friends — everyone would overwrite each other's sketchpad.

## Solution

Segregate sketchpad storage by authenticated username (from the OAuth token). Each user gets their own file (e.g., `/data/{username}.md`). The `read_file` and `write_file` tools already receive auth context — route to a per-user path instead of a shared one. Should be a small change in the tools layer.

Target: next milestone (not v1.0).
