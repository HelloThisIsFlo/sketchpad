---
status: complete
phase: 05-per-user-storage-isolation
source: [05-01-SUMMARY.md, 05-02-SUMMARY.md]
started: 2026-03-06T19:00:00Z
updated: 2026-03-06T19:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. End-to-End OAuth + Tool Test
expected: Start the MCP server and tunnel. Run `uv run python test_oauth.py`. All checks pass -- discovery, auth, token exchange, read_file returns content, write_file succeeds, read-back matches written content.
result: pass

### 2. Per-User Directory on Disk
expected: After test_oauth.py writes "Hello from test_oauth.py!", check the data/ directory. The file should be at data/github/<your-lowercase-github-username>/sketchpad.md -- proving per-user isolation is working at the filesystem level.
result: pass

### 3. Welcome Message for Fresh User
expected: A new user reading their sketchpad for the first time gets a welcome message. Verified via test_oauth.py read_file call returning "Welcome to Sketchpad! Write something here." before any writes.
result: pass

### 4. No Username in Tool Schema
expected: In the test_oauth.py output for tools/list, read_file has zero input parameters. write_file has only content and mode. No username or identity field visible.
result: pass

### 5. Connect from Claude
expected: Add the server as a remote MCP integration on claude.ai. Connect via tunnel URL. Claude shows read_file and write_file tools. Write and read back content through Claude's UI.
result: pass

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
