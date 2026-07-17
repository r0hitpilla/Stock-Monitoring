import json

import pytest

from app.infrastructure.cache.redis_subscriber import RedisSubscriber


class FakePubSub:
    def __init__(self, messages: list[dict]) -> None:
        self._messages = [{"type": "message", "data": json.dumps(m)} for m in messages]
        self.subscribed_channels: list[str] = []
        self.closed = False

    async def subscribe(self, *channels: str) -> None:
        self.subscribed_channels.extend(channels)

    async def unsubscribe(self, *channels: str) -> None:
        pass

    async def get_message(
        self, ignore_subscribe_messages: bool = True, timeout: float | None = None
    ):
        if self._messages:
            return self._messages.pop(0)
        return None

    async def close(self) -> None:
        self.closed = True


class FakeRedisClient:
    def __init__(self, pubsub: FakePubSub) -> None:
        self._pubsub = pubsub

    def pubsub(self):
        return self._pubsub


@pytest.mark.asyncio
async def test_listen_subscribes_and_yields_decoded_messages():
    fake_pubsub = FakePubSub([{"event_id": 1}, {"event_id": 2}])
    subscriber = RedisSubscriber(FakeRedisClient(fake_pubsub))

    gen = subscriber.listen(["events:7"])
    first = await gen.__anext__()
    second = await gen.__anext__()
    await gen.aclose()

    assert first == {"event_id": 1}
    assert second == {"event_id": 2}
    assert fake_pubsub.subscribed_channels == ["events:7"]
