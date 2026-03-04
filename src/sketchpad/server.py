from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.auth.providers.github import GitHubProvider
from key_value.aio.stores.filetree import (
    FileTreeStore,
    FileTreeV1KeySanitizationStrategy,
    FileTreeV1CollectionSanitizationStrategy,
)
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from cryptography.fernet import Fernet

from sketchpad.config import get_config
from sketchpad.tools import register_tools


def create_oauth_provider(cfg, client_storage):
    """Build the OAuth provider based on OAUTH_PROVIDER config.

    Currently only 'github' is implemented. Raises ValueError for
    unknown providers so the server fails fast at startup.
    """
    provider = cfg["OAUTH_PROVIDER"]

    if provider == "github":
        return GitHubProvider(
            client_id=cfg["GITHUB_CLIENT_ID"],
            client_secret=cfg["GITHUB_CLIENT_SECRET"],
            base_url=cfg["SERVER_URL"],
            jwt_signing_key=cfg["JWT_SIGNING_KEY"],
            client_storage=client_storage,
        )

    raise ValueError(
        f"Unknown OAUTH_PROVIDER: '{provider}'. "
        f"Supported providers: github. "
        f"Set OAUTH_PROVIDER in your .env file."
    )


def create_app() -> FastMCP:
    """Create and configure the FastMCP server with OAuth and file tools.

    Reads environment variables via get_config() -- will raise KeyError
    if required vars are missing. This is intentional: fail fast at startup.
    """
    cfg = get_config()

    # Persistent encrypted storage for OAuth state (tokens, clients, etc.)
    state_dir = Path(cfg["STATE_DIR"])
    state_dir.mkdir(parents=True, exist_ok=True)

    store = FileTreeStore(
        data_directory=state_dir,
        key_sanitization_strategy=FileTreeV1KeySanitizationStrategy(state_dir),
        collection_sanitization_strategy=FileTreeV1CollectionSanitizationStrategy(
            state_dir
        ),
    )
    encrypted_store = FernetEncryptionWrapper(
        key_value=store,
        fernet=Fernet(cfg["STORAGE_ENCRYPTION_KEY"]),
    )

    auth = create_oauth_provider(cfg, encrypted_store)

    mcp = FastMCP(name="Sketchpad", auth=auth)
    register_tools(mcp)

    return mcp


if __name__ == "__main__":
    app = create_app()
    app.run(transport="http", host="0.0.0.0", port=8000)
