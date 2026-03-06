from pathlib import Path

from cryptography.fernet import Fernet
from fastmcp import FastMCP
from fastmcp.server.auth.providers.github import GitHubProvider
from fastmcp.server.auth.providers.google import GoogleProvider
from key_value.aio.stores.filetree import (
    FileTreeStore,
    FileTreeV1CollectionSanitizationStrategy,
    FileTreeV1KeySanitizationStrategy,
)
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from starlette.requests import Request
from starlette.responses import JSONResponse

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

    if provider == "google":
        return GoogleProvider(
            client_id=cfg["GOOGLE_CLIENT_ID"],
            client_secret=cfg["GOOGLE_CLIENT_SECRET"],
            base_url=cfg["SERVER_URL"],
            jwt_signing_key=cfg["JWT_SIGNING_KEY"],
            client_storage=client_storage,
        )

    raise ValueError(
        f"Unknown OAUTH_PROVIDER: '{provider}'. "
        f"Supported providers: github, google. "
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

    # Health endpoint for K8s liveness/readiness probes.
    # FastMCP's /mcp endpoint returns 401 without auth, which K8s
    # would interpret as unhealthy. This custom route is unauthenticated
    # and returns a simple JSON response.
    @mcp.custom_route("/health", methods=["GET"])
    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "sketchpad"})

    register_tools(mcp)

    return mcp
