"""Dependency injection providers for FastAPI routes."""

from typing import AsyncIterator

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.auth_service import AuthService
from app.application.exceptions import InvalidTokenError
from app.core.config import Settings, get_settings
from app.domain.ports.otp import OtpProvider
from app.infrastructure.db.repositories import (
    SqlAlchemyOtpChallengeRepository,
    SqlAlchemyUserRepository,
)
from app.infrastructure.sms.console_provider import ConsoleOtpProvider


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield an async SQLAlchemy session from the app's session factory.

    Args:
        request: The FastAPI request object containing app.state.session_factory.

    Yields:
        An AsyncSession for database operations.
    """
    async with request.app.state.session_factory() as session:
        yield session


def get_otp_provider(settings: Settings = Depends(get_settings)) -> OtpProvider:
    """Return an OtpProvider instance based on configuration.

    Args:
        settings: Application settings.

    Returns:
        An OtpProvider implementation.

    Raises:
        NotImplementedError: If the configured provider is not recognized.
    """
    if settings.otp_provider == "console":
        return ConsoleOtpProvider()
    raise NotImplementedError(
        f"No OtpProvider adapter registered for '{settings.otp_provider}'. "
        "Implement one against app.domain.ports.otp.OtpProvider and wire it here."
    )


def get_auth_service(
    session: AsyncSession = Depends(get_session),
    otp_provider: OtpProvider = Depends(get_otp_provider),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    """Return an AuthService instance with all dependencies wired.

    Args:
        session: Database session.
        otp_provider: OTP provider implementation.
        settings: Application settings.

    Returns:
        An AuthService ready to handle authentication operations.
    """
    return AuthService(
        user_repo=SqlAlchemyUserRepository(session),
        otp_repo=SqlAlchemyOtpChallengeRepository(session),
        otp_provider=otp_provider,
        jwt_secret=settings.jwt_secret,
        jwt_algorithm=settings.jwt_algorithm,
        access_token_expire_minutes=settings.access_token_expire_minutes,
        refresh_token_expire_days=settings.refresh_token_expire_days,
    )


def get_current_user_id(
    authorization: str | None = Header(None),
    auth_service: AuthService = Depends(get_auth_service),
) -> int:
    """Extract and verify the current user ID from an Authorization header.

    Args:
        authorization: The Authorization header (expects "Bearer <token>").
        auth_service: The authentication service.

    Returns:
        The verified user ID.

    Raises:
        HTTPException: With 401 status if the header is malformed or token is invalid.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.removeprefix("Bearer ")
    try:
        return auth_service.verify_access_token(token)
    except InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
