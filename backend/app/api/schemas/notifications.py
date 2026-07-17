from typing import Any

from pydantic import BaseModel


class ChannelCreateSchema(BaseModel):
    type: str
    config: dict[str, Any]


class ChannelSchema(BaseModel):
    id: int
    type: str
    config: dict[str, Any]
    is_verified: bool


class NotificationLogEntrySchema(BaseModel):
    id: int
    detection_event_id: int
    channel_id: int
    status: str
    sent_at: str
