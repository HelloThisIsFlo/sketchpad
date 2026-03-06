# Phase 6: Storage Limits - Research

**Researched:** 2026-03-06
**Domain:** Python file I/O, size enforcement, configuration management
**Confidence:** HIGH

## Summary

Phase 6 adds per-user and global size limits to the `write_file` tool. The scope is narrow: two size checks before any write touches disk, removal of the legacy `SIZE_LIMIT` config key and soft warning, and two new environment variables. No external libraries are needed -- Python's `pathlib` and `os` provide everything required.

The existing codebase is well-structured for this change. `config.py` already follows an env-var-with-defaults pattern (just add two keys, remove one). `tools.py:write_file()` is the single integration point where checks are added. The `user_identity.py:resolve_user_dir()` function already resolves the per-user directory path, which is reused for per-user size calculation.

**Primary recommendation:** Add size checks inline in `tools.py:write_file()` before the write logic. Use a helper function for global size calculation via `Path.rglob('*')`. Keep it simple -- no separate module, no caching.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Per-user limit checks **resulting file size** (not just incoming content): replace mode = new content size, append mode = existing + new content size
- Both per-user and global checks run on every write, **per-user first** (fail fast)
- Check happens **before writing to disk** -- content never touches disk if it would exceed the limit
- Error messages are **user-friendly, no raw numbers** -- e.g., "Sketchpad too large." / "Server storage full."
- Log size limit rejections at **WARNING** level (same as path traversal)
- **Remove** the read-time soft warning in `read_file` (lines 36-38 in tools.py) and the `SIZE_LIMIT` config key entirely
- New env vars: `MAX_STORAGE_USER` (default 20000 bytes = 20KB) and `MAX_STORAGE_GLOBAL` (default 52428800 bytes = 50MB)
- Per-user limit is designed as **total user storage** (not per-file) to accommodate future multi-file support

### Claude's Discretion
- Global size calculation method (walk data dir vs cache vs other approach)
- Internal code structure for limit checking (separate module vs inline in tools.py)
- Exact error message wording (within the user-friendly, no-numbers framing)

### Deferred Ideas (OUT OF SCOPE)
- Multiple named sketchpads per user -- future phase
- Per-file size limits (when multiple files exist) -- not needed until multi-file support

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| STOR-01 | `write_file` rejects content exceeding a configurable per-user size limit (env var) | Per-user check: calculate resulting file size before write, compare against `MAX_STORAGE_USER`. Reject with user-friendly message. Config via `get_config()` pattern. |
| STOR-02 | `write_file` rejects writes when total data directory exceeds a configurable global size limit (env var) | Global check: walk `DATA_DIR` with `Path.rglob('*')`, sum file sizes, compare against `MAX_STORAGE_GLOBAL`. Reject with user-friendly message. |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pathlib (stdlib) | Python 3.12+ | File path operations, `rglob` for directory walk | Already used throughout codebase |
| os (stdlib) | Python 3.12+ | Environment variable access | Already used in `config.py` |
| logging (stdlib) | Python 3.12+ | WARNING-level logging for rejections | Already used in `user_identity.py` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=8.0 | Testing | Already in dev dependencies |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `Path.rglob('*')` for global size | `os.scandir()` recursive | Faster for huge directories but more code; `rglob` is fine for <2,500 user dirs |
| Walk-on-every-write | Cached global size | Premature optimization; adds stale-cache complexity for negligible gain at this scale |
| Separate `storage_limits.py` module | Inline in `tools.py` | Module adds a file but no real benefit for ~20 lines of logic |

## Architecture Patterns

### Recommended Approach: Inline in tools.py

The size check logic is small (~20 lines) and tightly coupled to `write_file`. Keep it in `tools.py` with a module-level helper for directory size calculation.

### Pattern 1: Pre-write Size Validation

**What:** Calculate the would-be size before touching disk, reject if over limit.
**When to use:** Every `write_file` call.
**Example:**

