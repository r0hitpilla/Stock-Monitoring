"""Redis-based event publisher adapter."""

import json
from typing import Protocol

from app.domain.entities import DetectionEvent
from app.domain.ports.messaging import EventPublisher


class RedisLike(Protocol):
    """Protocol for Redis-like clients with async publish capability."""

    async def publish(self, channel: str, message: str) -> int:
        """Publish a message to a channel.

        Args:
            channel: The channel name.
            message: The message string.

        Returns:
            The number of subscribers that received the message.
        """
        ...


class RedisEventPublisher(EventPublisher):
    """Publishes detection events to Redis pub/sub channels."""

    def __init__(self, redis_client: RedisLike) -> None:
        """Initialize with a Redis-like client.

        Args:
            redis_client: Any object exposing async publish(channel, message).
        """
        self._redis = redis_client

    async def publish(self, watch_target_id: int, event: DetectionEvent) -> None:
        """Publish a detection event to a watch-target-specific channel.

        Args:
            watch_target_id: The watch target ID.
            event: The detection event to publish.
        """
        payload = {
            "event_id": event.id,
            "watch_target_id": watch_target_id,
            "event_type": event.event_type.value,
            "snapshot_id": event.snapshot_id,
            "created_at": event.created_at.isoformat(),
        }
        await self._redis.publish(f"events:{watch_target_id}", json.dumps(payload))
