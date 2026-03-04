import os
from functools import lru_cache


@lru_cache(maxsize=1)
def get_config():
    """Load configuration from environment. Called at server startup, not at import time."""
    provider = os.environ.get("OAUTH_PROVIDER", "github").lower()

    cfg = {
        "OAUTH_PROVIDER": provider,
        # Required -- KeyError if missing (fail fast at startup, not import)
        "JWT_SIGNING_KEY": os.environ["JWT_SIGNING_KEY"],
        "STORAGE_ENCRYPTION_KEY": os.environ["STORAGE_ENCRYPTION_KEY"],
        # Optional with defaults
        "SERVER_URL": os.environ.get("SERVER_URL", "http://localhost:8000"),
        "DATA_DIR": os.environ.get("DATA_DIR", "./data"),
        "STATE_DIR": os.environ.get("STATE_DIR", "./state"),
        "SKETCHPAD_FILENAME": os.environ.get("SKETCHPAD_FILENAME", "sketchpad.md"),
        "SIZE_LIMIT": int(os.environ.get("SIZE_LIMIT", "50000")),
    }

    # Provider-specific env vars
    if provider == "github":
        cfg["GITHUB_CLIENT_ID"] = os.environ["GITHUB_CLIENT_ID"]
        cfg["GITHUB_CLIENT_SECRET"] = os.environ["GITHUB_CLIENT_SECRET"]
    elif provider == "google":
        cfg["GOOGLE_CLIENT_ID"] = os.environ["GOOGLE_CLIENT_ID"]
        cfg["GOOGLE_CLIENT_SECRET"] = os.environ["GOOGLE_CLIENT_SECRET"]

    return cfg
