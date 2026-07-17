"""Application-layer orchestration for monitoring a single watch target."""

from datetime import datetime, timezone

from app.application.diffing import diff_snapshots
from app.domain.entities import DetectionEvent, LocationContext, WatchTarget
from app.domain.ports.messaging import EventPublisher, TaskDispatcher
from app.domain.ports.provider import ProviderRegistry
from app.domain.ports.repositories import (
    DetectionEventRepository,
    SnapshotRepository,
    WatchTargetRepository,
)


class MonitoringService:
    """Orchestrates a single check of a watch target end to end.

    Given a watch target, this service resolves the correct retailer
    provider, searches for the tracked product, diffs the result against
    the latest stored snapshot, and on any detected change persists a new
    snapshot plus one detection event per changed field, publishes each
    event, and dispatches a background job per event. The watch target is
    always marked as checked, whether or not anything changed.
    """

    def __init__(
        self,
        provider_registry: ProviderRegistry,
        watch_target_repo: WatchTargetRepository,
        snapshot_repo: SnapshotRepository,
        event_repo: DetectionEventRepository,
        event_publisher: EventPublisher,
        task_dispatcher: TaskDispatcher,
    ) -> None:
        """Initialize the service with its collaborating ports.

        Args:
            provider_registry: Registry used to resolve a retailer provider by slug.
            watch_target_repo: Repository for watch target persistence and scheduling state.
            snapshot_repo: Repository for reading/writing product snapshots.
            event_repo: Repository for persisting detection events.
            event_publisher: Publisher used to broadcast detected events.
            task_dispatcher: Dispatcher used to enqueue background jobs per event.
        """
        self._provider_registry = provider_registry
        self._watch_target_repo = watch_target_repo
        self._snapshot_repo = snapshot_repo
        self._event_repo = event_repo
        self._event_publisher = event_publisher
        self._task_dispatcher = task_dispatcher

    async def check_watch_target(
        self, watch_target: WatchTarget
    ) -> list[DetectionEvent]:
        """Check a single watch target and report any detected changes.

        This is the single orchestration point the scheduler calls per due
        target: initialize the provider for the target's location, search
        by keyword, diff against the latest snapshot, and on any change
        persist a new snapshot plus one DetectionEvent per changed field,
        publish each event, and dispatch a background job per event. The
        target is always marked as checked so `list_due` stops returning it
        until its interval elapses again.

        Args:
            watch_target: The watch target to check.

        Returns:
            The list of detection events fired by this check. Empty if the
            provider returned no results or nothing changed.

        Raises:
            ValueError: If the watch target has not yet been persisted
                (i.e. has no ID). Only persisted targets can be checked.
        """
        if watch_target.id is None:
            raise ValueError(
                "watch_target must be persisted (have an id) before checking"
            )
        watch_target_id = watch_target.id

        provider = self._provider_registry.get(watch_target.retailer_slug)
        await provider.initialize(
            LocationContext(watch_target.city, watch_target.pincode)
        )

        results = await provider.search_product(watch_target.keyword)
        if not results:
            await self._watch_target_repo.mark_checked(
                watch_target_id, datetime.now(timezone.utc)
            )
            return []
        result = results[0]

        previous = await self._snapshot_repo.get_latest(watch_target_id)
        event_types = diff_snapshots(previous, result)

        if not event_types:
            await self._watch_target_repo.mark_checked(
                watch_target_id, result.scraped_at
            )
            return []

        snapshot = await self._snapshot_repo.create(watch_target_id, result)
        if snapshot.id is None:
            raise ValueError(
                "snapshot_repo.create must return a persisted snapshot with an id"
            )
        snapshot_id = snapshot.id

        events: list[DetectionEvent] = []
        for event_type in event_types:
            event = await self._event_repo.create(
                watch_target_id,
                snapshot_id,
                previous.id if previous else None,
                event_type,
                result.scraped_at,
            )
            if event.id is None:
                raise ValueError(
                    "event_repo.create must return a persisted event with an id"
                )
            events.append(event)
            await self._event_publisher.publish(watch_target_id, event)
            self._task_dispatcher.dispatch_detection_event(event.id)

        await self._watch_target_repo.mark_checked(watch_target_id, result.scraped_at)
        return events
