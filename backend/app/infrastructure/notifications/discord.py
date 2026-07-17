"""Discord notification sender adapter."""

from app.domain.entities import DetectionEvent, NotificationChannel, NotificationContext
from app.domain.enums import NotificationChannelType
from app.domain.ports.notification import NotificationSender
from app.infrastructure.notifications.formatting import format_message
from app.infrastructure.notifications.telegram import HttpClientLike


class DiscordSender(NotificationSender):
    """Notification sender for Discord via webhook."""

    channel_type = NotificationChannelType.DISCORD

    def __init__(self, http_client: HttpClientLike) -> None:
        """Initialize Discord sender.

        Args:
            http_client: HTTP client for making requests.
        """
        self._http_client = http_client

    async def send(
        self, channel: NotificationChannel, event: DetectionEvent, context: NotificationContext
    ) -> bool:
        """Send notification via Discord.

        Args:
            channel: The notification channel configuration.
            event: The detection event.
            context: The notification context.

        Returns:
            True if sent successfully, False otherwise.
        """
        webhook_url = channel.config.get("webhook_url")
        if not webhook_url:
            return False
        response = await self._http_client.post(webhook_url, json={"content": format_message(context)})
        return response.status_code in (200, 204)
