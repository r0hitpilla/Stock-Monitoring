from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.domain.entities import ProviderProductResult
from app.domain.enums import Availability, EventType
from app.infrastructure.db.models import Base
from app.infrastructure.db.repositories import (
    SqlAlchemyDetectionEventRepository,
    SqlAlchemySnapshotRepository,
    SqlAlchemyWatchTargetRepository,
)
from app.infrastructure.db.session import get_engine, get_sessionmaker


@pytest.fixture
async def session_factory():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield get_sessionmaker(engine)
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_or_create_is_idempotent_and_list_due_finds_new_targets(
    session_factory: async_sessionmaker,
):
    async with session_factory() as session:
        repo = SqlAlchemyWatchTargetRepository(session)

        first = await repo.get_or_create("blinkit", "Bengaluru", "560001", "milk", 300)
        second = await repo.get_or_create("blinkit", "Bengaluru", "560001", "milk", 300)
        await session.commit()

        assert first.id == second.id

        due = await repo.list_due(datetime.now(timezone.utc))
        assert any(t.id == first.id for t in due)


@pytest.mark.asyncio
async def test_snapshot_and_detection_event_repositories_roundtrip(
    session_factory: async_sessionmaker,
):
    async with session_factory() as session:
        watch_target_repo = SqlAlchemyWatchTargetRepository(session)
        snapshot_repo = SqlAlchemySnapshotRepository(session)
        event_repo = SqlAlchemyDetectionEventRepository(session)

        target = await watch_target_repo.get_or_create(
            "blinkit", "Bengaluru", "560001", "milk", 300
        )
        await session.commit()

        assert await snapshot_repo.get_latest(target.id) is None

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
            product_url="https://blinkit.com/prn/milk/123",
            scraped_at=datetime.now(timezone.utc),
        )
        snapshot = await snapshot_repo.create(target.id, result)
        await session.commit()

        latest = await snapshot_repo.get_latest(target.id)
        assert latest is not None
        assert latest.price == 29.0

        event = await event_repo.create(
            target.id,
            snapshot.id,
            None,
            EventType.STOCK_AVAILABLE,
            datetime.now(timezone.utc),
        )
        await session.commit()

        events = await event_repo.list_for_watch_target(target.id)
        assert events[0].id == event.id
