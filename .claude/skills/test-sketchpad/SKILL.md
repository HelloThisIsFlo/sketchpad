---
name: test-sketchpad
description: Test the Sketchpad MCP server integration by walking through read, write, and read-back operations
---

# Test Sketchpad Integration

Walk through each test step interactively, reporting what happens at each step.

## Steps

1. **Read current content**: Call the `read_file` tool from the Sketchpad server. Report what you see (the current content or a welcome message if empty).

2. **Write new content**: Call `write_file` with test content that includes a timestamp (e.g., "Test from Claude Code at [current time]"). Report the result.

3. **Read back**: Call `read_file` again. Verify the content matches what was written in step 2.

4. **Report**: Summarize the results:
   - Did read_file work? (Step 1)
   - Did write_file work? (Step 2)
   - Did read-back match? (Step 3)
   - Overall: PASS or FAIL
