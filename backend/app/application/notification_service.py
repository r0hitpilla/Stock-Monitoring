"""Notification service for processing and sending notifications."""

from app.domain.entities import NotificationContext
from app.domain.enums import NotificationChannelType
from app.domain.ports.notification import NotificationSender
from app.domain.ports.repositories import (
    DetectionEventRepository,
    NotificationChannelRepository,
    NotificationLogRepository,
    SnapshotRepository,
    WatchRepository,
    WatchTargetRepository,
)


class NotificationService:
    """Service for orchestrating notification delivery."""

    def __init__(
        self,
        watch_target_repo: WatchTargetRepository,
        snapshot_repo: SnapshotRepository,
        event_repo: DetectionEventRepository,
        watch_repo: WatchRepository,
        channel_repo: NotificationChannelRepository,
        notification_log_repo: NotificationLogRepository,
        senders: dict[NotificationChannelType, NotificationSender],
        cooldown_seconds: int = 900,
    ) -> None:
        """Initialize the notification service.

        Args:
            watch_target_repo: Repository for watch targets.
            snapshot_repo: Repository for snapshots.
            event_repo: Repository for detection events.
            watch_repo: Repository for watches.
            channel_repo: Repository for notification channels.
            notification_log_repo: Repository for notification logs.
            senders: Map of channel types to notification senders.
            cooldown_seconds: Cooldown period for deduplication in seconds.
        """
        self._watch_target_repo = watch_target_repo
        self._snapshot_repo = snapshot_repo
        self._event_repo = event_repo
        self._watch_repo = watch_repo
        self._channel_repo = channel_repo
        self._notification_log_repo = notification_log_repo
        self._senders = senders
        self._cooldown_seconds = cooldown_seconds

    async def process_event(self, event_id: int) -> None:
        """Process a detection event and send notifications.

        Loads the event and related data, then sends notifications to all
        subscribed users through their configured channels. Uses deduplication
        to prevent alert storms.

        Args:
            event_id: The ID of the detection event to process.
        """
        event = await self._event_repo.get_by_id(event_id)
        if event is None:
            return

        watch_target = await self._watch_target_repo.get_by_id(event.watch_target_id)
        snapshot = await self._snapshot_repo.get_by_id(event.snapshot_id)
        if watch_target is None or snapshot is None:
            return

        context = NotificationContext(
            keyword=watch_target.keyword,
            retailer_slug=watch_target.retailer_slug,
            event_type=event.event_type,
            snapshot=snapshot,
        )

        watches = await self._watch_repo.list_by_watch_target(event.watch_target_id)
        seen_users: set[int] = set()
        for watch in watches:
            if watch.user_id in seen_users:
                continue
            seen_users.add(watch.user_id)

            dedup_key = (
                f"{watch.user_id}:{event.watch_target_id}:{event.event_type.value}"
            )
            if await self._notification_log_repo.exists_recent(
                dedup_key, self._cooldown_seconds
            ):
                continue

            channels = await self._channel_repo.list_for_user(watch.user_id)
            for channel in channels:
                sender = self._senders.get(channel.type)
                if sender is None:
                    continue
                success = await sender.send(channel, event, context)
                # event.id and channel.id are guaranteed to be non-None here
                # since they were fetched/listed from the database
                assert event.id is not None
                assert channel.id is not None
                await self._notification_log_repo.create(
                    user_id=watch.user_id,
                    detection_event_id=event.id,
                    channel_id=channel.id,
                    status="sent" if success else "failed",
                    dedup_key=dedup_key,
                )
