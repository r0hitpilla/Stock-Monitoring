"""Abstract notification sender interface."""

from abc import ABC, abstractmethod
from typing import ClassVar

from app.domain.entities import DetectionEvent, NotificationChannel, NotificationContext
from app.domain.enums import NotificationChannelType


class NotificationSender(ABC):
    """Abstract base class for notification senders."""

    channel_type: ClassVar[NotificationChannelType]

    @abstractmethod
    async def send(
        self,
        channel: NotificationChannel,
        event: DetectionEvent,
        context: NotificationContext,
    ) -> bool:
        """Send a notification through a channel.

        Args:
            channel: The notification channel to send through.
            event: The detection event that triggered the notification.
            context: The notification context with message details.

        Returns:
            True if the notification was sent successfully, False otherwise.
        """
        ...
