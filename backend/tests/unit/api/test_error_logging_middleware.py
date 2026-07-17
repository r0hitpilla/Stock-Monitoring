"""Regression test for ErrorLoggingMiddleware logging and exception re-raising."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select

from app.api.error_logging_middleware import ErrorLoggingMiddleware
from app.infrastructure.db.models import Base, SystemLogModel
from app.infrastructure.db.session import get_sessionmaker


@asynccontextmanager
async def _build_test_app_with_db():
    """Build a test app with an in-memory SQLite database.

    The database is created fresh for each test and all tables are initialized.
    The app.state.session_factory is set to a working async sessionmaker.

    Yields:
        A configured FastAPI app with the ErrorLoggingMiddleware and a
        test-specific session factory.
    """
    # Create an in-memory SQLite engine
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Build the app
    app = FastAPI()

    # Install the middleware
    app.add_middleware(ErrorLoggingMiddleware)

    # Set the session factory on app.state
    app.state.session_factory = get_sessionmaker(engine)

    # Add a test route that raises an exception
    @app.get("/test-error")
    async def test_error_route():
        raise ValueError("test error message")

    try:
        yield app
    finally:
        # Cleanup
        await engine.dispose()


async def test_middleware_logs_unhandled_exception_to_database():
    """Verify ErrorLoggingMiddleware logs exceptions and re-raises them.

    This test ensures that:
    1. When an unhandled exception occurs in a request handler,
       the middleware catches it.
    2. The middleware writes a SystemLogModel entry with level="error",
       the exception message, and the request path.
    3. The exception is re-raised, so it propagates to the client
       (resulting in a 500 response).
    """
    async with _build_test_app_with_db() as app:
        client = TestClient(app, raise_server_exceptions=False)

        # Call the endpoint that raises an exception
        response = client.get("/test-error")

        # Verify the exception propagated (500 status)
        assert response.status_code == 500

        # Query the database to verify the SystemLogModel entry was created
        async with app.state.session_factory() as session:
            stmt = select(SystemLogModel).where(
                SystemLogModel.level == "error",
                SystemLogModel.message == "test error message",
            )
            log_entry = (await session.execute(stmt)).scalar_one_or_none()

        # Verify the log entry exists
        assert log_entry is not None, "No SystemLogModel entry found in database"
        assert log_entry.level == "error"
        assert log_entry.message == "test error message"
        assert log_entry.context == {"path": "/test-error"}
        assert log_entry.created_at is not None
        assert isinstance(log_entry.created_at, datetime)
