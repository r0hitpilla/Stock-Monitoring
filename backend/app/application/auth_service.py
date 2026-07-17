"""Phone + OTP authentication service issuing JWT access/refresh tokens."""

from datetime import datetime, timedelta, timezone

import jwt

from app.application.exceptions import (
    InvalidOtpError,
    InvalidTokenError,
    RateLimitExceededError,
)
from app.core.security import generate_otp_code, hash_otp_code, verify_otp_code
from app.domain.entities import TokenPair
from app.domain.ports.otp import OtpProvider
from app.domain.ports.repositories import OtpChallengeRepository, UserRepository


class AuthService:
    """Orchestrates phone+OTP authentication and JWT issuance."""

    def __init__(
        self,
        user_repo: UserRepository,
        otp_repo: OtpChallengeRepository,
        otp_provider: OtpProvider,
        jwt_secret: str,
        jwt_algorithm: str,
        access_token_expire_minutes: int,
        refresh_token_expire_days: int,
        otp_ttl_seconds: int = 300,
        otp_cooldown_seconds: int = 30,
        otp_max_per_hour: int = 5,
        otp_max_attempts: int = 5,
    ) -> None:
        """Initialize the auth service with its dependencies and policy knobs.

        Args:
            user_repo: Repository for user lookup/creation.
            otp_repo: Repository for OTP challenge persistence.
            otp_provider: Delivery mechanism for OTP codes.
            jwt_secret: Secret key used to sign JWTs.
            jwt_algorithm: JWT signing algorithm (e.g. "HS256").
            access_token_expire_minutes: Access token lifetime in minutes.
            refresh_token_expire_days: Refresh token lifetime in days.
            otp_ttl_seconds: How long an OTP challenge remains valid.
            otp_cooldown_seconds: Minimum seconds between OTP requests (reserved
                for future use; not currently enforced independently of the
                hourly cap).
            otp_max_per_hour: Maximum OTP requests allowed per phone per hour.
            otp_max_attempts: Maximum verification attempts allowed per challenge.
        """
        self._user_repo = user_repo
        self._otp_repo = otp_repo
        self._otp_provider = otp_provider
        self._jwt_secret = jwt_secret
        self._jwt_algorithm = jwt_algorithm
        self._access_token_expire_minutes = access_token_expire_minutes
        self._refresh_token_expire_days = refresh_token_expire_days
        self._otp_ttl_seconds = otp_ttl_seconds
        self._otp_cooldown_seconds = otp_cooldown_seconds
        self._otp_max_per_hour = otp_max_per_hour
        self._otp_max_attempts = otp_max_attempts

    async def request_otp(self, phone_number: str) -> None:
        """Generate and send a new OTP challenge for a phone number.

        Args:
            phone_number: The phone number to send the OTP to.

        Raises:
            RateLimitExceededError: If the hourly OTP request cap is exceeded.
        """
        recent_count = await self._otp_repo.count_recent(
            phone_number, window_seconds=3600
        )
        if recent_count >= self._otp_max_per_hour:
            raise RateLimitExceededError(f"Too many OTP requests for {phone_number}")

        now = datetime.now(timezone.utc)
        code = generate_otp_code()
        await self._otp_repo.create(
            phone_number=phone_number,
            code_hash=hash_otp_code(code),
            expires_at=now + timedelta(seconds=self._otp_ttl_seconds),
            created_at=now,
        )
        await self._otp_provider.send_otp(phone_number, code)

    async def verify_otp(self, phone_number: str, code: str) -> TokenPair:
        """Verify an OTP code and issue a token pair on success.

        Args:
            phone_number: The phone number the OTP was requested for.
            code: The plaintext OTP code to verify.

        Returns:
            A `TokenPair` for the (possibly newly created) user.

        Raises:
            InvalidOtpError: If the code is missing, wrong, expired, or exhausted.
        """
        challenge = await self._otp_repo.get_latest(phone_number)
        now = datetime.now(timezone.utc)
        if (
            challenge is None
            or challenge.consumed
            or challenge.expires_at < now
            or challenge.attempt_count >= self._otp_max_attempts
        ):
            raise InvalidOtpError("OTP is invalid, expired, or exhausted")

        assert challenge.id is not None  # persisted challenges always have an id

        if not verify_otp_code(code, challenge.code_hash):
            await self._otp_repo.increment_attempt(challenge.id)
            raise InvalidOtpError("Incorrect OTP code")

        await self._otp_repo.mark_consumed(challenge.id)
        user = await self._user_repo.get_or_create_by_phone(phone_number)
        assert user.id is not None  # persisted users always have an id
        return TokenPair(
            access_token=self._issue_token(
                user.id, timedelta(minutes=self._access_token_expire_minutes), "access"
            ),
            refresh_token=self._issue_token(
                user.id, timedelta(days=self._refresh_token_expire_days), "refresh"
            ),
        )

    def verify_access_token(self, token: str) -> int:
        """Verify an access token and return the encoded user id.

        Args:
            token: The JWT access token.

        Returns:
            The user id encoded in the token.

        Raises:
            InvalidTokenError: If the token is invalid, expired, or not an access token.
        """
        return self._verify_token(token, expected_type="access")

    def refresh(self, refresh_token: str) -> TokenPair:
        """Issue a new token pair from a valid refresh token.

        Args:
            refresh_token: The JWT refresh token.

        Returns:
            A new `TokenPair`.

        Raises:
            InvalidTokenError: If the token is invalid, expired, or not a refresh token.
        """
        user_id = self._verify_token(refresh_token, expected_type="refresh")
        return TokenPair(
            access_token=self._issue_token(
                user_id, timedelta(minutes=self._access_token_expire_minutes), "access"
            ),
            refresh_token=self._issue_token(
                user_id, timedelta(days=self._refresh_token_expire_days), "refresh"
            ),
        )

    def _verify_token(self, token: str, expected_type: str) -> int:
        """Decode and validate a JWT, returning its subject as a user id."""
        try:
            payload = jwt.decode(
                token, self._jwt_secret, algorithms=[self._jwt_algorithm]
            )
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc
        if payload.get("type") != expected_type:
            raise InvalidTokenError(f"Expected a {expected_type} token")
        return int(payload["sub"])

    def _issue_token(
        self, user_id: int, expires_delta: timedelta, token_type: str
    ) -> str:
        """Encode a signed JWT for the given user id, expiry, and token type."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "type": token_type,
            "iat": now,
            "exp": now + expires_delta,
        }
        return jwt.encode(payload, self._jwt_secret, algorithm=self._jwt_algorithm)
