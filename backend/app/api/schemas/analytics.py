from pydantic import BaseModel


class PricePointSchema(BaseModel):
    timestamp: str
    price: float | None


class AvailabilitySummarySchema(BaseModel):
    availability_pct: float
    restock_count: int
    total_downtime_minutes: float
    average_downtime_minutes: float
