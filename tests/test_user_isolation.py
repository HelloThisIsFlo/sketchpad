import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest

from sketchpad.user_identity import resolve_user_dir
from sketchpad.tools import WELCOME_MESSAGE, _get_user_sketchpad_path


def test_user_path_resolution(tmp_data_dir):
    result = resolve_user_dir(tmp_data_dir, "github", "octocat")
    assert result == Path(tmp_data_dir).resolve() / "github" / "octocat"


def test_two_users_isolated(tmp_data_dir):
    alice = resolve_user_dir(tmp_data_dir, "github", "alice")
    bob = resolve_user_dir(tmp_data_dir, "github", "bob")
    assert alice != bob


def test_username_lowercased(tmp_data_dir):
    result = resolve_user_dir(tmp_data_dir, "github", "Octocat")
    assert "octocat" in str(result)
    assert "Octocat" not in str(result)


def test_path_traversal_blocked(tmp_data_dir):
    with pytest.raises(ValueError, match="Invalid request"):
        resolve_user_dir(tmp_data_dir, "github", "../etc")


def test_traversal_logged(tmp_data_dir, caplog):
    import logging

    with caplog.at_level(logging.WARNING):
        with pytest.raises(ValueError):
            resolve_user_dir(tmp_data_dir, "github", "../etc")
    # "../etc" is caught by regex validation (dots/slashes are invalid GitHub chars)
    # before reaching the is_relative_to defense-in-depth check. Either way, the
    # operator sees a WARNING-level log entry for the suspicious input.
    assert "../etc" in caplog.text
    assert "WARNING" in caplog.text


@pytest.mark.parametrize(
    "username",
    [
        "",
        "-leadinghyphen",
        "has spaces",
        "has.dots",
        "a" * 40,
    ],
    ids=[
        "empty",
        "leading-hyphen",
        "spaces",
        "dots",
        "too-long-40-chars",
    ],
)
def test_invalid_username_rejected(tmp_data_dir, username):
    with pytest.raises(ValueError):
        resolve_user_dir(tmp_data_dir, "github", username)


def test_sanitize_idempotent(tmp_data_dir):
    first = resolve_user_dir(tmp_data_dir, "github", "OctoCat")
    second = resolve_user_dir(tmp_data_dir, "github", "OctoCat")
    assert first == second
    # Already-lowercase is also stable
    lower = resolve_user_dir(tmp_data_dir, "github", "octocat")
    assert lower == first


def test_sanitize_injective(tmp_data_dir):
    # Same user, different case -> same path (GitHub case-insensitive)
    lower = resolve_user_dir(tmp_data_dir, "github", "octocat")
    upper = resolve_user_dir(tmp_data_dir, "github", "Octocat")
    assert lower == upper
    # Different users -> different paths
    other = resolve_user_dir(tmp_data_dir, "github", "octocats")
    assert lower != other


def test_single_char_username(tmp_data_dir):
    result = resolve_user_dir(tmp_data_dir, "github", "a")
    assert result == Path(tmp_data_dir).resolve() / "github" / "a"


def test_auto_create_dir_not_done_by_resolve(tmp_data_dir):
    result = resolve_user_dir(tmp_data_dir, "github", "octocat")
    # resolve_user_dir only computes the path, it does NOT create directories
    assert not result.parent.exists()


def test_unknown_provider_rejected(tmp_data_dir):
    with pytest.raises(ValueError):
        resolve_user_dir(tmp_data_dir, "unknown", "user")


# ---------------------------------------------------------------------------
# Plan 02: Integration tests — tools with mocked auth
# ---------------------------------------------------------------------------


class MockAccessToken:
    """Minimal mock for fastmcp AccessToken with a claims dict."""

    def __init__(self, claims):
        self.claims = claims


def _mock_config(tmp_data_dir):
    """Return a config dict pointing at the given temp directory."""
    return {
        "DATA_DIR": str(tmp_data_dir),
        "OAUTH_PROVIDER": "github",
        "SKETCHPAD_FILENAME": "sketchpad.md",
        "MAX_STORAGE_USER": 20000,
        "MAX_STORAGE_GLOBAL": 52428800,
        # SIZE_LIMIT kept temporarily until tools.py is updated (Task 2)
        "SIZE_LIMIT": 50000,
    }


