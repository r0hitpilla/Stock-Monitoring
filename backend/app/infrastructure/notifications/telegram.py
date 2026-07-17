"""Telegram notification sender adapter."""

from typing import Protocol

from app.domain.entities import DetectionEvent, NotificationChannel, NotificationContext
from app.domain.enums import NotificationChannelType
from app.domain.ports.notification import NotificationSender
from app.infrastructure.notifications.formatting import format_message


class HttpResponseLike(Protocol):
    """Protocol for HTTP response objects."""

    status_code: int


class HttpClientLike(Protocol):
    """Protocol for HTTP client with async post method."""

    async def post(self, url: str, json: dict) -> HttpResponseLike: ...


class TelegramSender(NotificationSender):
    """Notification sender for Telegram via Bot API."""

    channel_type = NotificationChannelType.TELEGRAM

    def __init__(self, http_client: HttpClientLike, bot_token: str) -> None:
        """Initialize Telegram sender.

        Args:
            http_client: HTTP client for making requests.
            bot_token: Telegram bot token.
        """
        self._http_client = http_client
        self._bot_token = bot_token

    async def send(
        self, channel: NotificationChannel, event: DetectionEvent, context: NotificationContext
    ) -> bool:
        """Send notification via Telegram.

        Args:
            channel: The notification channel configuration.
            event: The detection event.
            context: The notification context.

        Returns:
            True if sent successfully, False otherwise.
        """
        chat_id = channel.config.get("chat_id")
        if not chat_id:
            return False
        response = await self._http_client.post(
            f"https://api.telegram.org/bot{self._bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": format_message(context)},
        )
        return response.status_code == 200
