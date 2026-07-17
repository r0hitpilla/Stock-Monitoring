"""Celery-based task dispatcher adapter."""

from typing import Any, Protocol

from app.domain.ports.messaging import TaskDispatcher


class CeleryAppLike(Protocol):
    """Protocol for Celery app instances with send_task capability."""

    def send_task(self, name: str, args: list[Any]) -> Any:
        """Send a task by name string.

        Args:
            name: The fully-qualified task name (e.g. 'app.tasks.notifications.process_detection_event').
            args: List of positional arguments to pass to the task.

        Returns:
            An AsyncResult or similar task reference.
        """
        ...


class CeleryTaskDispatcher(TaskDispatcher):
    """Dispatches background tasks via Celery by task name string."""

    def __init__(self, celery_app: CeleryAppLike) -> None:
        """Initialize with a Celery app instance.

        Args:
            celery_app: Any object exposing send_task(name, args).
        """
        self._celery_app = celery_app

    def dispatch_detection_event(self, event_id: int) -> None:
        """Dispatch a background task to process a detection event.

        Args:
            event_id: The ID of the detection event to process.
        """
        self._celery_app.send_task(
            "app.tasks.notifications.process_detection_event", args=[event_id]
        )
