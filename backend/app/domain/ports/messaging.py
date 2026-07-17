"""Abstract messaging ports for the domain layer.

These ports decouple the application layer from any concrete messaging
technology (e.g. Redis pub/sub for events, Celery for task dispatch).
Concrete adapters are implemented in the infrastructure layer.
"""

from abc import ABC, abstractmethod

from app.domain.entities import DetectionEvent


class EventPublisher(ABC):
    """Publishes detection events to interested subscribers."""

    @abstractmethod
    async def publish(self, watch_target_id: int, event: DetectionEvent) -> None:
        """Publish a detection event for a given watch target.

        Args:
            watch_target_id: The watch target the event belongs to.
            event: The detection event to publish.
        """
        ...


class TaskDispatcher(ABC):
    """Dispatches background jobs in response to domain events."""

    @abstractmethod
    def dispatch_detection_event(self, event_id: int) -> None:
        """Dispatch a background job (e.g. a notification task) for an event.

        Args:
            event_id: The ID of the detection event to process.
        """
        ...