```python
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def _calculate_dir_size(directory: Path) -> int:
    """Sum of all file sizes in a directory tree."""
    return sum(f.stat().st_size for f in directory.rglob('*') if f.is_file())

def write_file(content: str, mode: str = "replace") -> str:
    sketchpad_path = _get_user_sketchpad_path()
    cfg = get_config()

    # --- Per-user limit (STOR-01) ---
    if mode == "append":
        existing_size = sketchpad_path.stat().st_size if sketchpad_path.exists() else 0
        resulting_size = existing_size + len(content.encode("utf-8"))
    else:
        resulting_size = len(content.encode("utf-8"))

    if resulting_size > cfg["MAX_STORAGE_USER"]:
        logger.warning("Per-user storage limit exceeded: %d bytes", resulting_size)
        return "Sketchpad too large. Try reducing the size of your sketchpad."

    # --- Global limit (STOR-02) ---
    data_dir = Path(cfg["DATA_DIR"]).resolve()
    global_size = _calculate_dir_size(data_dir)
    # For replace mode, subtract current file size (it will be overwritten)
    current_file_size = sketchpad_path.stat().st_size if sketchpad_path.exists() else 0
    net_addition = resulting_size - current_file_size
    if global_size + net_addition > cfg["MAX_STORAGE_GLOBAL"]:
        logger.warning("Global storage limit exceeded: %d bytes", global_size + net_addition)
        return "Server storage full. Try again later or reduce your sketchpad size."

    # ... proceed with actual write ...
```

### Pattern 2: Return Error String (Not Exception)

**What:** Size limit violations return a user-friendly error string, not raise an exception.
**When to use:** This is a user-facing rejection, not an internal error. The tool returns a message the LLM can relay.
**Rationale:** MCP tools communicate results via return values. Exceptions would be caught by FastMCP and turned into error responses with stack traces -- not appropriate for a user-facing "your file is too big" message.

### Pattern 3: Config via get_config() with @lru_cache

**What:** New env vars follow the existing `get_config()` pattern with defaults.
**Example:**

```python
cfg = {
    # ... existing keys ...
    "MAX_STORAGE_USER": int(os.environ.get("MAX_STORAGE_USER", "20000")),
    "MAX_STORAGE_GLOBAL": int(os.environ.get("MAX_STORAGE_GLOBAL", "52428800")),
}
# Remove SIZE_LIMIT entirely
```

### Anti-Patterns to Avoid
- **Raising ValueError/RuntimeError for size limits:** These are not programming errors. Return a helpful string message instead.
- **Writing to disk then checking size after:** Content must never touch disk if it would exceed the limit.
- **Checking only incoming content size (ignoring existing file):** In append mode, the limit applies to the resulting file, not just the appended chunk.
- **Caching global directory size:** Adds stale-cache bugs for negligible performance gain. Walk fresh on each write.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Directory size calculation | Manual `os.walk` + stat loop | `Path.rglob('*')` + `stat().st_size` comprehension | Cleaner, already used in codebase, handles nested dirs |
| Byte length of string | `len(content)` | `len(content.encode("utf-8"))` | Strings have character length; files store bytes. Multi-byte chars (emoji, CJK) would silently bypass limits |

**Key insight:** The only gotcha in this entire phase is `len(content)` vs `len(content.encode("utf-8"))`. Everything else is straightforward.

## Common Pitfalls

### Pitfall 1: Character Count vs Byte Count
**What goes wrong:** `len(content)` returns character count, not byte count. A string with emoji or non-ASCII characters takes more bytes on disk than characters in the string.
**Why it happens:** Python strings are Unicode; `len()` counts code points.
**How to avoid:** Always use `len(content.encode("utf-8"))` for size comparisons against byte limits.
**Warning signs:** Tests with ASCII-only content pass but limits are bypassed with emoji/CJK content.

