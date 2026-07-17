from pydantic import BaseModel


class WatchCreateSchema(BaseModel):
    product_id: int
    retailer_slug: str
    city: str
    pincode: str
    interval_seconds: int = 300


class WatchSchema(BaseModel):
    id: int
    product_id: int
    watch_target_id: int
    interval_seconds: int
    is_active: bool = True
