from datetime import datetime, timezone

import pytest

from app.domain.entities import DetectionEvent, NotificationChannel, NotificationContext, Snapshot
from app.domain.enums import Availability, EventType, NotificationChannelType
from app.infrastructure.notifications.telegram import TelegramSender


class FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class FakeHttpClient:
    def __init__(self, status_code: int = 200) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._status_code = status_code

    async def post(self, url: str, json: dict):
        self.calls.append((url, json))
        return FakeResponse(self._status_code)


def _context():
    snapshot = Snapshot(
        id=1, watch_target_id=7, timestamp=datetime.now(timezone.utc),
        availability=Availability.AVAILABLE, price=29.0, mrp=32.0, discount_pct=9.4,
        eta_minutes=10, store_name="Blinkit Koramangala", image_url=None,
        quantity_label="500 ml", variants=["500 ml"], product_url="https://blinkit.com/prn/milk/123",
    )
    return NotificationContext(
        keyword="milk", retailer_slug="blinkit", event_type=EventType.STOCK_AVAILABLE, snapshot=snapshot
    )


def _event():
    return DetectionEvent(
        id=1, watch_target_id=7, snapshot_id=1, previous_snapshot_id=None,
        event_type=EventType.STOCK_AVAILABLE, created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_telegram_sender_posts_to_bot_api_with_chat_id():
    http_client = FakeHttpClient()
    sender = TelegramSender(http_client, bot_token="TEST_TOKEN")
    channel = NotificationChannel(
        id=1, user_id=10, type=NotificationChannelType.TELEGRAM,
        config={"chat_id": "123456"}, is_verified=True,
    )

    result = await sender.send(channel, _event(), _context())

    assert result is True
    url, payload = http_client.calls[0]
    assert url == "https://api.telegram.org/botTEST_TOKEN/sendMessage"
    assert payload["chat_id"] == "123456"


@pytest.mark.asyncio
async def test_telegram_sender_returns_false_when_chat_id_missing():
    http_client = FakeHttpClient()
    sender = TelegramSender(http_client, bot_token="TEST_TOKEN")
    channel = NotificationChannel(
        id=1, user_id=10, type=NotificationChannelType.TELEGRAM, config={}, is_verified=False
    )

    result = await sender.send(channel, _event(), _context())

    assert result is False
    assert http_client.calls == []
