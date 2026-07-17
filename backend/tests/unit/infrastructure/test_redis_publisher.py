import json
from datetime import datetime, timezone

import pytest

from app.domain.entities import DetectionEvent
from app.domain.enums import EventType
from app.infrastructure.cache.redis_publisher import RedisEventPublisher


class FakeRedisClient:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []

    async def publish(self, channel: str, message: str) -> int:
        self.published.append((channel, message))
        return 1


@pytest.mark.asyncio
async def test_publish_sends_json_payload_to_watch_target_channel():
    fake_redis = FakeRedisClient()
    publisher = RedisEventPublisher(fake_redis)
    event = DetectionEvent(
        id=42,
        watch_target_id=7,
        snapshot_id=100,
        previous_snapshot_id=99,
        event_type=EventType.STOCK_AVAILABLE,
        created_at=datetime.now(timezone.utc),
    )

    await publisher.publish(7, event)

    assert len(fake_redis.published) == 1
    channel, message = fake_redis.published[0]
    assert channel == "events:7"
    payload = json.loads(message)
    assert payload["event_id"] == 42
    assert payload["event_type"] == "stock_available"
