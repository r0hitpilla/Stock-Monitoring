"""Asyncio scheduler that periodically checks due watch targets."""

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable

import structlog

from app.application.monitoring_service import MonitoringService
from app.domain.entities import DetectionEvent, WatchTarget
from app.domain.ports.repositories import WatchTargetRepository

logger = structlog.get_logger(__name__)


def utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


class Scheduler:
    """Periodically finds due watch targets and checks them with bounded concurrency.

    Each scheduling pass (`tick`) fetches all currently due watch targets,
    groups them by retailer, and checks each retailer's group concurrently
    (bounded by a per-retailer `asyncio.Semaphore`). A single target's
    exception is caught and logged, never aborting the tick for the
    remaining targets — in the same retailer group or in other groups.
    """

    def __init__(
        self,
        watch_target_repo: WatchTargetRepository,
        monitoring_service: MonitoringService,
        now_fn: Callable[[], datetime] = utcnow,
        concurrency_per_retailer: int = 4,
    ) -> None:
        """Initialize the scheduler.

        Args:
            watch_target_repo: Repository used to list watch targets due for checking.
            monitoring_service: Service used to check a single watch target.
            now_fn: Callable returning the current time; injectable for testing.
            concurrency_per_retailer: Maximum concurrent checks per retailer group.
        """
        self._watch_target_repo = watch_target_repo
        self._monitoring_service = monitoring_service
        self._now_fn = now_fn
        self._concurrency_per_retailer = concurrency_per_retailer

    async def tick(self) -> list[DetectionEvent]:
        """Run one scheduling pass.

        Fetches all watch targets due at the current time, groups them by
        `retailer_slug`, and checks each group concurrently with a bounded
        `asyncio.Semaphore` per retailer. Exceptions raised while checking
        an individual target are caught and logged rather than propagated,
        so one failing target never prevents others from being checked.

        Returns:
            The combined list of detection events fired across all checked
            targets in this pass.
        """
        due_targets = await self._watch_target_repo.list_due(self._now_fn())
        by_retailer: dict[str, list[WatchTarget]] = defaultdict(list)
        for target in due_targets:
            by_retailer[target.retailer_slug].append(target)

        group_results = await asyncio.gather(
            *(self._run_retailer_group(group) for group in by_retailer.values())
        )

        events: list[DetectionEvent] = []
        for group_events in group_results:
            events.extend(group_events)
        return events

    async def _run_retailer_group(
        self, targets: list[WatchTarget]
    ) -> list[DetectionEvent]:
        """Check every target in a single retailer group with bounded concurrency.

        Args:
            targets: The watch targets belonging to one retailer, due for checking.

        Returns:
            The combined list of detection events fired by this group's checks.
        """
        semaphore = asyncio.Semaphore(self._concurrency_per_retailer)

        async def _check(target: WatchTarget) -> list[DetectionEvent]:
            async with semaphore:
                try:
                    return await self._monitoring_service.check_watch_target(target)
                except Exception:
                    logger.exception(
                        "watch_target_check_failed", watch_target_id=target.id
                    )
                    return []

        check_results = await asyncio.gather(*(_check(target) for target in targets))

        events: list[DetectionEvent] = []
        for target_events in check_results:
            events.extend(target_events)
        return events

    async def run_forever(self, poll_interval_seconds: float = 1.0) -> None:
        """Run `tick()` repeatedly on a fixed interval until cancelled.

        Args:
            poll_interval_seconds: Seconds to sleep between successive ticks.
        """
        while True:
            await self.tick()
            await asyncio.sleep(poll_interval_seconds)
