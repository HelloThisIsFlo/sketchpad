# Sketchpad MCP Server — Multi-stage uv build
# ==============================================
# Uses uv (https://docs.astral.sh/uv/) to manage Python dependencies.
# Two-stage build: builder installs deps into a .venv, runtime copies only the venv.
#
# Build: docker build -t ghcr.io/<owner>/sketchpad:latest .
# Run:   docker run -p 8000:8000 --env-file .env ghcr.io/<owner>/sketchpad:latest
#
# The server starts via `python -m sketchpad`, which calls create_app()
# and runs the FastMCP Streamable HTTP transport on 0.0.0.0:8000.
# Internally, FastMCP uses uvicorn as its ASGI server.

# --- Builder stage: install dependencies with uv ---
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first for layer caching.
# uv.lock and pyproject.toml are bind-mounted so they don't end up in the layer,
# but the installed .venv does. This means dependency changes rebuild this layer,
# but source code changes skip it.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --compile-bytecode

# Copy full source and install the project itself.
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --compile-bytecode

# --- Runtime stage: slim image with only the venv ---
FROM python:3.12-slim

WORKDIR /app

# Copy the fully built virtual environment from the builder.
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# The MCP server listens on port 8000.
EXPOSE 8000

# Start the FastMCP server via the package entry point.
# create_app() configures GitHubProvider OAuth and registers tools.
# FastMCP internally runs uvicorn for the Streamable HTTP transport.
CMD ["python", "-m", "sketchpad"]
