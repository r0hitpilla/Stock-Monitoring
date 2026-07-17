from typing import Any

from pydantic import BaseModel


class SettingUpdateSchema(BaseModel):
    key: str
    value: Any
