"""Tests for tool descriptions, Field annotations, and newline behavior (DESC-01..03, D-05)."""

import asyncio
from unittest.mock import patch

import pytest

from sketchpad.tools import register_tools


# ---------------------------------------------------------------------------
# Test helpers -- same pattern as test_parameter_validation.py
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
# DESC-01: Docstrings reframed as inter-agent persistence layer
# ---------------------------------------------------------------------------


def test_read_file_description(mcp_with_tools):
    """read_file description mentions Sketchpad as a persistence layer."""
    tool = asyncio.run(mcp_with_tools.get_tool("read_file"))
    desc = tool.description
    assert "Sketchpad" in desc, f"Expected 'Sketchpad' in description: {desc}"
    assert "persistence" in desc.lower(), (
        f"Expected 'persistence' in description: {desc}"
    )


def test_write_file_description(mcp_with_tools):
    """write_file description mentions Sketchpad as a persistence layer."""
    tool = asyncio.run(mcp_with_tools.get_tool("write_file"))
    desc = tool.description
    assert "Sketchpad" in desc, f"Expected 'Sketchpad' in description: {desc}"
    assert "persistence" in desc.lower(), (
        f"Expected 'persistence' in description: {desc}"
    )


def test_descriptions_no_scratchpad(mcp_with_tools):
    """Neither tool description contains 'scratchpad' (D-04)."""
    for name in ("read_file", "write_file"):
        tool = asyncio.run(mcp_with_tools.get_tool(name))
        desc = tool.description.lower()
        assert "scratchpad" not in desc, (
            f"{name} description contains 'scratchpad': {tool.description}"
        )


# ---------------------------------------------------------------------------
# DESC-02: Field(description=...) visible in JSON schema
# ---------------------------------------------------------------------------


def test_content_param_has_description(mcp_with_tools):
    """write_file JSON schema properties.content has a 'description' key."""
    tool = asyncio.run(mcp_with_tools.get_tool("write_file"))
    content_schema = tool.parameters["properties"]["content"]
    assert "description" in content_schema, (
        f"Expected 'description' in content schema: {content_schema}"
    )


def test_mode_param_has_description(mcp_with_tools):
    """write_file JSON schema properties.mode has a 'description' key."""
    tool = asyncio.run(mcp_with_tools.get_tool("write_file"))
    mode_schema = tool.parameters["properties"]["mode"]
    assert "description" in mode_schema, (
        f"Expected 'description' in mode schema: {mode_schema}"
    )


# ---------------------------------------------------------------------------
# DESC-03: Usage guidelines (Do / Do NOT guardrails)
# ---------------------------------------------------------------------------


def test_write_description_has_do_guardrails(mcp_with_tools):
    """write_file description contains Do and Do NOT guardrails (D-01)."""
    tool = asyncio.run(mcp_with_tools.get_tool("write_file"))
    desc = tool.description
    assert "Do NOT" in desc, f"Expected 'Do NOT' in description: {desc}"


def test_write_description_no_storage_limits(mcp_with_tools):
    """write_file description does NOT mention storage limits (D-02)."""
    tool = asyncio.run(mcp_with_tools.get_tool("write_file"))
    desc = tool.description.lower()
    for forbidden in ("limit", "size", "bytes"):
        assert forbidden not in desc, (
            f"Description should not mention '{forbidden}': {tool.description}"
        )


def test_write_description_user_asks(mcp_with_tools):
    """write_file description mentions user explicitly asking (D-08)."""
    tool = asyncio.run(mcp_with_tools.get_tool("write_file"))
    desc = tool.description.lower()
    assert "user" in desc and "ask" in desc, (
        f"Expected 'user' and 'ask' in description: {tool.description}"
    )


def test_read_description_check_prior_context(mcp_with_tools):
    """read_file description mentions checking for prior context (D-07)."""
    tool = asyncio.run(mcp_with_tools.get_tool("read_file"))
    desc = tool.description.lower()
    assert "prior" in desc or "context" in desc, (
        f"Expected 'prior' or 'context' in description: {tool.description}"
    )


# ---------------------------------------------------------------------------
# D-05: Newline separator in append mode
# ---------------------------------------------------------------------------


def test_append_newline_separator(tmp_data_dir, mcp_with_tools):
    """Appending to existing content inserts a newline separator."""
    write_fn = _get_tool_fn(mcp_with_tools, "write_file")
    read_fn = _get_tool_fn(mcp_with_tools, "read_file")

    auth_patch, config_patch = _patch_auth_and_config(tmp_data_dir, "testuser")
    with auth_patch, config_patch:
        write_fn(content="first")
        write_fn(content="second")
        result = read_fn()

    assert result == "first\nsecond", f"Expected 'first\\nsecond', got {result!r}"


def test_first_append_no_leading_newline(tmp_data_dir, mcp_with_tools):
    """First write to non-existent file does NOT start with a newline."""
    write_fn = _get_tool_fn(mcp_with_tools, "write_file")
    read_fn = _get_tool_fn(mcp_with_tools, "read_file")

    auth_patch, config_patch = _patch_auth_and_config(tmp_data_dir, "testuser")
    with auth_patch, config_patch:
        write_fn(content="hello")
        result = read_fn()

    assert not result.startswith("\n"), f"Content starts with newline: {result!r}"
    assert result == "hello", f"Expected 'hello', got {result!r}"
