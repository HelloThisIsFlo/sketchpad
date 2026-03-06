"""Tests for per-user and global storage size limits (STOR-01, STOR-02)."""

import asyncio
import logging
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from sketchpad.config import get_config
from sketchpad.tools import register_tools

# ---------------------------------------------------------------------------
# Test helpers -- same pattern as test_user_isolation.py
# ---------------------------------------------------------------------------


class MockAccessToken:
    """Minimal mock for fastmcp AccessToken with a claims dict."""

    def __init__(self, claims):
        self.claims = claims


def _mock_config(tmp_data_dir, **overrides):
    """Return a config dict with new storage limit keys.

    Accepts keyword overrides so individual tests can set custom limits.
    """
    cfg = {
        "DATA_DIR": str(tmp_data_dir),
        "OAUTH_PROVIDER": "github",
        "SKETCHPAD_FILENAME": "sketchpad.md",
        "MAX_STORAGE_USER": 20000,
        "MAX_STORAGE_GLOBAL": 52428800,
    }
    cfg.update(overrides)
    return cfg


def _patch_auth_and_config(tmp_data_dir, login, **config_overrides):
    """Return a tuple of patchers for get_access_token and get_config."""
    token = MockAccessToken({"login": login}) if login is not None else None
    auth_patch = patch("sketchpad.tools.get_access_token", return_value=token)
    config_patch = patch(
        "sketchpad.tools.get_config",
        return_value=_mock_config(tmp_data_dir, **config_overrides),
    )
    return auth_patch, config_patch


def _get_tool_fn(mcp, name):
    """Get a registered tool's underlying function via the async get_tool API."""
    tool = asyncio.run(mcp.get_tool(name))
    return tool.fn


@pytest.fixture
def mcp_with_tools():
    """Create a FastMCP instance with tools registered."""
    from fastmcp import FastMCP

    mcp = FastMCP("test")
    register_tools(mcp)
    return mcp


# ---------------------------------------------------------------------------
# STOR-CFG: Config keys
# ---------------------------------------------------------------------------


def test_config_keys(monkeypatch):
    """get_config() returns MAX_STORAGE_USER and MAX_STORAGE_GLOBAL; SIZE_LIMIT absent."""
    get_config.cache_clear()
    try:
        monkeypatch.setenv("JWT_SIGNING_KEY", "test-key")
        monkeypatch.setenv("STORAGE_ENCRYPTION_KEY", "test-enc-key")
        monkeypatch.setenv("GITHUB_CLIENT_ID", "id")
        monkeypatch.setenv("GITHUB_CLIENT_SECRET", "secret")
        monkeypatch.setenv("MAX_STORAGE_USER", "12345")
        monkeypatch.setenv("MAX_STORAGE_GLOBAL", "99999")

        cfg = get_config()

        assert "MAX_STORAGE_USER" in cfg
        assert cfg["MAX_STORAGE_USER"] == 12345
        assert "MAX_STORAGE_GLOBAL" in cfg
        assert cfg["MAX_STORAGE_GLOBAL"] == 99999
        assert "SIZE_LIMIT" not in cfg
    finally:
        get_config.cache_clear()


# ---------------------------------------------------------------------------
# STOR-01: Per-user limits
# ---------------------------------------------------------------------------


def test_replace_exceeds_user_limit(tmp_data_dir, mcp_with_tools):
    """write_file with content exceeding per-user limit is rejected, file not created."""
    write_fn = _get_tool_fn(mcp_with_tools, "write_file")

    auth_patch, config_patch = _patch_auth_and_config(
        tmp_data_dir, "alice", MAX_STORAGE_USER=20000
    )
    with auth_patch, config_patch:
        result = write_fn(content="x" * 20001, mode="replace")

    # Should be rejected
    assert isinstance(result, str)
    assert "too large" in result.lower() or "sketchpad" in result.lower()

    # File should NOT exist on disk
    sketchpad_path = Path(tmp_data_dir) / "github" / "alice" / "sketchpad.md"
    assert not sketchpad_path.exists()


