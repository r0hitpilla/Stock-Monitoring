from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_session
from app.api.schemas.settings import SettingUpdateSchema
from app.domain.ports.repositories import SettingsRepository
from app.infrastructure.db.repositories import SqlAlchemySettingsRepository

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


def get_settings_repository(
    session: AsyncSession = Depends(get_session),
) -> SettingsRepository:
    """Provide a SettingsRepository backed by the request's DB session."""
    return SqlAlchemySettingsRepository(session)


@router.get("")
async def get_settings_for_user(
    user_id: int = Depends(get_current_user_id),
    repo: SettingsRepository = Depends(get_settings_repository),
) -> dict[str, Any]:
    """Get all settings for the current user as a key/value mapping."""
    return await repo.get_for_user(user_id)


@router.put("")
async def update_setting(
    body: SettingUpdateSchema,
    user_id: int = Depends(get_current_user_id),
    repo: SettingsRepository = Depends(get_settings_repository),
) -> dict[str, Any]:
    """Set a single setting for the current user and return the updated mapping."""
    await repo.set_for_user(user_id, body.key, body.value)
    return await repo.get_for_user(user_id)
