from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SystemLogSchema(BaseModel):
    id: int
    level: str
    message: str
    context: dict[str, Any]
    created_at: datetime
