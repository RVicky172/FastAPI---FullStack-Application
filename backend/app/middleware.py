"""
Middleware = code that wraps EVERY request/response.

    request  ->  [Middleware A] -> [Middleware B] -> route handler
    response <-  [Middleware A] <- [Middleware B] <- route handler

Good for cross-cutting concerns: logging, timing, request IDs, auth headers,
rate limiting, etc. Below are two custom middlewares written as classes.
(main.py also shows the shorter decorator style: @app.middleware("http").)
"""
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("todo_api")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Gives every request a unique ID (handy for tracing logs)."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:8]
        # Anything stored on request.state is available inside route handlers.
        request.state.request_id = request_id

        response = await call_next(request)  # <- passes control to the next layer

        response.headers["X-Request-ID"] = request_id
        return response


class TimingLoggingMiddleware(BaseHTTPMiddleware):
    """Logs method, path, status and how long the request took."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
        logger.info(
            "[%s] %s %s -> %s (%.2fms)",
            getattr(request.state, "request_id", "-"),
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
