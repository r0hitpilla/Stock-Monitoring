"""Retailers endpoint schemas."""

from pydantic import BaseModel


class RetailerSchema(BaseModel):
    """Schema for a retailer response."""

    slug: str
    name: str
    is_active: bool
