"""Abstract port for OTP delivery."""

from abc import ABC, abstractmethod


class OtpProvider(ABC):
    """Delivers a one-time-password code to a phone number."""

    @abstractmethod
    async def send_otp(self, phone_number: str, code: str) -> None:
        """Send an OTP code to the given phone number.

        Args:
            phone_number: The recipient's phone number.
            code: The plaintext OTP code to deliver.
        """
        ...