### Pitfall 2: Global Size Doesn't Account for File Replacement
**What goes wrong:** In replace mode, the global size check counts the old file's bytes. If the old file is 10KB and the new file is 10KB, the check sees 20KB of impact.
**Why it happens:** The global walk includes the current file that's about to be overwritten.
**How to avoid:** Calculate net addition: `resulting_size - current_file_size`. Only the net increase matters for global capacity.
**Warning signs:** Replace operations fail the global limit even when the file isn't growing.

### Pitfall 3: Forgetting to Remove SIZE_LIMIT from Test Mocks
**What goes wrong:** Existing test helper `_mock_config()` includes `"SIZE_LIMIT": 50000`. After removing `SIZE_LIMIT` from real config, tests still reference it. Tests pass but don't reflect reality.
**Why it happens:** Test mock dicts are maintained separately from `get_config()`.
**How to avoid:** Update `_mock_config()` to replace `SIZE_LIMIT` with `MAX_STORAGE_USER` and `MAX_STORAGE_GLOBAL`.
**Warning signs:** Tests pass with old config shape but production code uses new shape.

### Pitfall 4: Race Condition on Global Size (Acceptable)
**What goes wrong:** Two concurrent writes could both pass the global check, then both write, exceeding the limit.
**Why it happens:** No locking between size check and write.
**How to avoid:** Accept it. This is a sketchpad app with low write volume. The global limit protects against runaway growth, not byte-exact accounting. A transient overshoot by one write is harmless.
**Warning signs:** N/A -- this is a known acceptable tradeoff, not a bug.

## Code Examples

### Existing Code to Modify

**config.py line 20 -- replace SIZE_LIMIT:**
```python
# REMOVE this line:
"SIZE_LIMIT": int(os.environ.get("SIZE_LIMIT", "50000")),

# ADD these lines:
"MAX_STORAGE_USER": int(os.environ.get("MAX_STORAGE_USER", "20000")),
"MAX_STORAGE_GLOBAL": int(os.environ.get("MAX_STORAGE_GLOBAL", "52428800")),
```

**tools.py lines 36-38 -- remove soft warning in read_file:**
```python
# REMOVE this block:
cfg = get_config()
if len(content) > cfg["SIZE_LIMIT"]:
    content += "\n\n---\n[WARNING: File exceeds recommended size limit (~50KB). Consider trimming older content.]"
```

**.env.example -- update env var documentation:**
```bash
# REMOVE:
# Soft size limit in bytes (default: 50000 ~50KB)
# SIZE_LIMIT=50000

# ADD:
# Per-user storage limit in bytes (default: 20000 = 20KB)
# MAX_STORAGE_USER=20000

# Global storage limit in bytes (default: 52428800 = 50MB)
# MAX_STORAGE_GLOBAL=52428800
```

