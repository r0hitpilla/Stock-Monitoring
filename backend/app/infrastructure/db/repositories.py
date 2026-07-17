"""SQLAlchemy implementations of repository interfaces."""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import (
    DetectionEvent,
    NotificationChannel,
    NotificationLog,
    OtpChallenge,
    Product,
    ProviderProductResult,
    Retailer,
    Snapshot,
    SystemLog,
    User,
    Watch,
    WatchTarget,
)
from app.domain.enums import Availability, EventType, NotificationChannelType
from app.domain.ports.repositories import (
    DetectionEventRepository,
    NotificationChannelRepository,
    NotificationLogRepository,
    OtpChallengeRepository,
    ProductRepository,
    RetailerRepository,
    SettingsRepository,
    SnapshotRepository,
    SystemLogRepository,
    UserRepository,
    WatchRepository,
    WatchTargetRepository,
)
from app.infrastructure.db.models import (
    DetectionEventModel,
    NotificationChannelModel,
    NotificationLogModel,
    OtpChallengeModel,
    ProductModel,
    RetailerModel,
    SettingsModel,
    SnapshotModel,
    SystemLogModel,
    UserModel,
    WatchModel,
    WatchTargetModel,
)


def _to_user(model: UserModel) -> User:
    """Convert a UserModel to a User entity."""
    return User(
        id=model.id,
        phone_number=model.phone_number,
        email=model.email,
        created_at=model.created_at,
    )


def _to_otp_challenge(model: OtpChallengeModel) -> OtpChallenge:
    """Convert an OtpChallengeModel to an OtpChallenge entity."""
    return OtpChallenge(
        id=model.id,
        phone_number=model.phone_number,
        code_hash=model.code_hash,
        expires_at=model.expires_at,
        created_at=model.created_at,
        consumed=model.consumed,
        attempt_count=model.attempt_count,
    )


def _to_retailer(model: RetailerModel) -> Retailer:
    """Convert a RetailerModel to a Retailer entity."""
    return Retailer(
        id=model.id,
        slug=model.slug,
        name=model.name,
        is_active=model.is_active,
    )


def _to_product(model: ProductModel) -> Product:
    """Convert a ProductModel to a Product entity."""
    return Product(
        id=model.id,
        user_id=model.user_id,
        name=model.name,
        keyword=model.keyword,
        canonical_image_url=model.canonical_image_url,
    )


