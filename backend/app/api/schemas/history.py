"""History endpoint schemas."""

from datetime import datetime

from pydantic import BaseModel


class SnapshotSchema(BaseModel):
    """Schema for a snapshot within a history entry."""

    availability: str
    price: float | None
    mrp: float | None
    discount_pct: float | None
    eta_minutes: int | None
    store_name: str | None
    image_url: str | None
    quantity_label: str | None
    variants: list[str]
    product_url: str | None


class HistoryEntrySchema(BaseModel):
    """Schema for a history entry (detection event with snapshot)."""

    event_id: int
    event_type: str
    created_at: datetime
    snapshot: SnapshotSchema
