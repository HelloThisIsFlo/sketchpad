# Sketchpad MCP Server
# ====================
# Minimal Python image for the MCP server.
# Currently runs a simple HTTP server as a placeholder.
# Phase 2 will add the FastMCP server code and dependencies.
#
# Build: docker build -t ghcr.io/<owner>/sketchpad:latest .
# Push:  docker push ghcr.io/<owner>/sketchpad:latest
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer caching: deps change less often than code).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY . .

# The MCP server listens on port 8000.
EXPOSE 8000

# Placeholder command -- replaced in Phase 2 with the actual FastMCP server.
CMD ["python", "-m", "http.server", "8000"]
