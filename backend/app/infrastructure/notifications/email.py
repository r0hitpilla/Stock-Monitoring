"""Email notification sender adapter."""

import asyncio
import smtplib
from email.message import EmailMessage

from app.domain.entities import DetectionEvent, NotificationChannel, NotificationContext
from app.domain.enums import NotificationChannelType
from app.domain.ports.notification import NotificationSender
from app.infrastructure.notifications.formatting import format_message


class EmailSender(NotificationSender):
    """Notification sender for Email via SMTP."""

    channel_type = NotificationChannelType.EMAIL

    def __init__(
        self, smtp_host: str, smtp_port: int, smtp_username: str, smtp_password: str, from_address: str
    ) -> None:
        """Initialize Email sender.

        Args:
            smtp_host: SMTP server hostname.
            smtp_port: SMTP server port.
            smtp_username: SMTP authentication username.
            smtp_password: SMTP authentication password.
            from_address: Email address to send from.
        """
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_username = smtp_username
        self._smtp_password = smtp_password
        self._from_address = from_address

    async def send(
        self, channel: NotificationChannel, event: DetectionEvent, context: NotificationContext
    ) -> bool:
        """Send notification via Email.

        Args:
            channel: The notification channel configuration.
            event: The detection event.
            context: The notification context.

        Returns:
            True if sent successfully, False otherwise.
        """
        to_address = channel.config.get("email")
        if not to_address:
            return False
        return await asyncio.to_thread(self._send_sync, to_address, context)

    def _send_sync(self, to_address: str, context: NotificationContext) -> bool:
        """Send email synchronously.

        Args:
            to_address: Email address to send to.
            context: The notification context.

        Returns:
            True if sent successfully, False otherwise.
        """
        message = EmailMessage()
        message["Subject"] = f"{context.keyword} update"
        message["From"] = self._from_address
        message["To"] = to_address
        message.set_content(format_message(context))
        try:
            with smtplib.SMTP(self._smtp_host, self._smtp_port) as smtp:
                smtp.starttls()
                smtp.login(self._smtp_username, self._smtp_password)
                smtp.send_message(message)
            return True
        except OSError:
            return False
