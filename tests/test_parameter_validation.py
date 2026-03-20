"""Tests for write_file mode parameter validation (VALID-01..04)."""

import asyncio
from typing import Literal, get_type_hints
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from sketchpad.tools import register_tools

# ---------------------------------------------------------------------------
# Test helpers -- same pattern as test_user_isolation.py
# ---------------------------------------------------------------------------


class MockAccessToken:
    """Minimal mock for fastmcp AccessToken with a claims dict."""

    def __init__(self, claims):
        self.claims = claims


def _mock_config(tmp_data_dir):
    return {
        "DATA_DIR": str(tmp_data_dir),
        "OAUTH_PROVIDER": "github",
        "SKETCHPAD_FILENAME": "sketchpad.md",
        "MAX_STORAGE_USER": 20000,
        "MAX_STORAGE_GLOBAL": 52428800,
    }


def _patch_auth_and_config(tmp_data_dir, login):
    token = MockAccessToken({"login": login})
    auth_patch = patch("sketchpad.tools.get_access_token", return_value=token)
    config_patch = patch(
        "sketchpad.tools.get_config", return_value=_mock_config(tmp_data_dir)
    )
    return auth_patch, config_patch


def _get_tool_fn(mcp, name):
    tool = asyncio.run(mcp.get_tool(name))
    return tool.fn


@pytest.fixture
def mcp_with_tools():
    from fastmcp import FastMCP

    mcp = FastMCP("test")
    register_tools(mcp)
    return mcp


# ---------------------------------------------------------------------------
# VALID-01: Literal type annotation
# ---------------------------------------------------------------------------


def test_literal_type_annotation(mcp_with_tools):
    """write_file mode parameter has Literal['replace', 'append'] annotation."""
    write_fn = _get_tool_fn(mcp_with_tools, "write_file")
    hints = get_type_hints(write_fn)
    assert hints["mode"] is Literal["replace", "append"], (
        f"Expected Literal['replace', 'append'], got {hints['mode']}"
    )


# ---------------------------------------------------------------------------
# VALID-02: Default mode is append
# ---------------------------------------------------------------------------


def test_default_mode_is_append(tmp_data_dir, mcp_with_tools):
    """Calling write_file without mode= appends (does not replace)."""
    write_fn = _get_tool_fn(mcp_with_tools, "write_file")
    read_fn = _get_tool_fn(mcp_with_tools, "read_file")

    auth_patch, config_patch = _patch_auth_and_config(tmp_data_dir, "testuser")
    with auth_patch, config_patch:
        write_fn(content="first")
        write_fn(content=" second")
        result = read_fn()

    assert result == "first\n second"


# ---------------------------------------------------------------------------
# VALID-03: JSON schema enum
# ---------------------------------------------------------------------------


def test_schema_enum(mcp_with_tools):
    """JSON schema for mode parameter contains enum and correct default."""

    async def _check():
        tool = await mcp_with_tools.get_tool("write_file")
        schema = tool.parameters
        mode_schema = schema["properties"]["mode"]
        assert mode_schema["enum"] == ["replace", "append"], (
            f"Expected enum ['replace', 'append'], got {mode_schema}"
        )
        assert mode_schema["default"] == "append", (
            f"Expected default 'append', got {mode_schema.get('default')}"
        )

    asyncio.run(_check())


# ---------------------------------------------------------------------------
# VALID-04: Invalid mode rejected via tool.run()
# ---------------------------------------------------------------------------


def test_invalid_mode_rejected(mcp_with_tools):
    """Invalid mode value is rejected by Pydantic before function body runs.

    CRITICAL: Must use tool.run() (Pydantic path), NOT tool.fn() (bypasses validation).
    """

    async def _check():
        tool = await mcp_with_tools.get_tool("write_file")
        with pytest.raises(ValidationError, match="literal_error"):
            await tool.run({"content": "hello", "mode": "banana"})

    asyncio.run(_check())
