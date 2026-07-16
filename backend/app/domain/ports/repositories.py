"""Abstract repository interfaces for domain layer."""

from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities import (
    DetectionEvent,
    ProviderProductResult,
    Snapshot,
    WatchTarget,
)
from app.domain.enums import EventType


class WatchTargetRepository(ABC):
    """Repository for managing watch targets."""

    @abstractmethod
    async def get_or_create(
        self,
        retailer_slug: str,
        city: str,
        pincode: str,
        keyword: str,
        interval_seconds: int,
    ) -> WatchTarget:
        """Get or create a watch target.

        Args:
            retailer_slug: The retailer identifier.
            city: The city name.
            pincode: The postal code.
            keyword: The product search keyword.
            interval_seconds: The check interval in seconds.

        Returns:
            The watch target entity.
        """
        ...

    @abstractmethod
    async def list_due(self, now: datetime) -> list[WatchTarget]:
        """List watch targets that are due for checking.

        Args:
            now: The current datetime.

        Returns:
            A list of watch targets due for checking.
        """
        ...

    @abstractmethod
    async def mark_checked(self, watch_target_id: int, when: datetime) -> None:
        """Mark a watch target as checked.

        Args:
            watch_target_id: The watch target ID.
            when: The datetime of the check.
        """
        ...


class SnapshotRepository(ABC):
    """Repository for managing snapshots of product state."""

    @abstractmethod
    async def get_latest(self, watch_target_id: int) -> Snapshot | None:
        """Get the latest snapshot for a watch target.

        Args:
            watch_target_id: The watch target ID.

        Returns:
            The latest snapshot or None if no snapshots exist.
        """
        ...

    @abstractmethod
    async def create(
        self, watch_target_id: int, result: ProviderProductResult
    ) -> Snapshot:
        """Create a new snapshot from a provider result.

        Args:
            watch_target_id: The watch target ID.
            result: The provider product result.

        Returns:
            The created snapshot entity.
        """
        ...


class DetectionEventRepository(ABC):
    """Repository for managing detection events."""

    @abstractmethod
    async def create(
        self,
        watch_target_id: int,
        snapshot_id: int,
        previous_snapshot_id: int | None,
        event_type: EventType,
        when: datetime,
    ) -> DetectionEvent:
        """Create a new detection event.

        Args:
            watch_target_id: The watch target ID.
            snapshot_id: The snapshot ID.
            previous_snapshot_id: The previous snapshot ID, if any.
            event_type: The type of event detected.
            when: The datetime of the event.

        Returns:
            The created detection event entity.
        """
        ...

    @abstractmethod
    async def list_for_watch_target(
        self, watch_target_id: int, limit: int = 50
    ) -> list[DetectionEvent]:
        """List detection events for a watch target.

        Args:
            watch_target_id: The watch target ID.
            limit: Maximum number of events to return.

        Returns:
            A list of detection events.
        """
        ...
