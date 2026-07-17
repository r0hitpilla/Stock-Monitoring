from datetime import datetime, timezone

import pytest

from app.domain.entities import DetectionEvent, NotificationChannel, NotificationContext, Snapshot
from app.domain.enums import Availability, EventType, NotificationChannelType
from app.infrastructure.notifications.discord import DiscordSender


class FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class FakeHttpClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def post(self, url: str, json: dict):
        self.calls.append((url, json))
        return FakeResponse(204)


@pytest.mark.asyncio
async def test_discord_sender_posts_content_to_webhook_url():
    http_client = FakeHttpClient()
    sender = DiscordSender(http_client)
    channel = NotificationChannel(
        id=2, user_id=10, type=NotificationChannelType.DISCORD,
        config={"webhook_url": "https://discord.com/api/webhooks/abc/xyz"}, is_verified=True,
    )
    snapshot = Snapshot(
        id=1, watch_target_id=7, timestamp=datetime.now(timezone.utc),
        availability=Availability.AVAILABLE, price=29.0, mrp=32.0, discount_pct=9.4,
        eta_minutes=10, store_name="Blinkit Koramangala", image_url=None,
        quantity_label="500 ml", variants=["500 ml"], product_url="https://blinkit.com/prn/milk/123",
    )
    context = NotificationContext(
        keyword="milk", retailer_slug="blinkit", event_type=EventType.STOCK_AVAILABLE, snapshot=snapshot
    )
    event = DetectionEvent(
        id=1, watch_target_id=7, snapshot_id=1, previous_snapshot_id=None,
        event_type=EventType.STOCK_AVAILABLE, created_at=datetime.now(timezone.utc),
    )

    result = await sender.send(channel, event, context)

    assert result is True
    url, payload = http_client.calls[0]
    assert url == "https://discord.com/api/webhooks/abc/xyz"
    assert "content" in payload
