"""Authentication router for OTP request/verify and token refresh endpoints."""

from fastapi import APIRouter, Depends, status

from app.api.deps import get_auth_service
from app.api.schemas.auth import (
    OtpRequestSchema,
    OtpVerifySchema,
    RefreshRequestSchema,
    TokenPairSchema,
)
from app.application.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/otp/request", status_code=status.HTTP_202_ACCEPTED)
async def request_otp(
    body: OtpRequestSchema, auth_service: AuthService = Depends(get_auth_service)
) -> None:
    """Request an OTP for phone number verification.

    Args:
        body: Request body containing the phone number.
        auth_service: Injected AuthService dependency.

    Raises:
        RateLimitExceededError: If the hourly OTP request cap is exceeded (429).
    """
    await auth_service.request_otp(body.phone_number)


@router.post("/otp/verify", response_model=TokenPairSchema)
async def verify_otp(
    body: OtpVerifySchema, auth_service: AuthService = Depends(get_auth_service)
) -> TokenPairSchema:
    """Verify an OTP code and return an access/refresh token pair.

    Args:
        body: Request body containing phone number and OTP code.
        auth_service: Injected AuthService dependency.

    Returns:
        TokenPairSchema with access and refresh tokens.

    Raises:
        InvalidOtpError: If the OTP code is invalid, expired, or exhausted (400).
    """
    tokens = await auth_service.verify_otp(body.phone_number, body.code)
    return TokenPairSchema(
        access_token=tokens.access_token, refresh_token=tokens.refresh_token
    )


@router.post("/refresh", response_model=TokenPairSchema)
async def refresh(
    body: RefreshRequestSchema, auth_service: AuthService = Depends(get_auth_service)
) -> TokenPairSchema:
    """Issue a new token pair from a valid refresh token.

    Args:
        body: Request body containing the refresh token.
        auth_service: Injected AuthService dependency.

    Returns:
        TokenPairSchema with new access and refresh tokens.

    Raises:
        InvalidTokenError: If the refresh token is invalid or expired (401).
    """
    tokens = auth_service.refresh(body.refresh_token)
    return TokenPairSchema(
        access_token=tokens.access_token, refresh_token=tokens.refresh_token
    )
