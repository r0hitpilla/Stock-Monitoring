from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    type_annotation_map = {datetime: DateTime(timezone=True)}


class UserModel(Base):
    """User account model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime]


class OtpChallengeModel(Base):
    """OTP challenge for phone authentication."""

    __tablename__ = "otp_challenges"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str] = mapped_column(index=True)
    code_hash: Mapped[str]
    expires_at: Mapped[datetime]
    created_at: Mapped[datetime]
    consumed: Mapped[bool] = mapped_column(default=False)
    attempt_count: Mapped[int] = mapped_column(default=0)


class RetailerModel(Base):
    """Supported retailer configurations."""

    __tablename__ = "retailers"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)


class ProductModel(Base):
    """Products that users watch."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]
    keyword: Mapped[str]
    canonical_image_url: Mapped[str | None] = mapped_column(nullable=True)


class WatchTargetModel(Base):
    """Cross-user scrape targets (deduplicated by unique constraint)."""

    __tablename__ = "watch_targets"
    __table_args__ = (
        UniqueConstraint(
            "retailer_slug", "city", "pincode", "keyword", name="uq_watch_target"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    retailer_slug: Mapped[str]
    city: Mapped[str]
    pincode: Mapped[str]
    keyword: Mapped[str]
    interval_seconds: Mapped[int] = mapped_column(default=300)
    last_checked_at: Mapped[datetime | None] = mapped_column(nullable=True)


class WatchModel(Base):
    """User watches tied to products and locations."""

    __tablename__ = "watches"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    watch_target_id: Mapped[int] = mapped_column(ForeignKey("watch_targets.id"))
    interval_seconds: Mapped[int] = mapped_column(default=300)
    is_active: Mapped[bool] = mapped_column(default=True)


class SnapshotModel(Base):
    """Snapshot of product availability at a location."""

    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    watch_target_id: Mapped[int] = mapped_column(
        ForeignKey("watch_targets.id"), index=True
    )
    timestamp: Mapped[datetime]
    availability: Mapped[str]
    price: Mapped[float | None]
    mrp: Mapped[float | None]
    discount_pct: Mapped[float | None]
    eta_minutes: Mapped[int | None]
    store_name: Mapped[str | None]
    image_url: Mapped[str | None]
    quantity_label: Mapped[str | None]
    variants: Mapped[list[str]] = mapped_column(JSON, default=list)
    product_url: Mapped[str | None]


class DetectionEventModel(Base):
    """Event detected when snapshot differs from previous (price change, availability change, etc)."""

    __tablename__ = "detection_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    watch_target_id: Mapped[int] = mapped_column(
        ForeignKey("watch_targets.id"), index=True
    )
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"))
    previous_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("snapshots.id"), nullable=True
    )
    event_type: Mapped[str]
    created_at: Mapped[datetime]


class NotificationChannelModel(Base):
    """User's notification channel (Slack, email, etc)."""

    __tablename__ = "notification_channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str]
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_verified: Mapped[bool] = mapped_column(default=False)


class NotificationLogModel(Base):
    """Log of sent notifications."""

    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    detection_event_id: Mapped[int] = mapped_column(ForeignKey("detection_events.id"))
    channel_id: Mapped[int] = mapped_column(ForeignKey("notification_channels.id"))
    status: Mapped[str]
    sent_at: Mapped[datetime]
    dedup_key: Mapped[str] = mapped_column(index=True)


class SettingsModel(Base):
    """Global and user-specific settings, stored as key/value rows."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    key: Mapped[str]
    value_json: Mapped[Any] = mapped_column(JSON, default=dict)


class SystemLogModel(Base):
    """System-level log entry (e.g. an unhandled request error)."""

    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str]
    message: Mapped[str]
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime]
