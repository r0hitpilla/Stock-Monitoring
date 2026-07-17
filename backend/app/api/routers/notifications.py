from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_session
from app.api.schemas.notifications import (
    ChannelCreateSchema,
    ChannelSchema,
    NotificationLogEntrySchema,
)
from app.domain.enums import NotificationChannelType
from app.domain.ports.repositories import (
    NotificationChannelRepository,
    NotificationLogRepository,
)
from app.infrastructure.db.repositories import (
    SqlAlchemyNotificationChannelRepository,
    SqlAlchemyNotificationLogRepository,
)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


def get_notification_channel_repository(
    session: AsyncSession = Depends(get_session),
) -> NotificationChannelRepository:
    """Provide a NotificationChannelRepository backed by the request's DB session."""
    return SqlAlchemyNotificationChannelRepository(session)


def get_notification_log_repository(
    session: AsyncSession = Depends(get_session),
) -> NotificationLogRepository:
    """Provide a NotificationLogRepository backed by the request's DB session."""
    return SqlAlchemyNotificationLogRepository(session)


@router.post(
    "/channels", response_model=ChannelSchema, status_code=status.HTTP_201_CREATED
)
async def create_channel(
    body: ChannelCreateSchema,
    user_id: int = Depends(get_current_user_id),
    repo: NotificationChannelRepository = Depends(get_notification_channel_repository),
) -> ChannelSchema:
    """Create a new notification channel for the current user."""
    channel = await repo.create(
        user_id, NotificationChannelType(body.type), body.config
    )
    return ChannelSchema(
        id=channel.id,
        type=channel.type.value,
        config=channel.config,
        is_verified=channel.is_verified,
    )


@router.get("/channels", response_model=list[ChannelSchema])
async def list_channels(
    user_id: int = Depends(get_current_user_id),
    repo: NotificationChannelRepository = Depends(get_notification_channel_repository),
) -> list[ChannelSchema]:
    """List notification channels for the current user."""
    channels = await repo.list_for_user(user_id)
    return [
        ChannelSchema(
            id=c.id, type=c.type.value, config=c.config, is_verified=c.is_verified
        )
        for c in channels
    ]


@router.post("/channels/{channel_id}/verify")
async def verify_channel(
    channel_id: int,
    user_id: int = Depends(get_current_user_id),
    repo: NotificationChannelRepository = Depends(get_notification_channel_repository),
) -> dict[str, str]:
    """Self-attest that a notification channel received a test message.

    This is a self-attestation (the user confirms receipt) rather than an
    inbound webhook verification, which is out of scope for the MVP.
    """
    channel = await repo.get_by_id(channel_id)
    if channel is None or channel.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel not found")
    await repo.mark_verified(channel_id)
    return {"status": "verified"}


@router.delete("/channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: int,
    user_id: int = Depends(get_current_user_id),
    repo: NotificationChannelRepository = Depends(get_notification_channel_repository),
) -> None:
    """Delete a notification channel belonging to the current user."""
    channel = await repo.get_by_id(channel_id)
    if channel is None or channel.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel not found")
    await repo.delete(channel_id)


@router.get("/log", response_model=list[NotificationLogEntrySchema])
async def list_notification_log(
    user_id: int = Depends(get_current_user_id),
    repo: NotificationLogRepository = Depends(get_notification_log_repository),
) -> list[NotificationLogEntrySchema]:
    """List sent-notification log entries for the current user."""
    entries = await repo.list_for_user(user_id)
    return [
        NotificationLogEntrySchema(
            id=e.id,
            detection_event_id=e.detection_event_id,
            channel_id=e.channel_id,
            status=e.status,
            sent_at=e.sent_at.isoformat(),
        )
        for e in entries
    ]
