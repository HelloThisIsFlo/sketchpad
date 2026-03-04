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


def create_app() -> FastMCP:
    """Create and configure the FastMCP server with GitHub OAuth and file tools.

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

    # GitHub OAuth provider -- handles all OAuth 2.1 endpoints automatically:
    # /.well-known/oauth-authorization-server, /.well-known/oauth-protected-resource,
    # /register, /authorize, /token, /auth/callback
    auth = GitHubProvider(
        client_id=cfg["GITHUB_CLIENT_ID"],
        client_secret=cfg["GITHUB_CLIENT_SECRET"],
        base_url=cfg["SERVER_URL"],
        jwt_signing_key=cfg["JWT_SIGNING_KEY"],
        client_storage=encrypted_store,
    )

    mcp = FastMCP(name="Sketchpad", auth=auth)
    register_tools(mcp)

    return mcp


if __name__ == "__main__":
    app = create_app()
    app.run(transport="http", host="0.0.0.0", port=8000)
