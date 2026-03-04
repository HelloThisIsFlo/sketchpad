from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (if present) before reading config
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from sketchpad.server import create_app  # noqa: E402

app = create_app()
app.run(transport="http", host="0.0.0.0", port=8000)
