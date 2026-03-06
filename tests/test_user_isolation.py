from pathlib import Path

import pytest

from sketchpad.user_identity import resolve_user_dir


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
