# Phase 6: Storage Limits - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Write operations are bounded by configurable per-user and global size limits. Both limits are enforced before content touches disk. Configurable via environment variables without code changes.

</domain>

<decisions>
## Implementation Decisions

### Per-user limit scope
- Check the **resulting file size** after the write (not just the incoming content)
- For `replace` mode: size of new content
- For `append` mode: existing file size + new content size
- Check happens **before writing to disk** — content never touches disk if it would exceed the limit
- Both per-user and global checks run on every write, per-user first (fail fast)

### Error messages
- User-friendly, no raw numbers — e.g., "Sketchpad too large. Try reducing the size of your sketchpad."
- Global limit uses same tone but different cause — e.g., "Server storage full. Try again later or reduce your sketchpad size."
- Not a security boundary (unlike path traversal) — guidance is helpful, not evasive

### Logging
- Log size limit rejections at WARNING level (same as path traversal)
- Hitting the limit is unusual for a sketchpad — may indicate misuse, worth monitoring

### Existing SIZE_LIMIT cleanup
- Remove the read-time soft warning in `read_file` (lines 36-38 in tools.py) — hard write limit makes it redundant
- Remove the `SIZE_LIMIT` config key entirely
- Replace with `MAX_STORAGE_USER` env var (new, clear naming)

### Default limit values
- Per-user: **20KB** (`MAX_STORAGE_USER=20000`) — ~5,000 tokens, context-window-friendly for a sketchpad
- Global: **50MB** (`MAX_STORAGE_GLOBAL=52428800`) — protects PVC, allows ~2,500 users at max
- Design rationale: sketchpad is for transient ideas, not long-term storage. 20KB is generous for notes but won't eat the context window when read

### Environment variable naming
- `MAX_STORAGE_USER` — per-user limit in bytes
- `MAX_STORAGE_GLOBAL` — global limit in bytes
- Prefix `MAX_STORAGE_` aligns visually for easy comparison in env files

### Claude's Discretion
- Global size calculation method (walk data dir vs cache vs other approach)
- Internal code structure for limit checking (separate module vs inline in tools.py)
- Exact error message wording (within the user-friendly, no-numbers framing)

</decisions>

<specifics>
## Specific Ideas

- "Sketchpad is what it is — it's temporary, to not forget to pass ideas." The 20KB limit reflects this philosophy.
- User's current sketchpad is ~10KB and feels "very, very long" — 20KB is 2x that, generous enough.
- Future: multiple named sketchpads per user. The per-user limit should work as total user storage, not per-file. (Not in scope for this phase, but informs the limit design.)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `config.py:get_config()`: Add `MAX_STORAGE_USER` and `MAX_STORAGE_GLOBAL` env vars, remove `SIZE_LIMIT`
- `user_identity.py:resolve_user_dir()`: Already resolves per-user directory — reuse for per-user size calculation
- `tools.py:_get_user_sketchpad_path()`: Returns the exact file path — use for size check

### Established Patterns
- Environment-based config via `get_config()` with `@lru_cache` — new limits follow same pattern
- Defensive assertions for internal errors (Phase 5) — size limit is a user-facing rejection, not assertion
- WARNING-level logging for suspicious activity (path traversal) — reuse for size limit hits

### Integration Points
- `tools.py:write_file()` (line 43): Add size checks before the write logic
- `tools.py:read_file()` (lines 36-38): Remove the soft warning block
- `config.py` (line 20): Replace `SIZE_LIMIT` with `MAX_STORAGE_USER` and `MAX_STORAGE_GLOBAL`
- `.env.example`: Update with new env var names and defaults

</code_context>

<deferred>
## Deferred Ideas

- Multiple named sketchpads per user — future phase, but per-user limit is designed as total user storage to accommodate this
- Per-file size limits (when multiple files exist) — not needed until multi-file support

</deferred>

---

*Phase: 06-storage-limits*
*Context gathered: 2026-03-06*
