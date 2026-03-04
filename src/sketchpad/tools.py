from pathlib import Path

from sketchpad.config import get_config

WELCOME_MESSAGE = "Welcome to Sketchpad! Write something here."


def register_tools(mcp):
    """Register read_file and write_file tools on the given FastMCP instance."""

    @mcp.tool
    def read_file() -> str:
        """Read the sketchpad file. This is a single shared Markdown file for jotting down notes, ideas, and drafts."""
        cfg = get_config()
        sketchpad_path = Path(cfg["DATA_DIR"]) / cfg["SKETCHPAD_FILENAME"]

        if not sketchpad_path.exists():
            return WELCOME_MESSAGE

        content = sketchpad_path.read_text(encoding="utf-8")

        if len(content) > cfg["SIZE_LIMIT"]:
            content += "\n\n---\n[WARNING: File exceeds recommended size limit (~50KB). Consider trimming older content.]"

        return content

    @mcp.tool
    def write_file(content: str, mode: str = "replace") -> str:
        """Write to the sketchpad file. Use this for notes, drafts, ideas -- Markdown formatting recommended but not required.

        Args:
            content: The text to write.
            mode: 'replace' (default) overwrites the file; 'append' adds to the end.
        """
        cfg = get_config()
        sketchpad_path = Path(cfg["DATA_DIR"]) / cfg["SKETCHPAD_FILENAME"]

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
