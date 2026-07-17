from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.api.routers.analytics import (
    get_detection_event_repository,
    get_snapshot_repository,
    get_watch_repository,
    router,
)
from app.domain.entities import DetectionEvent, Snapshot, Watch
from app.domain.enums import Availability, EventType


class FakeWatchRepo:
    def __init__(self, watch: Watch | None) -> None:
        self._watch = watch

    async def get_by_id(self, watch_id: int):
        return self._watch


class FakeSnapshotRepo:
    async def list_since(self, watch_target_id: int, since: datetime):
        return [
            Snapshot(
                id=1,
                watch_target_id=watch_target_id,
                timestamp=datetime.now(timezone.utc),
                availability=Availability.AVAILABLE,
                price=29.0,
                mrp=32.0,
                discount_pct=9.4,
                eta_minutes=10,
                store_name="Blinkit Koramangala",
                image_url=None,
                quantity_label="500 ml",
                variants=[],
                product_url=None,
            )
        ]


class FakeDetectionEventRepo:
    async def list_for_watch_target(
        self, watch_target_id: int, limit: int = 50, since: datetime | None = None
    ):
        return []


class WindowScopedFakeDetectionEventRepo:
    """Fake that mimics a real repository's `since` filtering behavior.

    Used to assert the router actually passes a `since` bound down to the
    repository, instead of silently ignoring the requested `days` window.
    """

    def __init__(self, events: list[DetectionEvent]) -> None:
        self._events = events

    async def list_for_watch_target(
        self, watch_target_id: int, limit: int = 50, since: datetime | None = None
    ):
        events = [e for e in self._events if e.watch_target_id == watch_target_id]
        if since is not None:
            events = [e for e in events if e.created_at >= since]
        return events


def _build_app(watch: Watch | None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user_id] = lambda: 10
    app.dependency_overrides[get_watch_repository] = lambda: FakeWatchRepo(watch)
    app.dependency_overrides[get_snapshot_repository] = lambda: FakeSnapshotRepo()
    app.dependency_overrides[get_detection_event_repository] = (
        lambda: FakeDetectionEventRepo()
    )
    return app


def test_price_history_returns_points_for_owned_watch():
    watch = Watch(
        id=5, user_id=10, product_id=1, watch_target_id=7, interval_seconds=300
    )
    client = TestClient(_build_app(watch))

    response = client.get("/api/v1/analytics/price-history", params={"watch_id": 5})

    assert response.status_code == 200
    assert response.json()[0]["price"] == 29.0


def test_availability_summary_returns_404_for_unowned_watch():
    watch = Watch(
        id=5, user_id=999, product_id=1, watch_target_id=7, interval_seconds=300
    )
    client = TestClient(_build_app(watch))

    response = client.get("/api/v1/analytics/availability", params={"watch_id": 5})

    assert response.status_code == 404


def test_availability_summary_excludes_events_before_requested_window():
    watch = Watch(
        id=5, user_id=10, product_id=1, watch_target_id=7, interval_seconds=300
    )
    now = datetime.now(timezone.utc)
    old_restock = DetectionEvent(
        id=1,
        watch_target_id=7,
        snapshot_id=1,
        previous_snapshot_id=None,
        event_type=EventType.STOCK_AVAILABLE,
        created_at=now - timedelta(days=40),
    )
    recent_restock = DetectionEvent(
        id=2,
        watch_target_id=7,
        snapshot_id=2,
        previous_snapshot_id=None,
        event_type=EventType.STOCK_AVAILABLE,
        created_at=now - timedelta(days=1),
    )
    app = _build_app(watch)
    app.dependency_overrides[get_detection_event_repository] = (
        lambda: WindowScopedFakeDetectionEventRepo([old_restock, recent_restock])
    )
    client = TestClient(app)

    response = client.get(
        "/api/v1/analytics/availability", params={"watch_id": 5, "days": 30}
    )

    assert response.status_code == 200
    # Only recent_restock (1 day ago) falls within the 30-day window; old_restock
    # (40 days ago) must not be counted.
    assert response.json()["restock_count"] == 1