def test_append_exceeds_user_limit(tmp_data_dir, mcp_with_tools):
    """Appending content that pushes total over per-user limit is rejected."""
    write_fn = _get_tool_fn(mcp_with_tools, "write_file")

    # Pre-populate file with 15000 bytes
    user_dir = Path(tmp_data_dir) / "github" / "alice"
    user_dir.mkdir(parents=True, exist_ok=True)
    sketchpad_path = user_dir / "sketchpad.md"
    sketchpad_path.write_text("a" * 15000, encoding="utf-8")

    auth_patch, config_patch = _patch_auth_and_config(
        tmp_data_dir, "alice", MAX_STORAGE_USER=20000
    )
    with auth_patch, config_patch:
        result = write_fn(content="b" * 6000, mode="append")

    # Should be rejected (15000 + 6000 = 21000 > 20000)
    assert "too large" in result.lower() or "sketchpad" in result.lower()

    # File should be unchanged
    assert sketchpad_path.read_text(encoding="utf-8") == "a" * 15000


def test_at_user_limit_accepted(tmp_data_dir, mcp_with_tools):
    """Content exactly at the per-user limit is accepted."""
    write_fn = _get_tool_fn(mcp_with_tools, "write_file")

    auth_patch, config_patch = _patch_auth_and_config(
        tmp_data_dir, "alice", MAX_STORAGE_USER=20000
    )
    with auth_patch, config_patch:
        result = write_fn(content="x" * 20000, mode="replace")

    # Should succeed
    assert "updated" in result.lower()

    # File should exist with content
    sketchpad_path = Path(tmp_data_dir) / "github" / "alice" / "sketchpad.md"
    assert sketchpad_path.exists()


def test_user_limit_error_message(tmp_data_dir, mcp_with_tools):
    """Per-user rejection contains 'Sketchpad too large', no raw digit sequences."""
    write_fn = _get_tool_fn(mcp_with_tools, "write_file")

    auth_patch, config_patch = _patch_auth_and_config(
        tmp_data_dir, "alice", MAX_STORAGE_USER=100
    )
    with auth_patch, config_patch:
        result = write_fn(content="x" * 200, mode="replace")

    assert "Sketchpad too large" in result
    # No raw numbers (digit sequences) in the message
    assert not re.search(r"\d+", result), f"Found digits in message: {result}"


def test_user_limit_logged_warning(tmp_data_dir, mcp_with_tools, caplog):
    """Per-user limit exceeded is logged at WARNING level."""
    write_fn = _get_tool_fn(mcp_with_tools, "write_file")

    auth_patch, config_patch = _patch_auth_and_config(
        tmp_data_dir, "alice", MAX_STORAGE_USER=100
    )
    with caplog.at_level(logging.WARNING):
        with auth_patch, config_patch:
            write_fn(content="x" * 200, mode="replace")

    # Should contain a warning about storage/user limit
    assert any(
        "storage" in r.message.lower() or "user" in r.message.lower()
        for r in caplog.records
        if r.levelno >= logging.WARNING
    ), f"Expected WARNING with 'storage' or 'user', got: {caplog.text}"


# ---------------------------------------------------------------------------
# STOR-02: Global limits
# ---------------------------------------------------------------------------


def test_global_limit_exceeded(tmp_data_dir, mcp_with_tools):
    """Write rejected when global data dir usage would exceed global limit."""
    write_fn = _get_tool_fn(mcp_with_tools, "write_file")

    # Fill data dir with files from a different user to simulate global usage
    other_dir = Path(tmp_data_dir) / "github" / "biguser"
    other_dir.mkdir(parents=True, exist_ok=True)
    big_file = other_dir / "big.dat"
    big_file.write_bytes(b"x" * 50000)

    # Set global limit to 50000 -- existing data already at limit
    auth_patch, config_patch = _patch_auth_and_config(
        tmp_data_dir, "alice", MAX_STORAGE_USER=100000, MAX_STORAGE_GLOBAL=50000
    )
    with auth_patch, config_patch:
        result = write_fn(content="new content", mode="replace")

    # Should be rejected by global limit
    assert "storage full" in result.lower() or "server" in result.lower()


def test_global_limit_replace_net_addition(tmp_data_dir, mcp_with_tools):
    """Replace with same-size content: net addition is 0, global check passes."""
    write_fn = _get_tool_fn(mcp_with_tools, "write_file")

    # Pre-populate alice's file with 5000 bytes
    user_dir = Path(tmp_data_dir) / "github" / "alice"
    user_dir.mkdir(parents=True, exist_ok=True)
    sketchpad = user_dir / "sketchpad.md"
    sketchpad.write_text("a" * 5000, encoding="utf-8")

    # Fill rest of data dir near capacity
    other_dir = Path(tmp_data_dir) / "github" / "biguser"
    other_dir.mkdir(parents=True, exist_ok=True)
    big_file = other_dir / "big.dat"
    big_file.write_bytes(b"x" * 45000)

    # Global = 5000 + 45000 = 50000, limit = 50000
    # Replacing alice's 5000 with 5000 -> net addition = 0 -> should pass
    auth_patch, config_patch = _patch_auth_and_config(
        tmp_data_dir, "alice", MAX_STORAGE_USER=100000, MAX_STORAGE_GLOBAL=50000
    )
    with auth_patch, config_patch:
        result = write_fn(content="b" * 5000, mode="replace")

    assert "updated" in result.lower()


