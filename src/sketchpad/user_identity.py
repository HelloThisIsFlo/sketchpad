import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# GitHub: alphanumeric + hyphens, 1-39 chars, no leading/trailing hyphens
GITHUB_USERNAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")


def resolve_user_dir(data_dir: str, provider: str, raw_identifier: str) -> Path:
    """Resolve a user's data directory with sanitization and traversal defense.

    Args:
        data_dir: Base data directory path (e.g., "/data").
        provider: OAuth provider name (e.g., "github").
        raw_identifier: Raw username/identifier from OAuth token.

    Returns:
        Resolved Path to the user's data directory.

    Raises:
        ValueError: If the identifier is invalid or path traversal is detected.
    """
    # Step 1: Provider-specific sanitization
    if provider == "github":
        identifier = raw_identifier.lower()
        if not GITHUB_USERNAME_RE.match(identifier) or len(identifier) > 39:
            logger.warning("Invalid GitHub username attempted: %s", raw_identifier)
            raise ValueError("Invalid request")
    else:
        raise ValueError(f"Unknown provider: {provider}")

    # Step 2: Construct path
    base = Path(data_dir).resolve()
    user_dir = (base / provider / identifier).resolve()

    # Step 3: Defense-in-depth -- verify path stays within base
    if not user_dir.is_relative_to(base):
        logger.warning("Path traversal attempt: %s", raw_identifier)
        raise ValueError("Invalid request")

    return user_dir