**tests/test_user_isolation.py -- update _mock_config:**
```python
def _mock_config(tmp_data_dir):
    return {
        "DATA_DIR": str(tmp_data_dir),
        "OAUTH_PROVIDER": "github",
        "SKETCHPAD_FILENAME": "sketchpad.md",
        "MAX_STORAGE_USER": 20000,
        "MAX_STORAGE_GLOBAL": 52428800,
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Soft read-time warning (`SIZE_LIMIT`) | Hard write-time rejection (`MAX_STORAGE_USER`) | This phase | Prevents oversized content from ever being written |
| No global limit | `MAX_STORAGE_GLOBAL` protects PVC | This phase | Prevents runaway disk usage on shared storage |

**Deprecated/outdated:**
- `SIZE_LIMIT` config key: Replaced by `MAX_STORAGE_USER`. Remove entirely, including from `.env.example`.

## Open Questions

1. **Should `_calculate_dir_size` follow symlinks?**
   - What we know: `Path.rglob('*')` + `is_file()` follows symlinks by default. The data dir should not contain symlinks.
   - What's unclear: Whether the NAS/NFS mount could introduce unexpected symlinks.
   - Recommendation: Use `is_file(follow_symlinks=False)` to avoid counting external files. Minimal cost, defensive.

2. **Should the global size include the `state/` directory?**
   - What we know: `DATA_DIR` and `STATE_DIR` are separate. The user decision says "total data directory".
   - What's unclear: Whether `STATE_DIR` (OAuth tokens, encrypted blobs) should count.
   - Recommendation: Only walk `DATA_DIR`. State is infrastructure, not user content. The decision says "data directory" explicitly.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STOR-01a | Replace mode: content exceeding per-user limit is rejected | unit | `pytest tests/test_storage_limits.py::test_replace_exceeds_user_limit -x` | Wave 0 |
| STOR-01b | Append mode: existing + new exceeding per-user limit is rejected | unit | `pytest tests/test_storage_limits.py::test_append_exceeds_user_limit -x` | Wave 0 |
| STOR-01c | Content at exactly the limit is accepted | unit | `pytest tests/test_storage_limits.py::test_at_user_limit_accepted -x` | Wave 0 |
| STOR-01d | Error message is user-friendly (no raw numbers) | unit | `pytest tests/test_storage_limits.py::test_user_limit_error_message -x` | Wave 0 |
| STOR-01e | Rejection logged at WARNING level | unit | `pytest tests/test_storage_limits.py::test_user_limit_logged_warning -x` | Wave 0 |
| STOR-02a | Write rejected when global limit would be exceeded | unit | `pytest tests/test_storage_limits.py::test_global_limit_exceeded -x` | Wave 0 |
| STOR-02b | Replace mode accounts for file being overwritten (net addition) | unit | `pytest tests/test_storage_limits.py::test_global_limit_replace_net_addition -x` | Wave 0 |
| STOR-02c | Global limit error message is user-friendly | unit | `pytest tests/test_storage_limits.py::test_global_limit_error_message -x` | Wave 0 |
| STOR-02d | Per-user check runs before global check (fail fast) | unit | `pytest tests/test_storage_limits.py::test_per_user_checked_before_global -x` | Wave 0 |
| STOR-CFG | Config has new env vars, SIZE_LIMIT removed | unit | `pytest tests/test_storage_limits.py::test_config_keys -x` | Wave 0 |
| STOR-READ | read_file no longer appends soft warning | unit | `pytest tests/test_storage_limits.py::test_read_no_soft_warning -x` | Wave 0 |
| STOR-BYTE | Multi-byte characters counted correctly (bytes, not chars) | unit | `pytest tests/test_storage_limits.py::test_multibyte_char_size -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_storage_limits.py` -- covers STOR-01, STOR-02, config changes, read_file cleanup
- [ ] Update `tests/test_user_isolation.py:_mock_config()` -- replace `SIZE_LIMIT` with new keys
- [ ] No new framework or fixture needed -- existing `tmp_data_dir`, `mcp_with_tools`, mock patterns are sufficient

## Sources

### Primary (HIGH confidence)
- Project source code: `config.py`, `tools.py`, `user_identity.py`, `server.py` -- read directly
- Project test code: `tests/conftest.py`, `tests/test_user_isolation.py` -- read directly
- `pyproject.toml` -- project configuration, test framework
- Python 3.12 stdlib `pathlib.Path.rglob()` -- standard approach for recursive directory traversal

### Secondary (MEDIUM confidence)
- [Python directory size calculation patterns](https://note.nkmk.me/en/python-os-path-getsize/) -- `Path.rglob('*')` with `stat().st_size` is the standard modern approach

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- pure Python stdlib, no external libraries needed
- Architecture: HIGH -- single integration point (`write_file`), clear pattern from existing code
- Pitfalls: HIGH -- well-understood domain (file I/O, byte counting), verified against source

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (stable domain, no external dependencies)
