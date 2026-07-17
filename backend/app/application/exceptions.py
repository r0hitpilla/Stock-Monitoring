"""Exceptions raised by application-layer services."""


class RateLimitExceededError(Exception):
    """Raised when a caller exceeds an allowed rate of requests."""


class InvalidOtpError(Exception):
    """Raised when an OTP code is missing, wrong, expired, or exhausted."""


class InvalidTokenError(Exception):
    """Raised when a JWT token is invalid, expired, or of the wrong type."""
