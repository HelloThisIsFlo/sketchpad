from pathlib import Path

from fastmcp.server.dependencies import get_access_token

from sketchpad.config import get_config
from sketchpad.user_identity import resolve_user_dir

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

        cfg = get_config()
        if len(content) > cfg["SIZE_LIMIT"]:
            content += "\n\n---\n[WARNING: File exceeds recommended size limit (~50KB). Consider trimming older content.]"

        return content

    @mcp.tool
    def write_file(content: str, mode: str = "replace") -> str:
        """Write to your personal sketchpad. Use this for notes, drafts,
        ideas -- Markdown formatting recommended but not required. Your
        sketchpad is shared across all your AI agents that use the same
        GitHub identity.

        Args:
            content: The text to write.
            mode: 'replace' (default) overwrites the file; 'append' adds to the end.
        """
        sketchpad_path = _get_user_sketchpad_path()
        sketchpad_path.parent.mkdir(parents=True, exist_ok=True)

        if mode == "append":
            existing = (
                sketchpad_path.read_text(encoding="utf-8")
                if sketchpad_path.exists()
                else ""
            )
            sketchpad_path.write_text(existing + content, encoding="utf-8")
        else:
            sketchpad_path.write_text(content, encoding="utf-8")

        return f"File updated ({mode} mode). Size: {sketchpad_path.stat().st_size} bytes."