def _patch_auth_and_config(tmp_data_dir, login):
    """Return a tuple of patchers for get_access_token and get_config."""
    token = MockAccessToken({"login": login}) if login is not None else None
    auth_patch = patch(
        "sketchpad.tools.get_access_token", return_value=token
    )
    config_patch = patch(
        "sketchpad.tools.get_config", return_value=_mock_config(tmp_data_dir)
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
    from sketchpad.tools import register_tools

    mcp = FastMCP("test")
    register_tools(mcp)
    return mcp


def test_read_returns_welcome_for_new_user(tmp_data_dir, mcp_with_tools):
    """A user who has never written before sees the welcome message."""
    read_fn = _get_tool_fn(mcp_with_tools, "read_file")

    auth_patch, config_patch = _patch_auth_and_config(tmp_data_dir, "newuser")
    with auth_patch, config_patch:
        result = read_fn()
    assert result == WELCOME_MESSAGE


def test_auto_create_dir(tmp_data_dir, mcp_with_tools):
    """A user's first write automatically creates their personal directory."""
    write_fn = _get_tool_fn(mcp_with_tools, "write_file")

    auth_patch, config_patch = _patch_auth_and_config(tmp_data_dir, "alice")
    with auth_patch, config_patch:
        write_fn(content="hello")

    expected_path = Path(tmp_data_dir) / "github" / "alice" / "sketchpad.md"
    assert expected_path.exists()
    assert expected_path.read_text(encoding="utf-8") == "hello"


def test_read_after_write(tmp_data_dir, mcp_with_tools):
    """Content written can be read back by the same user."""
    read_fn = _get_tool_fn(mcp_with_tools, "read_file")
    write_fn = _get_tool_fn(mcp_with_tools, "write_file")

    auth_patch, config_patch = _patch_auth_and_config(tmp_data_dir, "alice")
    with auth_patch, config_patch:
        write_fn(content="my notes")
        result = read_fn()
    assert result == "my notes"


def test_two_users_isolated_via_tools(tmp_data_dir, mcp_with_tools):
    """Two users writing to their sketchpads cannot see each other's content."""
    read_fn = _get_tool_fn(mcp_with_tools, "read_file")
    write_fn = _get_tool_fn(mcp_with_tools, "write_file")

    # Alice writes
    alice_auth, alice_config = _patch_auth_and_config(tmp_data_dir, "alice")
    with alice_auth, alice_config:
        write_fn(content="alice data")

    # Bob writes
    bob_auth, bob_config = _patch_auth_and_config(tmp_data_dir, "bob")
    with bob_auth, bob_config:
        write_fn(content="bob data")

    # Alice reads -- should see only her data
    alice_auth2, alice_config2 = _patch_auth_and_config(tmp_data_dir, "alice")
    with alice_auth2, alice_config2:
        result = read_fn()
    assert result == "alice data"
    assert "bob" not in result


def test_missing_token_raises(tmp_data_dir):
    """An unauthenticated request is rejected -- never falls back to shared."""
    auth_patch, config_patch = _patch_auth_and_config(tmp_data_dir, None)
    with auth_patch, config_patch:
        with pytest.raises(AssertionError, match="authentication"):
            _get_user_sketchpad_path()


def test_missing_login_claim_raises(tmp_data_dir):
    """A token without a login claim is rejected."""
    token = MockAccessToken(claims={})
    with patch("sketchpad.tools.get_access_token", return_value=token), \
         patch("sketchpad.tools.get_config", return_value=_mock_config(tmp_data_dir)):
        with pytest.raises(AssertionError, match="identity"):
            _get_user_sketchpad_path()


def test_response_excludes_username(tmp_data_dir, mcp_with_tools):
    """Tool response messages are generic -- no username leaked."""
    write_fn = _get_tool_fn(mcp_with_tools, "write_file")

    auth_patch, config_patch = _patch_auth_and_config(tmp_data_dir, "alice")
    with auth_patch, config_patch:
        result = write_fn(content="test")
    assert "alice" not in result


def test_tool_schema_excludes_username():
    """Verify the tool JSON schema visible to Claude AI has no username/identity params."""
    from fastmcp import FastMCP
    from sketchpad.tools import register_tools

    mcp = FastMCP("test")
    register_tools(mcp)

    async def _check():
        # Inspect read_file schema
        read_tool = await mcp.get_tool("read_file")
        read_schema = read_tool.parameters
        read_params = set(read_schema.get("properties", {}).keys())

        # read_file should have zero parameters
        assert read_params == set(), f"read_file should have no params, got {read_params}"

        # Inspect write_file schema
        write_tool = await mcp.get_tool("write_file")
        write_schema = write_tool.parameters
        write_params = set(write_schema.get("properties", {}).keys())

        # write_file should have only content and mode
        assert write_params == {"content", "mode"}, f"write_file params: {write_params}"

        # Neither tool should have username-related parameters
        forbidden = {"username", "login", "user", "identity", "identifier"}
        assert read_params.isdisjoint(forbidden), (
            f"read_file leaks identity: {read_params & forbidden}"
        )
        assert write_params.isdisjoint(forbidden), (
            f"write_file leaks identity: {write_params & forbidden}"
        )

    asyncio.run(_check())
