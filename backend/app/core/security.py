"""Security primitives for OTP code generation, hashing, and verification."""

import hashlib
import hmac
import secrets


def generate_otp_code() -> str:
    """Generate a cryptographically random 6-digit OTP code."""
    return f"{secrets.randbelow(1000000):06d}"


def hash_otp_code(code: str) -> str:
    """Hash an OTP code for storage at rest."""
    return hashlib.sha256(code.encode()).hexdigest()


def verify_otp_code(code: str, code_hash: str) -> bool:
    """Verify an OTP code against its stored hash using constant-time comparison."""
    return hmac.compare_digest(hash_otp_code(code), code_hash)
