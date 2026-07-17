"""Background tasks for notification processing."""

import asyncio

import httpx

from app.application.notification_service import NotificationService
from app.core.config import get_settings
from app.domain.enums import NotificationChannelType
from app.infrastructure.db.repositories import (
    SqlAlchemyDetectionEventRepository,
    SqlAlchemyNotificationChannelRepository,
    SqlAlchemyNotificationLogRepository,
    SqlAlchemySnapshotRepository,
    SqlAlchemyWatchRepository,
    SqlAlchemyWatchTargetRepository,
)
from app.infrastructure.db.session import get_engine, get_sessionmaker
from app.infrastructure.notifications.discord import DiscordSender
from app.infrastructure.notifications.email import EmailSender
from app.infrastructure.notifications.telegram import TelegramSender
from app.tasks.celery_app import celery_app


async def _process_detection_event_async(event_id: int) -> None:
    """Process a detection event asynchronously.

    Creates repositories, senders, and notification service, then processes
    the event through the notification pipeline.

    Args:
        event_id: The ID of the detection event to process.
    """
    settings = get_settings()
    engine = get_engine(settings.database_url)
    session_factory = get_sessionmaker(engine)
    async with session_factory() as session, httpx.AsyncClient() as http_client:
        senders = {
            NotificationChannelType.TELEGRAM: TelegramSender(http_client, settings.telegram_bot_token),
            NotificationChannelType.DISCORD: DiscordSender(http_client),
            NotificationChannelType.EMAIL: EmailSender(
                settings.smtp_host,
                settings.smtp_port,
                settings.smtp_username,
                settings.smtp_password,
                settings.smtp_from_address,
            ),
        }
        service = NotificationService(
            watch_target_repo=SqlAlchemyWatchTargetRepository(session),
            snapshot_repo=SqlAlchemySnapshotRepository(session),
            event_repo=SqlAlchemyDetectionEventRepository(session),
            watch_repo=SqlAlchemyWatchRepository(session),
            channel_repo=SqlAlchemyNotificationChannelRepository(session),
            notification_log_repo=SqlAlchemyNotificationLogRepository(session),
            senders=senders,
        )
        await service.process_event(event_id)
        await session.commit()
    await engine.dispose()


@celery_app.task(name="app.tasks.notifications.process_detection_event")
def process_detection_event(event_id: int) -> None:
    """Celery task to process a detection event.

    Dispatches to the async processor using asyncio.run().

    Args:
        event_id: The ID of the detection event to process.
    """
    asyncio.run(_process_detection_event_async(event_id))
