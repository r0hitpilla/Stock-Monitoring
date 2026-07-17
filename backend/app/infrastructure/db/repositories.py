"""SQLAlchemy implementations of repository interfaces."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import (
    DetectionEvent,
    NotificationChannel,
    NotificationLog,
    ProviderProductResult,
    Snapshot,
    Watch,
    WatchTarget,
)
from app.domain.enums import Availability, EventType, NotificationChannelType
from app.domain.ports.repositories import (
    DetectionEventRepository,
    NotificationChannelRepository,
    NotificationLogRepository,
    SnapshotRepository,
    WatchRepository,
    WatchTargetRepository,
)
from app.infrastructure.db.models import (
    DetectionEventModel,
    NotificationChannelModel,
    NotificationLogModel,
    SnapshotModel,
    WatchModel,
    WatchTargetModel,
)


def _to_watch_target(model: WatchTargetModel) -> WatchTarget:
    """Convert a WatchTargetModel to a WatchTarget entity."""
    return WatchTarget(
        id=model.id,
        retailer_slug=model.retailer_slug,
        city=model.city,
        pincode=model.pincode,
        keyword=model.keyword,
        interval_seconds=model.interval_seconds,
    )


class SqlAlchemyWatchTargetRepository(WatchTargetRepository):
    """SQLAlchemy implementation of WatchTargetRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async session.

        Args:
            session: The SQLAlchemy async session.
        """
        self._session = session

    async def get_or_create(
        self,
        retailer_slug: str,
        city: str,
        pincode: str,
        keyword: str,
        interval_seconds: int,
    ) -> WatchTarget:
        """Get or create a watch target."""
        stmt = select(WatchTargetModel).where(
            WatchTargetModel.retailer_slug == retailer_slug,
            WatchTargetModel.city == city,
            WatchTargetModel.pincode == pincode,
            WatchTargetModel.keyword == keyword,
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            if interval_seconds < existing.interval_seconds:
                existing.interval_seconds = interval_seconds
            return _to_watch_target(existing)

        model = WatchTargetModel(
            retailer_slug=retailer_slug,
            city=city,
            pincode=pincode,
            keyword=keyword,
            interval_seconds=interval_seconds,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_watch_target(model)

    async def get_by_id(self, watch_target_id: int) -> WatchTarget | None:
        """Get a watch target by ID."""
        stmt = select(WatchTargetModel).where(WatchTargetModel.id == watch_target_id)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is None:
            return None
        return _to_watch_target(model)

    async def list_due(self, now: datetime) -> list[WatchTarget]:
        """List watch targets that are due for checking."""
        stmt = select(WatchTargetModel)
        models = (await self._session.execute(stmt)).scalars().all()
        due = []
        for model in models:
            if model.last_checked_at is None:
                due.append(model)
                continue
            elapsed = (now - model.last_checked_at).total_seconds()
            if elapsed >= model.interval_seconds:
                due.append(model)
        return [_to_watch_target(m) for m in due]

    async def mark_checked(self, watch_target_id: int, when: datetime) -> None:
        """Mark a watch target as checked."""
        stmt = select(WatchTargetModel).where(WatchTargetModel.id == watch_target_id)
        model = (await self._session.execute(stmt)).scalar_one()
        model.last_checked_at = when


class SqlAlchemySnapshotRepository(SnapshotRepository):
    """SQLAlchemy implementation of SnapshotRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async session.

        Args:
            session: The SQLAlchemy async session.
        """
        self._session = session

    async def get_latest(self, watch_target_id: int) -> Snapshot | None:
        """Get the latest snapshot for a watch target."""
        stmt = (
            select(SnapshotModel)
            .where(SnapshotModel.watch_target_id == watch_target_id)
            .order_by(SnapshotModel.timestamp.desc())
            .limit(1)
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is None:
            return None
        return Snapshot(
            id=model.id,
            watch_target_id=model.watch_target_id,
            timestamp=model.timestamp,
            availability=Availability(model.availability),
            price=model.price,
            mrp=model.mrp,
            discount_pct=model.discount_pct,
            eta_minutes=model.eta_minutes,
            store_name=model.store_name,
            image_url=model.image_url,
            quantity_label=model.quantity_label,
            variants=model.variants,
            product_url=model.product_url,
        )

    async def get_by_id(self, snapshot_id: int) -> Snapshot | None:
        """Get a snapshot by ID."""
        stmt = select(SnapshotModel).where(SnapshotModel.id == snapshot_id)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is None:
            return None
        return Snapshot(
            id=model.id,
            watch_target_id=model.watch_target_id,
            timestamp=model.timestamp,
            availability=Availability(model.availability),
            price=model.price,
            mrp=model.mrp,
            discount_pct=model.discount_pct,
            eta_minutes=model.eta_minutes,
            store_name=model.store_name,
            image_url=model.image_url,
            quantity_label=model.quantity_label,
            variants=model.variants,
            product_url=model.product_url,
        )

    async def create(
        self, watch_target_id: int, result: ProviderProductResult
    ) -> Snapshot:
        """Create a new snapshot from a provider result."""
        model = SnapshotModel(
            watch_target_id=watch_target_id,
            timestamp=result.scraped_at,
            availability=result.availability.value,
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
        self._session.add(model)
        await self._session.flush()
        return Snapshot(
            id=model.id,
            watch_target_id=model.watch_target_id,
            timestamp=model.timestamp,
            availability=Availability(model.availability),
            price=model.price,
            mrp=model.mrp,
            discount_pct=model.discount_pct,
            eta_minutes=model.eta_minutes,
            store_name=model.store_name,
            image_url=model.image_url,
            quantity_label=model.quantity_label,
            variants=model.variants,
            product_url=model.product_url,
        )


class SqlAlchemyDetectionEventRepository(DetectionEventRepository):
    """SQLAlchemy implementation of DetectionEventRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async session.

        Args:
            session: The SQLAlchemy async session.
        """
        self._session = session

    async def create(
        self,
        watch_target_id: int,
        snapshot_id: int,
        previous_snapshot_id: int | None,
        event_type: EventType,
        when: datetime,
    ) -> DetectionEvent:
        """Create a new detection event."""
        model = DetectionEventModel(
            watch_target_id=watch_target_id,
            snapshot_id=snapshot_id,
            previous_snapshot_id=previous_snapshot_id,
            event_type=event_type.value,
            created_at=when,
        )
        self._session.add(model)
        await self._session.flush()
        return DetectionEvent(
            id=model.id,
            watch_target_id=model.watch_target_id,
            snapshot_id=model.snapshot_id,
            previous_snapshot_id=model.previous_snapshot_id,
            event_type=EventType(model.event_type),
            created_at=model.created_at,
        )

    async def get_by_id(self, event_id: int) -> DetectionEvent | None:
        """Get a detection event by ID."""
        stmt = select(DetectionEventModel).where(DetectionEventModel.id == event_id)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is None:
            return None
        return DetectionEvent(
            id=model.id,
            watch_target_id=model.watch_target_id,
            snapshot_id=model.snapshot_id,
            previous_snapshot_id=model.previous_snapshot_id,
            event_type=EventType(model.event_type),
            created_at=model.created_at,
        )

    async def list_for_watch_target(
        self, watch_target_id: int, limit: int = 50
    ) -> list[DetectionEvent]:
        """List detection events for a watch target."""
        stmt = (
            select(DetectionEventModel)
            .where(DetectionEventModel.watch_target_id == watch_target_id)
            .order_by(DetectionEventModel.created_at.desc())
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [
            DetectionEvent(
                id=m.id,
                watch_target_id=m.watch_target_id,
                snapshot_id=m.snapshot_id,
                previous_snapshot_id=m.previous_snapshot_id,
                event_type=EventType(m.event_type),
                created_at=m.created_at,
            )
            for m in models
        ]


class SqlAlchemyWatchRepository(WatchRepository):
    """SQLAlchemy implementation of WatchRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async session.

        Args:
            session: The SQLAlchemy async session.
        """
        self._session = session

    async def list_by_watch_target(self, watch_target_id: int) -> list[Watch]:
        """List watches for a watch target."""
        stmt = select(WatchModel).where(
            WatchModel.watch_target_id == watch_target_id,
            WatchModel.is_active.is_(True),
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [
            Watch(
                id=m.id,
                user_id=m.user_id,
                product_id=m.product_id,
                watch_target_id=m.watch_target_id,
                interval_seconds=m.interval_seconds,
                is_active=m.is_active,
            )
            for m in models
        ]


class SqlAlchemyNotificationChannelRepository(NotificationChannelRepository):
    """SQLAlchemy implementation of NotificationChannelRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async session.

        Args:
            session: The SQLAlchemy async session.
        """
        self._session = session

    async def list_for_user(self, user_id: int) -> list[NotificationChannel]:
        """List notification channels for a user."""
        stmt = select(NotificationChannelModel).where(
            NotificationChannelModel.user_id == user_id
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [
            NotificationChannel(
                id=m.id,
                user_id=m.user_id,
                type=NotificationChannelType(m.type),
                config=m.config_json,
                is_verified=m.is_verified,
            )
            for m in models
        ]


class SqlAlchemyNotificationLogRepository(NotificationLogRepository):
    """SQLAlchemy implementation of NotificationLogRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async session.

        Args:
            session: The SQLAlchemy async session.
        """
        self._session = session

    async def exists_recent(self, dedup_key: str, cooldown_seconds: int) -> bool:
        """Check if a notification was recently sent."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=cooldown_seconds)
        stmt = select(NotificationLogModel).where(
            NotificationLogModel.dedup_key == dedup_key,
            NotificationLogModel.sent_at >= cutoff,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def create(
        self,
        user_id: int,
        detection_event_id: int,
        channel_id: int,
        status: str,
        dedup_key: str,
    ) -> NotificationLog:
        """Create a new notification log entry."""
        model = NotificationLogModel(
            user_id=user_id,
            detection_event_id=detection_event_id,
            channel_id=channel_id,
            status=status,
            sent_at=datetime.now(timezone.utc),
            dedup_key=dedup_key,
        )
        self._session.add(model)
        await self._session.flush()
        return NotificationLog(
            id=model.id,
            user_id=model.user_id,
            detection_event_id=model.detection_event_id,
            channel_id=model.channel_id,
            status=model.status,
            sent_at=model.sent_at,
            dedup_key=model.dedup_key,
        )
