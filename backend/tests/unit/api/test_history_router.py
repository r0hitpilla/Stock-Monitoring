from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.api.routers.history import (
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

    async def get_by_id(self, watch_id: int) -> Watch | None:
        return self._watch


class FakeDetectionEventRepo:
    async def list_for_watch_target(
        self, watch_target_id: int, limit: int = 50
    ) -> list[DetectionEvent]:
        return [
            DetectionEvent(
                id=1,
                watch_target_id=watch_target_id,
                snapshot_id=100,
                previous_snapshot_id=None,
                event_type=EventType.STOCK_AVAILABLE,
                created_at=datetime.now(timezone.utc),
            )
        ]


class FakeSnapshotRepo:
    async def get_by_id(self, snapshot_id: int) -> Snapshot | None:
        return Snapshot(
            id=snapshot_id,
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


def _build_app(watch: Watch | None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user_id] = lambda: 10
    app.dependency_overrides[get_watch_repository] = lambda: FakeWatchRepo(watch)
    app.dependency_overrides[get_detection_event_repository] = lambda: FakeDetectionEventRepo()
    app.dependency_overrides[get_snapshot_repository] = lambda: FakeSnapshotRepo()
    return app


def test_history_returns_events_for_owned_watch() -> None:
    watch = Watch(id=5, user_id=10, product_id=1, watch_target_id=7, interval_seconds=300)
    client = TestClient(_build_app(watch))

    response = client.get("/api/v1/history", params={"watch_id": 5})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["event_type"] == "stock_available"
    assert body[0]["snapshot"]["price"] == 29.0


def test_history_returns_404_for_watch_owned_by_someone_else() -> None:
    watch = Watch(id=5, user_id=999, product_id=1, watch_target_id=7, interval_seconds=300)
    client = TestClient(_build_app(watch))

    response = client.get("/api/v1/history", params={"watch_id": 5})

    assert response.status_code == 404


def test_history_returns_404_for_missing_watch() -> None:
    client = TestClient(_build_app(None))

    response = client.get("/api/v1/history", params={"watch_id": 999})

    assert response.status_code == 404
