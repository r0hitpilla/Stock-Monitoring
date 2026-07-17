from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.domain.enums import Availability, EventType, NotificationChannelType


@dataclass(frozen=True)
class LocationContext:
    """Geographic location context for monitoring."""

    city: str
    pincode: str


class ProviderProductResult(BaseModel):
    """Result of a single product scrape from a retailer."""

    retailer_slug: str
    keyword: str
    product_name: str
    availability: Availability
    price: float | None = None
    mrp: float | None = None
    discount_pct: float | None = None
    eta_minutes: int | None = None
    store_name: str | None = None
    image_url: str | None = None
    quantity_label: str | None = None
    variants: list[str] = []
    product_url: str | None = None
    scraped_at: datetime


@dataclass
class WatchTarget:
    """A product watch target in a specific location."""

    id: int | None
    retailer_slug: str
    city: str
    pincode: str
    keyword: str
    interval_seconds: int = 300


@dataclass
class Snapshot:
    """A point-in-time snapshot of product availability and price."""

    id: int | None
    watch_target_id: int
    timestamp: datetime
    availability: Availability
    price: float | None
    mrp: float | None
    discount_pct: float | None
    eta_minutes: int | None
    store_name: str | None
    image_url: str | None
    quantity_label: str | None
    variants: list[str]
    product_url: str | None


@dataclass
class DetectionEvent:
    """A detected change event from watching a product."""

    id: int | None
    watch_target_id: int
    snapshot_id: int
    previous_snapshot_id: int | None
    event_type: EventType
    created_at: datetime


@dataclass
class Product:
    """A product that a user is watching."""

    id: int | None
    user_id: int
    name: str
    keyword: str
    canonical_image_url: str | None = None


@dataclass
class Watch:
    """A user's watch for a product at a location."""

    id: int | None
    user_id: int
    product_id: int
    watch_target_id: int
    interval_seconds: int
    is_active: bool = True


@dataclass
class NotificationChannel:
    """A user's notification delivery channel."""

    id: int | None
    user_id: int
    type: NotificationChannelType
    config: dict[str, Any]
    is_verified: bool = False


@dataclass
class NotificationLog:
    """Log of a sent notification."""

    id: int | None
    user_id: int
    detection_event_id: int
    channel_id: int
    status: str
    sent_at: datetime
    dedup_key: str


@dataclass
class User:
    """A registered user identified by phone number."""

    id: int | None
    phone_number: str
    email: str | None
    created_at: datetime


@dataclass
class OtpChallenge:
    """A one-time-password challenge issued for phone verification."""

    id: int | None
    phone_number: str
    code_hash: str
    expires_at: datetime
    created_at: datetime
    consumed: bool = False
    attempt_count: int = 0


@dataclass
class TokenPair:
    """An access/refresh JWT pair issued after successful authentication."""

    access_token: str
    refresh_token: str


@dataclass
class NotificationContext:
    """Context needed by a notification sender to compose a message."""

    keyword: str
    retailer_slug: str
    event_type: EventType
    snapshot: "Snapshot"


@dataclass
class Retailer:
    """A supported retailer configuration."""

    id: int | None
    slug: str
    name: str
    is_active: bool = True
