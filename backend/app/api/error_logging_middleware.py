"""Middleware that logs unhandled request exceptions to SystemLogRepository."""

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """Logs unhandled exceptions (structlog + a SystemLog row) before re-raising.

    This populates the Logs page without requiring every module to know about
    `SystemLogRepository` directly: any unhandled exception anywhere in the
    request pipeline is captured here, once.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Pass the request through, logging and re-raising on unhandled exceptions.

        Args:
            request: The incoming request.
            call_next: The next handler in the middleware chain.

        Returns:
            The response from the downstream handler.

        Raises:
            Exception: Re-raises whatever exception was caught, after logging it.
        """
        try:
            return await call_next(request)
        except Exception as exc:
            logger.exception("unhandled_request_error", path=request.url.path)
            async with request.app.state.session_factory() as session:
                from app.infrastructure.db.repositories import (
                    SqlAlchemySystemLogRepository,
                )

                await SqlAlchemySystemLogRepository(session).create(
                    level="error",
                    message=str(exc),
                    context={"path": request.url.path},
                    at=datetime.now(timezone.utc),
                )
                await session.commit()
            raise
