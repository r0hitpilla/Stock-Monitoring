from datetime import datetime, timezone

import pytest

from app.application.monitoring_service import MonitoringService
from app.domain.entities import LocationContext, ProviderProductResult, WatchTarget
from app.domain.enums import Availability, EventType
from app.domain.ports.provider import BaseRetailProvider


class FakeProvider(BaseRetailProvider):
    slug = "blinkit"

    def __init__(self, result: ProviderProductResult) -> None:
        self._result = result
        self.initialized_with: LocationContext | None = None

    async def initialize(self, location: LocationContext) -> None:
        self.initialized_with = location

    async def search_product(self, keyword: str) -> list[ProviderProductResult]:
        return [self._result]

    async def get_product(self, product_url: str) -> ProviderProductResult:
        return self._result

    async def check_availability(self, product_url: str) -> Availability:
        return self._result.availability

    async def extract_price(self, page):
        return (self._result.price, self._result.mrp, self._result.discount_pct)

    async def extract_eta(self, page):
        return self._result.eta_minutes

    async def extract_store(self, page):
        return self._result.store_name

    async def extract_image(self, page):
        return self._result.image_url

    async def extract_quantity(self, page):
        return self._result.quantity_label

    async def extract_variants(self, page):
        return self._result.variants

    async def health_check(self) -> bool:
        return True


class FakeProviderRegistry:
    def __init__(self, provider: BaseRetailProvider) -> None:
        self._provider = provider

    def get(self, retailer_slug: str) -> BaseRetailProvider:
        return self._provider

    def list_active_slugs(self) -> list[str]:
        return [self._provider.slug]


class FakeWatchTargetRepo:
    def __init__(self) -> None:
        self.checked_at: dict[int, datetime] = {}

    async def get_or_create(self, *args, **kwargs):
        raise NotImplementedError

    async def list_due(self, now):
        raise NotImplementedError

    async def mark_checked(self, watch_target_id: int, when: datetime) -> None:
        self.checked_at[watch_target_id] = when


class FakeSnapshotRepo:
    def __init__(self, latest=None) -> None:
        self._latest = latest
        self.created = []

    async def get_latest(self, watch_target_id: int):
        return self._latest

    async def create(self, watch_target_id: int, result: ProviderProductResult):
        from app.domain.entities import Snapshot

        snapshot = Snapshot(
            id=len(self.created) + 1,
            watch_target_id=watch_target_id,
            timestamp=result.scraped_at,
            availability=result.availability,
            price=result.price,
            mrp=result.mrp,
            discount_pct=result.discount_pct,
            eta_minutes=result.eta_minutes,
            store_name=result.store_name,
            image_url=result.image_url,
            quantity_label=result.quantity_label,
            variants=result.variants,
            product_url=result.product_url,
        )
        self.created.append(snapshot)
        return snapshot


class FakeDetectionEventRepo:
    def __init__(self) -> None:
        self.created = []

    async def create(
        self, watch_target_id, snapshot_id, previous_snapshot_id, event_type, when
    ):
        from app.domain.entities import DetectionEvent

        event = DetectionEvent(
            id=len(self.created) + 1,
            watch_target_id=watch_target_id,
            snapshot_id=snapshot_id,
            previous_snapshot_id=previous_snapshot_id,
            event_type=event_type,
            created_at=when,
        )
        self.created.append(event)
        return event

    async def list_for_watch_target(self, watch_target_id, limit=50):
        return self.created


class FakeEventPublisher:
    def __init__(self) -> None:
        self.published = []

    async def publish(self, watch_target_id, event):
        self.published.append((watch_target_id, event))


class FakeTaskDispatcher:
    def __init__(self) -> None:
        self.dispatched = []

    def dispatch_detection_event(self, event_id: int) -> None:
        self.dispatched.append(event_id)


@pytest.mark.asyncio
async def test_check_watch_target_persists_snapshot_and_publishes_event_on_restock():
    result = ProviderProductResult(
        retailer_slug="blinkit",
        keyword="milk",
        product_name="Amul Milk 500ml",
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
        scraped_at=datetime.now(timezone.utc),
    )
    provider = FakeProvider(result)
    watch_target_repo = FakeWatchTargetRepo()
    snapshot_repo = FakeSnapshotRepo(latest=None)
    event_repo = FakeDetectionEventRepo()
    publisher = FakeEventPublisher()
    dispatcher = FakeTaskDispatcher()

    service = MonitoringService(
        provider_registry=FakeProviderRegistry(provider),
        watch_target_repo=watch_target_repo,
        snapshot_repo=snapshot_repo,
        event_repo=event_repo,
        event_publisher=publisher,
        task_dispatcher=dispatcher,
    )

    watch_target = WatchTarget(
        id=1,
        retailer_slug="blinkit",
        city="Bengaluru",
        pincode="560001",
        keyword="milk",
    )

    events = await service.check_watch_target(watch_target)

    assert len(events) == 1
    assert events[0].event_type == EventType.STOCK_AVAILABLE
    assert provider.initialized_with == LocationContext("Bengaluru", "560001")
    assert len(snapshot_repo.created) == 1
    assert len(publisher.published) == 1
    assert dispatcher.dispatched == [events[0].id]
    assert 1 in watch_target_repo.checked_at


@pytest.mark.asyncio
async def test_check_watch_target_marks_checked_but_persists_nothing_when_unchanged():
    result = ProviderProductResult(
        retailer_slug="blinkit",
        keyword="milk",
        product_name="Amul Milk 500ml",
        availability=Availability.OUT_OF_STOCK,
        price=None,
        mrp=None,
        discount_pct=None,
        eta_minutes=None,
        store_name=None,
        image_url=None,
        quantity_label=None,
        variants=[],
        product_url="https://blinkit.com/prn/milk/123",
        scraped_at=datetime.now(timezone.utc),
    )
    provider = FakeProvider(result)
    watch_target_repo = FakeWatchTargetRepo()
    snapshot_repo = FakeSnapshotRepo(latest=None)
    event_repo = FakeDetectionEventRepo()
    publisher = FakeEventPublisher()
    dispatcher = FakeTaskDispatcher()

    service = MonitoringService(
        provider_registry=FakeProviderRegistry(provider),
        watch_target_repo=watch_target_repo,
        snapshot_repo=snapshot_repo,
        event_repo=event_repo,
        event_publisher=publisher,
        task_dispatcher=dispatcher,
    )
    watch_target = WatchTarget(
        id=1,
        retailer_slug="blinkit",
        city="Bengaluru",
        pincode="560001",
        keyword="milk",
    )

    events = await service.check_watch_target(watch_target)

    assert events == []
    assert snapshot_repo.created == []
    assert publisher.published == []
    assert 1 in watch_target_repo.checked_at
