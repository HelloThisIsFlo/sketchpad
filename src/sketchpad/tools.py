import logging
from pathlib import Path
from typing import Literal

from fastmcp.server.dependencies import get_access_token

from sketchpad.config import get_config
from sketchpad.user_identity import resolve_user_dir

logger = logging.getLogger(__name__)

WELCOME_MESSAGE = "Welcome to Sketchpad! Write something here."


def _get_user_sketchpad_path() -> Path:
    """Extract authenticated user identity and resolve their sketchpad path."""
    token = get_access_token()
    assert token is not None, "Internal error: missing authentication context"
    login = token.claims.get("login")
    assert login, "Internal error: missing user identity in token"
    cfg = get_config()
    user_dir = resolve_user_dir(cfg["DATA_DIR"], cfg["OAUTH_PROVIDER"], login)
    return user_dir / cfg["SKETCHPAD_FILENAME"]


def _calculate_dir_size(directory: Path) -> int:
    """Sum of all file sizes in a directory tree."""
    return sum(f.stat().st_size for f in directory.rglob("*") if f.is_file())


def register_tools(mcp):
    """Register read_file and write_file tools on the given FastMCP instance."""

    @mcp.tool
    def read_file() -> str:
        """Read your personal sketchpad. This is your private Markdown file,
        shared across all your AI agents (Claude, Cursor, etc.) that use
        the same GitHub identity."""
        sketchpad_path = _get_user_sketchpad_path()
        if not sketchpad_path.exists():
            return WELCOME_MESSAGE

        content = sketchpad_path.read_text(encoding="utf-8")

        return content

    @mcp.tool
    def write_file(content: str, mode: Literal["replace", "append"] = "append") -> str:
        """Write to your personal sketchpad. Use this for notes, drafts,
        ideas -- Markdown formatting recommended but not required. Your
        sketchpad is shared across all your AI agents that use the same
        GitHub identity.

        Args:
            content: The text to write.
            mode: 'append' (default) adds to the end; 'replace' overwrites the file.
        """
        sketchpad_path = _get_user_sketchpad_path()
        sketchpad_path.parent.mkdir(parents=True, exist_ok=True)

        cfg = get_config()
        content_bytes = len(content.encode("utf-8"))

        # Per-user limit (STOR-01) -- check first, fail fast
        if mode == "append":
            existing_size = (
                sketchpad_path.stat().st_size if sketchpad_path.exists() else 0
            )
            resulting_size = existing_size + content_bytes
        else:
            resulting_size = content_bytes

        if resulting_size > cfg["MAX_STORAGE_USER"]:
            logger.warning("Per-user storage limit exceeded for write")
            return "Sketchpad too large. Try reducing the size of your sketchpad."

        # Global limit (STOR-02)
        data_dir = Path(cfg["DATA_DIR"]).resolve()
        global_size = _calculate_dir_size(data_dir)
        current_file_size = (
            sketchpad_path.stat().st_size if sketchpad_path.exists() else 0
        )
        net_addition = resulting_size - current_file_size
        if global_size + net_addition > cfg["MAX_STORAGE_GLOBAL"]:
            logger.warning("Global storage limit exceeded for write")
            return "Server storage full. Try again later or reduce your sketchpad size."

        if mode == "append":
            existing = (
                sketchpad_path.read_text(encoding="utf-8")
                if sketchpad_path.exists()
                else ""
            )
            sketchpad_path.write_text(existing + content, encoding="utf-8")
        else:
            sketchpad_path.write_text(content, encoding="utf-8")

        return (
            f"File updated ({mode} mode). Size: {sketchpad_path.stat().st_size} bytes."
        )
