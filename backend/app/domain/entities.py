from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import Availability, EventType


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
