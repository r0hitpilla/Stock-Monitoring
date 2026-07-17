"""Abstract repository interfaces for domain layer."""

from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities import (
    DetectionEvent,
    NotificationChannel,
    NotificationLog,
    OtpChallenge,
    ProviderProductResult,
    Retailer,
    Snapshot,
    User,
    Watch,
    WatchTarget,
)
from app.domain.enums import EventType


class UserRepository(ABC):
    """Repository for managing user accounts."""

    @abstractmethod
    async def get_or_create_by_phone(self, phone_number: str) -> User:
        """Get an existing user by phone number, or create one.

        Args:
            phone_number: The user's phone number.

        Returns:
            The existing or newly created user entity.
        """
        ...

    @abstractmethod
    async def get_by_id(self, user_id: int) -> User | None:
        """Get a user by ID.

        Args:
            user_id: The user ID.

        Returns:
            The user entity or None if not found.
        """
        ...


class OtpChallengeRepository(ABC):
    """Repository for managing OTP challenges."""

    @abstractmethod
    async def create(
        self,
        phone_number: str,
        code_hash: str,
        expires_at: datetime,
        created_at: datetime,
    ) -> OtpChallenge:
        """Create a new OTP challenge.

        Args:
            phone_number: The phone number the challenge is for.
            code_hash: The hashed OTP code.
            expires_at: When the challenge expires.
            created_at: When the challenge was created.

        Returns:
            The created OTP challenge entity.
        """
        ...

    @abstractmethod
    async def get_latest(self, phone_number: str) -> OtpChallenge | None:
        """Get the most recently created OTP challenge for a phone number.

        Args:
            phone_number: The phone number to look up.

        Returns:
            The latest OTP challenge, or None if none exist.
        """
        ...

    @abstractmethod
    async def count_recent(self, phone_number: str, window_seconds: int) -> int:
        """Count OTP challenges created for a phone number within a time window.

        Args:
            phone_number: The phone number to look up.
            window_seconds: The size of the recency window, in seconds.

        Returns:
            The number of challenges created within the window.
        """
        ...

    @abstractmethod
    async def mark_consumed(self, challenge_id: int) -> None:
        """Mark an OTP challenge as consumed.

        Args:
            challenge_id: The OTP challenge ID.
        """
        ...

    @abstractmethod
    async def increment_attempt(self, challenge_id: int) -> None:
        """Increment the attempt count of an OTP challenge.

        Args:
            challenge_id: The OTP challenge ID.
        """
        ...


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
    async def get_by_id(self, watch_target_id: int) -> WatchTarget | None:
        """Get a watch target by ID.

        Args:
            watch_target_id: The watch target ID.

        Returns:
            The watch target entity or None if not found.
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
    async def get_by_id(self, snapshot_id: int) -> Snapshot | None:
        """Get a snapshot by ID.

        Args:
            snapshot_id: The snapshot ID.

        Returns:
            The snapshot entity or None if not found.
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
    async def get_by_id(self, event_id: int) -> DetectionEvent | None:
        """Get a detection event by ID.

        Args:
            event_id: The detection event ID.

        Returns:
            The detection event entity or None if not found.
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


class RetailerRepository(ABC):
    """Repository for managing retailers."""

    @abstractmethod
    async def list_all(self) -> list[Retailer]:
        """List all retailers.

        Returns:
            A list of all retailers.
        """
        ...


class WatchRepository(ABC):
    """Repository for managing user watches."""

    @abstractmethod
    async def list_by_watch_target(self, watch_target_id: int) -> list[Watch]:
        """List watches for a watch target.

        Args:
            watch_target_id: The watch target ID.

        Returns:
            A list of watches for the target.
        """
        ...

    @abstractmethod
    async def get_by_id(self, watch_id: int) -> Watch | None:
        """Get a watch by ID.

        Args:
            watch_id: The watch ID.

        Returns:
            The watch entity or None if not found.
        """
        ...


class NotificationChannelRepository(ABC):
    """Repository for managing user notification channels."""

    @abstractmethod
    async def list_for_user(self, user_id: int) -> list[NotificationChannel]:
        """List notification channels for a user.

        Args:
            user_id: The user ID.

        Returns:
            A list of notification channels for the user.
        """
        ...


class NotificationLogRepository(ABC):
    """Repository for managing notification logs."""

    @abstractmethod
    async def exists_recent(self, dedup_key: str, cooldown_seconds: int) -> bool:
        """Check if a notification was recently sent for a dedup key.

        Args:
            dedup_key: The deduplication key.
            cooldown_seconds: The cooldown period in seconds.

        Returns:
            True if a notification with this key was sent within the cooldown period.
        """
        ...

    @abstractmethod
    async def create(
        self,
        user_id: int,
        detection_event_id: int,
        channel_id: int,
        status: str,
        dedup_key: str,
    ) -> NotificationLog:
        """Create a new notification log entry.

        Args:
            user_id: The user ID.
            detection_event_id: The detection event ID.
            channel_id: The notification channel ID.
            status: The notification status (e.g., "sent", "failed").
            dedup_key: The deduplication key.

        Returns:
            The created notification log entity.
        """
        ...
