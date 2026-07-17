"""Celery application factory."""

from celery import Celery

from app.core.config import get_settings


def create_celery_app() -> Celery:
    """Create and configure the Celery application.

    Returns:
        Configured Celery application instance.
    """
    settings = get_settings()
    app = Celery(
        "inventory_monitor",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=["app.tasks.notifications"],
    )
    app.conf.task_routes = {"app.tasks.notifications.*": {"queue": "notifications"}}
    return app


celery_app = create_celery_app()
