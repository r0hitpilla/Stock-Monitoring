from datetime import datetime, timezone

import pytest

from app.application.notification_service import NotificationService
from app.domain.entities import (
    DetectionEvent,
    NotificationChannel,
    NotificationContext,
    Snapshot,
    Watch,
    WatchTarget,
)
from app.domain.enums import Availability, EventType, NotificationChannelType
from app.domain.ports.notification import NotificationSender


def _watch_target():
    return WatchTarget(
        id=7,
        retailer_slug="blinkit",
        city="Bengaluru",
        pincode="560001",
        keyword="milk",
    )


def _snapshot():
    return Snapshot(
        id=100,
        watch_target_id=7,
        timestamp=datetime.now(timezone.utc),
        availability=Availability.AVAILABLE,
        price=29.0,
        mrp=32.0,
        discount_pct=9.4,
        eta_minutes=10,
        store_name="Blinkit Koramangala",
        image_url=None,
        quantity_label="500 ml",
        variants=["500 ml"],
        product_url="https://blinkit.com/prn/milk/123",
    )


def _event():
    return DetectionEvent(
        id=42,
        watch_target_id=7,
        snapshot_id=100,
        previous_snapshot_id=None,
        event_type=EventType.STOCK_AVAILABLE,
        created_at=datetime.now(timezone.utc),
    )


class FakeWatchTargetRepo:
    async def get_by_id(self, watch_target_id: int):
        return _watch_target()


class FakeSnapshotRepo:
    async def get_by_id(self, snapshot_id: int):
        return _snapshot()


class FakeDetectionEventRepo:
    async def get_by_id(self, event_id: int):
        return _event()


class FakeWatchRepo:
    def __init__(self, watches: list[Watch]) -> None:
        self._watches = watches

    async def list_by_watch_target(self, watch_target_id: int):
        return self._watches


class FakeChannelRepo:
    def __init__(self, channels_by_user: dict[int, list[NotificationChannel]]) -> None:
        self._channels_by_user = channels_by_user

    async def list_for_user(self, user_id: int):
        return self._channels_by_user.get(user_id, [])


class FakeNotificationLogRepo:
    def __init__(self, recent_keys: set[str] | None = None) -> None:
        self._recent_keys = recent_keys or set()
        self.created: list[dict] = []

    async def exists_recent(self, dedup_key: str, cooldown_seconds: int) -> bool:
        return dedup_key in self._recent_keys

    async def create(self, user_id, detection_event_id, channel_id, status, dedup_key):
        self.created.append(
            {
                "user_id": user_id,
                "channel_id": channel_id,
                "status": status,
                "dedup_key": dedup_key,
            }
        )


class FakeSender(NotificationSender):
    channel_type = NotificationChannelType.TELEGRAM

    def __init__(self) -> None:
        self.sent_to: list[NotificationChannel] = []

    async def send(self, channel, event, context: NotificationContext) -> bool:
        self.sent_to.append(channel)
        return True


@pytest.mark.asyncio
async def test_process_event_sends_to_every_channel_of_every_subscribed_user():
    watches = [
        Watch(id=1, user_id=10, product_id=1, watch_target_id=7, interval_seconds=300)
    ]
    channel = NotificationChannel(
        id=1,
        user_id=10,
        type=NotificationChannelType.TELEGRAM,
        config={},
        is_verified=True,
    )
    sender = FakeSender()
    log_repo = FakeNotificationLogRepo()

    service = NotificationService(
        watch_target_repo=FakeWatchTargetRepo(),
        snapshot_repo=FakeSnapshotRepo(),
        event_repo=FakeDetectionEventRepo(),
        watch_repo=FakeWatchRepo(watches),
        channel_repo=FakeChannelRepo({10: [channel]}),
        notification_log_repo=log_repo,
        senders={NotificationChannelType.TELEGRAM: sender},
    )

    await service.process_event(42)

    assert sender.sent_to == [channel]
    assert log_repo.created == [
        {
            "user_id": 10,
            "channel_id": 1,
            "status": "sent",
            "dedup_key": "10:7:stock_available",
        }
    ]


@pytest.mark.asyncio
async def test_process_event_skips_user_within_cooldown():
    watches = [
        Watch(id=1, user_id=10, product_id=1, watch_target_id=7, interval_seconds=300)
    ]
    channel = NotificationChannel(
        id=1,
        user_id=10,
        type=NotificationChannelType.TELEGRAM,
        config={},
        is_verified=True,
    )
    sender = FakeSender()
    log_repo = FakeNotificationLogRepo(recent_keys={"10:7:stock_available"})

    service = NotificationService(
        watch_target_repo=FakeWatchTargetRepo(),
        snapshot_repo=FakeSnapshotRepo(),
        event_repo=FakeDetectionEventRepo(),
        watch_repo=FakeWatchRepo(watches),
        channel_repo=FakeChannelRepo({10: [channel]}),
        notification_log_repo=log_repo,
        senders={NotificationChannelType.TELEGRAM: sender},
    )

    await service.process_event(42)

    assert sender.sent_to == []
    assert log_repo.created == []