class SqlAlchemyUserRepository(UserRepository):
    """SQLAlchemy implementation of UserRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async session.

        Args:
            session: The SQLAlchemy async session.
        """
        self._session = session

    async def get_or_create_by_phone(self, phone_number: str) -> User:
        """Get an existing user by phone number, or create one."""
        stmt = select(UserModel).where(UserModel.phone_number == phone_number)
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            return _to_user(existing)

        model = UserModel(
            phone_number=phone_number,
            email=None,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(model)
        await self._session.flush()
        return _to_user(model)

    async def get_by_id(self, user_id: int) -> User | None:
        """Get a user by ID."""
        stmt = select(UserModel).where(UserModel.id == user_id)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is None:
            return None
        return _to_user(model)


class SqlAlchemyOtpChallengeRepository(OtpChallengeRepository):
    """SQLAlchemy implementation of OtpChallengeRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async session.

        Args:
            session: The SQLAlchemy async session.
        """
        self._session = session

    async def create(
        self,
        phone_number: str,
        code_hash: str,
        expires_at: datetime,
        created_at: datetime,
    ) -> OtpChallenge:
        """Create a new OTP challenge."""
        model = OtpChallengeModel(
            phone_number=phone_number,
            code_hash=code_hash,
            expires_at=expires_at,
            created_at=created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_otp_challenge(model)

    async def get_latest(self, phone_number: str) -> OtpChallenge | None:
        """Get the most recently created OTP challenge for a phone number."""
        stmt = (
            select(OtpChallengeModel)
            .where(OtpChallengeModel.phone_number == phone_number)
            .order_by(OtpChallengeModel.created_at.desc())
            .limit(1)
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is None:
            return None
        return _to_otp_challenge(model)

    async def count_recent(self, phone_number: str, window_seconds: int) -> int:
        """Count OTP challenges created for a phone number within a time window."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
        stmt = select(OtpChallengeModel).where(
            OtpChallengeModel.phone_number == phone_number,
            OtpChallengeModel.created_at >= cutoff,
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return len(models)

    async def mark_consumed(self, challenge_id: int) -> None:
        """Mark an OTP challenge as consumed."""
        stmt = select(OtpChallengeModel).where(OtpChallengeModel.id == challenge_id)
        model = (await self._session.execute(stmt)).scalar_one()
        model.consumed = True

    async def increment_attempt(self, challenge_id: int) -> None:
        """Increment the attempt count of an OTP challenge."""
        stmt = select(OtpChallengeModel).where(OtpChallengeModel.id == challenge_id)
        model = (await self._session.execute(stmt)).scalar_one()
        model.attempt_count += 1


class SqlAlchemyRetailerRepository(RetailerRepository):
    """SQLAlchemy implementation of RetailerRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async session.

        Args:
            session: The SQLAlchemy async session.
        """
        self._session = session

    async def list_all(self) -> list[Retailer]:
        """List all retailers."""
        stmt = select(RetailerModel)
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_retailer(m) for m in models]


class SqlAlchemyProductRepository(ProductRepository):
    """SQLAlchemy implementation of ProductRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async session.

        Args:
            session: The SQLAlchemy async session.
        """
        self._session = session

    async def create(
        self, user_id: int, name: str, keyword: str, canonical_image_url: str | None
    ) -> Product:
        """Create a new product."""
        model = ProductModel(
            user_id=user_id,
            name=name,
            keyword=keyword,
            canonical_image_url=canonical_image_url,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_product(model)

    async def list_for_user(self, user_id: int) -> list[Product]:
        """List products for a user."""
        stmt = select(ProductModel).where(ProductModel.user_id == user_id)
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_product(m) for m in models]

    async def get_by_id(self, product_id: int) -> Product | None:
        """Get a product by ID."""
        stmt = select(ProductModel).where(ProductModel.id == product_id)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is None:
            return None
        return _to_product(model)

    async def delete(self, product_id: int) -> None:
        """Delete a product."""
        stmt = select(ProductModel).where(ProductModel.id == product_id)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is not None:
            await self._session.delete(model)


def _to_watch(model: WatchModel) -> Watch:
    """Convert a WatchModel to a Watch entity."""
    return Watch(
        id=model.id,
        user_id=model.user_id,
        product_id=model.product_id,
        watch_target_id=model.watch_target_id,
        interval_seconds=model.interval_seconds,
        is_active=model.is_active,
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

    async def create(
        self, user_id: int, product_id: int, watch_target_id: int, interval_seconds: int
    ) -> Watch:
        """Create a new watch."""
        model = WatchModel(
            user_id=user_id,
            product_id=product_id,
            watch_target_id=watch_target_id,
            interval_seconds=interval_seconds,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_watch(model)

    async def list_by_watch_target(self, watch_target_id: int) -> list[Watch]:
        """List watches for a watch target."""
        stmt = select(WatchModel).where(
            WatchModel.watch_target_id == watch_target_id,
            WatchModel.is_active.is_(True),
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_watch(m) for m in models]

    async def list_for_user(self, user_id: int) -> list[Watch]:
        """List watches for a user."""
        stmt = select(WatchModel).where(WatchModel.user_id == user_id)
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_watch(m) for m in models]

    async def get_by_id(self, watch_id: int) -> Watch | None:
        """Get a watch by ID."""
        stmt = select(WatchModel).where(WatchModel.id == watch_id)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is None:
            return None
        return _to_watch(model)

    async def deactivate(self, watch_id: int) -> None:
        """Deactivate a watch (soft-delete)."""
        stmt = select(WatchModel).where(WatchModel.id == watch_id)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is not None:
            model.is_active = False


def _to_notification_channel(model: NotificationChannelModel) -> NotificationChannel:
    """Convert a NotificationChannelModel to a NotificationChannel entity."""
    return NotificationChannel(
        id=model.id,
        user_id=model.user_id,
        type=NotificationChannelType(model.type),
        config=model.config_json,
        is_verified=model.is_verified,
    )


def _to_notification_log(model: NotificationLogModel) -> NotificationLog:
    """Convert a NotificationLogModel to a NotificationLog entity."""
    return NotificationLog(
        id=model.id,
        user_id=model.user_id,
        detection_event_id=model.detection_event_id,
        channel_id=model.channel_id,
        status=model.status,
        sent_at=model.sent_at,
        dedup_key=model.dedup_key,
    )


class SqlAlchemyNotificationChannelRepository(NotificationChannelRepository):
    """SQLAlchemy implementation of NotificationChannelRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async session.

        Args:
            session: The SQLAlchemy async session.
        """
        self._session = session

    async def create(
        self,
        user_id: int,
        type: NotificationChannelType,
        config: dict[str, Any],
        is_verified: bool = False,
    ) -> NotificationChannel:
        """Create a new notification channel for a user."""
        model = NotificationChannelModel(
            user_id=user_id,
            type=type.value,
            config_json=config,
            is_verified=is_verified,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_notification_channel(model)

    async def list_for_user(self, user_id: int) -> list[NotificationChannel]:
        """List notification channels for a user."""
        stmt = select(NotificationChannelModel).where(
            NotificationChannelModel.user_id == user_id
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_notification_channel(m) for m in models]

    async def get_by_id(self, channel_id: int) -> NotificationChannel | None:
        """Get a notification channel by ID."""
        stmt = select(NotificationChannelModel).where(
            NotificationChannelModel.id == channel_id
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is None:
            return None
        return _to_notification_channel(model)

    async def delete(self, channel_id: int) -> None:
        """Delete a notification channel."""
        stmt = select(NotificationChannelModel).where(
            NotificationChannelModel.id == channel_id
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is not None:
            await self._session.delete(model)

    async def mark_verified(self, channel_id: int) -> None:
        """Mark a notification channel as verified."""
        stmt = select(NotificationChannelModel).where(
            NotificationChannelModel.id == channel_id
        )
        model = (await self._session.execute(stmt)).scalar_one()
        model.is_verified = True


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
        return _to_notification_log(model)

    async def list_for_user(
        self, user_id: int, limit: int = 50
    ) -> list[NotificationLog]:
        """List notification log entries for a user, most recent first."""
        stmt = (
            select(NotificationLogModel)
            .where(NotificationLogModel.user_id == user_id)
            .order_by(NotificationLogModel.sent_at.desc())
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_notification_log(m) for m in models]


class SqlAlchemySettingsRepository(SettingsRepository):
    """SQLAlchemy implementation of SettingsRepository.

    Settings are stored as user-scoped key/value rows (see `SettingsModel`),
    not as a single JSON blob per user.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async session.

        Args:
            session: The SQLAlchemy async session.
        """
        self._session = session

    async def get_for_user(self, user_id: int) -> dict[str, Any]:
        """Get all settings for a user as a key/value mapping."""
        stmt = select(SettingsModel).where(SettingsModel.user_id == user_id)
        models = (await self._session.execute(stmt)).scalars().all()
        return {m.key: m.value_json for m in models}

    async def set_for_user(self, user_id: int, key: str, value: Any) -> None:
        """Set (create or update) a single setting for a user."""
        stmt = select(SettingsModel).where(
            SettingsModel.user_id == user_id, SettingsModel.key == key
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            existing.value_json = value
        else:
            model = SettingsModel(user_id=user_id, key=key, value_json=value)
            self._session.add(model)
        await self._session.flush()


class SqlAlchemySystemLogRepository(SystemLogRepository):
    """SQLAlchemy implementation of SystemLogRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async session.

        Args:
            session: The SQLAlchemy async session.
        """
        self._session = session

    async def create(
        self,
        level: str,
        message: str,
        context: dict[str, Any],
        at: datetime,
    ) -> SystemLog:
        """Create a new system log entry."""
        model = SystemLogModel(
            level=level,
            message=message,
            context=context,
            created_at=at,
        )
        self._session.add(model)
        await self._session.flush()
        return SystemLog(
            id=model.id,
            level=model.level,
            message=model.message,
            context=model.context,
            created_at=model.created_at,
        )

    async def list_recent(self, limit: int = 100) -> list[SystemLog]:
        """List the most recent system log entries."""
        stmt = (
            select(SystemLogModel)
            .order_by(SystemLogModel.created_at.desc())
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [
            SystemLog(
                id=m.id,
                level=m.level,
                message=m.message,
                context=m.context,
                created_at=m.created_at,
            )
            for m in models
        ]
