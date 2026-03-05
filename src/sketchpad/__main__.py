from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (if present) before reading config
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from starlette.middleware import Middleware  # noqa: E402

from sketchpad.config import get_config  # noqa: E402
from sketchpad.middleware import OriginValidationMiddleware  # noqa: E402
from sketchpad.server import create_app  # noqa: E402

app = create_app()
cfg = get_config()

middleware = [
    Middleware(
        OriginValidationMiddleware,
        allowed_origins=cfg["ALLOWED_ORIGINS"],
    ),
]

app.run(transport="http", host="0.0.0.0", port=8000, middleware=middleware)
