import os
from functools import lru_cache


@lru_cache(maxsize=1)
def get_config():
    """Load configuration from environment. Called at server startup, not at import time."""
    return {
        # Required -- KeyError if missing (fail fast at startup, not import)
        "GITHUB_CLIENT_ID": os.environ["GITHUB_CLIENT_ID"],
        "GITHUB_CLIENT_SECRET": os.environ["GITHUB_CLIENT_SECRET"],
        "JWT_SIGNING_KEY": os.environ["JWT_SIGNING_KEY"],
        "STORAGE_ENCRYPTION_KEY": os.environ["STORAGE_ENCRYPTION_KEY"],
        # Optional with defaults
        "SERVER_URL": os.environ.get("SERVER_URL", "http://localhost:8000"),
        "DATA_DIR": os.environ.get("DATA_DIR", "./data"),
        "STATE_DIR": os.environ.get("STATE_DIR", "./state"),
        "SKETCHPAD_FILENAME": os.environ.get("SKETCHPAD_FILENAME", "sketchpad.md"),
        "SIZE_LIMIT": int(os.environ.get("SIZE_LIMIT", "50000")),
    }
