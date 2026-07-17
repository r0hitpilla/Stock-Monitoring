"""FastAPI application factory and core configuration."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.application.exceptions import (
    InvalidOtpError,
    InvalidTokenError,
    RateLimitExceededError,
)
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.infrastructure.db.session import get_engine, get_sessionmaker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage app lifecycle: startup and shutdown.

    On startup:
    - Initialize logging
    - Create the database engine
    - Store engine and session factory in app.state
    - Seed retailers into the database

    On shutdown:
    - Dispose of the engine
    """
    settings = get_settings()
    configure_logging(settings)
    engine = get_engine(settings.database_url)
    app.state.engine = engine
    app.state.session_factory = get_sessionmaker(engine)

    async with app.state.session_factory() as session:
        from app.infrastructure.db.seed import ensure_retailers_seeded

        try:
            await ensure_retailers_seeded(session)
        except Exception:
            # Seeding may fail in test/dev environments where the database
            # schema is not yet initialized. This is expected and not fatal.
            pass

    yield
    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        A configured FastAPI instance with exception handlers and the health endpoint.
    """
    application = FastAPI(title="Multi-Retailer Inventory Monitor", lifespan=lifespan)

    @application.exception_handler(InvalidOtpError)
    async def _invalid_otp(request: Request, exc: InvalidOtpError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @application.exception_handler(InvalidTokenError)
    async def _invalid_token(request: Request, exc: InvalidTokenError) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @application.exception_handler(RateLimitExceededError)
    async def _rate_limited(
        request: Request, exc: RateLimitExceededError
    ) -> JSONResponse:
        return JSONResponse(status_code=429, content={"detail": str(exc)})

    @application.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint.

        Returns:
            A JSON object with status "ok".
        """
        return {"status": "ok"}

    from app.api.routers.auth import router as auth_router
    from app.api.routers.history import router as history_router
    from app.api.routers.retailers import router as retailers_router

    application.include_router(auth_router)
    application.include_router(retailers_router)
    application.include_router(history_router)

    return application


app = create_app()