def test_global_limit_error_message(tmp_data_dir, mcp_with_tools):
    """Global rejection contains 'Server storage full', no raw numbers."""
    write_fn = _get_tool_fn(mcp_with_tools, "write_file")

    # Fill data dir
    other_dir = Path(tmp_data_dir) / "github" / "biguser"
    other_dir.mkdir(parents=True, exist_ok=True)
    big_file = other_dir / "big.dat"
    big_file.write_bytes(b"x" * 50000)

    auth_patch, config_patch = _patch_auth_and_config(
        tmp_data_dir, "alice", MAX_STORAGE_USER=100000, MAX_STORAGE_GLOBAL=50000
    )
    with auth_patch, config_patch:
        result = write_fn(content="extra", mode="replace")

    assert "Server storage full" in result
    assert not re.search(r"\d+", result), f"Found digits in message: {result}"


def test_per_user_checked_before_global(tmp_data_dir, mcp_with_tools):
    """When both limits would be exceeded, per-user message is returned (fail fast)."""
    write_fn = _get_tool_fn(mcp_with_tools, "write_file")

    # Fill data dir past global limit
    other_dir = Path(tmp_data_dir) / "github" / "biguser"
    other_dir.mkdir(parents=True, exist_ok=True)
    big_file = other_dir / "big.dat"
    big_file.write_bytes(b"x" * 50000)

    # Content exceeds both per-user (100) AND global (50000)
    auth_patch, config_patch = _patch_auth_and_config(
        tmp_data_dir, "alice", MAX_STORAGE_USER=100, MAX_STORAGE_GLOBAL=50000
    )
    with auth_patch, config_patch:
        result = write_fn(content="x" * 200, mode="replace")

    # Per-user message, not global
    assert "Sketchpad too large" in result
    assert "Server storage full" not in result


# ---------------------------------------------------------------------------
# STOR-READ: read_file no longer appends soft warning
# ---------------------------------------------------------------------------


def test_read_no_soft_warning(tmp_data_dir, mcp_with_tools):
    """read_file returns content without the legacy soft-size warning."""
    read_fn = _get_tool_fn(mcp_with_tools, "read_file")

    # Write large content directly to bypass write_file limit checks
    user_dir = Path(tmp_data_dir) / "github" / "alice"
    user_dir.mkdir(parents=True, exist_ok=True)
    sketchpad = user_dir / "sketchpad.md"
    large_content = "x" * 60000
    sketchpad.write_text(large_content, encoding="utf-8")

    auth_patch, config_patch = _patch_auth_and_config(
        tmp_data_dir, "alice", MAX_STORAGE_USER=100000
    )
    with auth_patch, config_patch:
        result = read_fn()

    # Content should be returned as-is, no warning appended
    assert result == large_content
    assert "WARNING" not in result
    assert "exceeds" not in result.lower()


# ---------------------------------------------------------------------------
# STOR-BYTE: Multi-byte character size
# ---------------------------------------------------------------------------


def test_multibyte_char_size(tmp_data_dir, mcp_with_tools):
    """Multi-byte characters (emoji) are measured in bytes, not characters."""
    write_fn = _get_tool_fn(mcp_with_tools, "write_file")

    # Each emoji is 4 bytes in UTF-8. 5001 emoji = 20004 bytes > 20000 limit
    # But only 5001 characters
    emoji_content = "\U0001f600" * 5001  # grinning face emoji

    auth_patch, config_patch = _patch_auth_and_config(
        tmp_data_dir, "alice", MAX_STORAGE_USER=20000
    )
    with auth_patch, config_patch:
        result = write_fn(content=emoji_content, mode="replace")

    # Should be rejected because bytes > limit, even though chars < limit
    assert "too large" in result.lower() or "sketchpad" in result.lower()

    # File should NOT exist on disk
    sketchpad_path = Path(tmp_data_dir) / "github" / "alice" / "sketchpad.md"
    assert not sketchpad_path.exists()
