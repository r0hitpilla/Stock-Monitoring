"""Analytics endpoint schemas."""

from pydantic import BaseModel


class PricePointSchema(BaseModel):
    """A single price observation at a point in time."""

    timestamp: str
    price: float | None


class AvailabilitySummarySchema(BaseModel):
    """Schema for aggregate availability/restock metrics over a period."""

    availability_pct: float
    restock_count: int
    total_downtime_minutes: float
    average_downtime_minutes: float
