import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class OriginValidationMiddleware(BaseHTTPMiddleware):
    """Reject requests to protected paths with disallowed Origin headers.

    Non-browser clients (curl, CLI) that omit Origin are allowed through
    so they can reach the auth layer. Only explicit bad Origins are blocked.
    """

    def __init__(
        self,
        app,
        allowed_origins: list[str],
        protected_paths: list[str] | None = None,
    ):
        super().__init__(app)
        self.allowed_origins: set[str] = set(allowed_origins)
        self.protected_paths: set[str] = set(
            protected_paths if protected_paths is not None else ["/mcp"]
        )

    async def dispatch(self, request: Request, call_next):
        if request.url.path not in self.protected_paths:
            return await call_next(request)

        origin = request.headers.get("origin")
        if origin is None:
            # Non-browser client (curl, CLI) -- let auth layer handle it
            return await call_next(request)

        if origin in self.allowed_origins:
            return await call_next(request)

        logger.warning(
            "Blocked request with disallowed Origin: %s from %s to %s",
            origin,
            request.client.host if request.client else "unknown",
            request.url.path,
        )
        return JSONResponse(
            status_code=403,
            content={
                "error": "origin_not_allowed",
                "detail": f"Origin '{origin}' is not in the allowlist",
            },
        )
