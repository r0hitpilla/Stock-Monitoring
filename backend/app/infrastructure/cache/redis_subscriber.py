"""Redis-based event subscriber adapter (consumer side of RedisEventPublisher)."""

import json
from typing import Any, AsyncIterator, Protocol


class PubSubLike(Protocol):
    """Protocol for Redis-like pub/sub objects."""

    async def subscribe(self, *channels: str) -> None:
        """Subscribe to one or more channels."""
        ...

    async def unsubscribe(self, *channels: str) -> None:
        """Unsubscribe from one or more channels."""
        ...

    async def get_message(
        self, ignore_subscribe_messages: bool = True, timeout: float | None = None
    ) -> dict[str, Any] | None:
        """Fetch the next pub/sub message, or None if none is available."""
        ...

    async def close(self) -> None:
        """Close the pub/sub connection."""
        ...


class RedisClientLike(Protocol):
    """Protocol for Redis-like clients exposing a pub/sub interface."""

    def pubsub(self) -> PubSubLike:
        """Return a new pub/sub object bound to this client."""
        ...


class RedisSubscriber:
    """Subscribes to Redis pub/sub channels and yields decoded JSON messages."""

    def __init__(self, redis_client: RedisClientLike) -> None:
        """Initialize with a Redis-like client.

        Args:
            redis_client: Any object exposing `.pubsub()` (matches `redis.asyncio.Redis`).
        """
        self._redis_client = redis_client

    async def listen(self, channels: list[str]) -> AsyncIterator[dict[str, Any]]:
        """Subscribe to the given channels and yield each message's decoded JSON data.

        This is an infinite generator by design: it yields messages forever until
        the caller breaks out of the loop or calls `.aclose()` on the generator,
        at which point the `finally` block unsubscribes and closes the pub/sub
        connection.

        Args:
            channels: The channel names to subscribe to.

        Yields:
            The JSON-decoded `data` field of each received message.
        """
        pubsub = self._redis_client.pubsub()
        await pubsub.subscribe(*channels)
        try:
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message is not None and message.get("type") == "message":
                    yield json.loads(message["data"])
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.close()
