"""Local-development OTP delivery via structured logging."""

import structlog

from app.domain.ports.otp import OtpProvider

logger = structlog.get_logger(__name__)


class ConsoleOtpProvider(OtpProvider):
    """Local-dev OTP delivery: logs the code instead of sending a real SMS."""

    async def send_otp(self, phone_number: str, code: str) -> None:
        """Log the OTP code instead of sending a real SMS."""
        logger.info("otp_code_generated", phone_number=phone_number, code=code)
