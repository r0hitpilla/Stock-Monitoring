"""Process entrypoint for the monitor service.

Wires up the database session, repositories, provider registry, Redis
client, Celery app, and `MonitoringService`, then runs the `Scheduler`
forever until a `SIGTERM`/`SIGINT` triggers graceful shutdown (cancelling
the scheduling loop and closing every provider that was instantiated
during the run).
"""

import asyncio
import signal

import redis.asyncio as redis
from celery import Celery

from app.application.monitoring_service import MonitoringService
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.infrastructure.cache.redis_publisher import RedisEventPublisher
from app.infrastructure.db.repositories import (
    SqlAlchemyDetectionEventRepository,
    SqlAlchemySnapshotRepository,
    SqlAlchemyWatchTargetRepository,
)
from app.infrastructure.db.session import get_engine, get_sessionmaker
from app.infrastructure.providers.bigbasket.provider import BigBasketProvider
from app.infrastructure.providers.blinkit.provider import BlinkitProvider
from app.infrastructure.providers.instamart.provider import InstamartProvider
from app.infrastructure.providers.registry import InMemoryProviderRegistry
from app.infrastructure.providers.zepto.provider import ZeptoProvider
from app.infrastructure.tasks_dispatch import CeleryTaskDispatcher
from app.monitor.scheduler import Scheduler


async def main() -> None:
    """Build all collaborators and run the scheduler until signalled to stop."""
    settings = get_settings()
    configure_logging(settings)

    engine = get_engine(settings.database_url)
    session_factory = get_sessionmaker(engine)
    redis_client = redis.from_url(settings.redis_url)
    celery_app = Celery("monitor", broker=settings.redis_url)

    provider_registry = InMemoryProviderRegistry(
        {
            "blinkit": BlinkitProvider,
            "zepto": ZeptoProvider,
            "instamart": InstamartProvider,
            "bigbasket": BigBasketProvider,
        }
    )

    async with session_factory() as session:
        scheduler = Scheduler(
            watch_target_repo=SqlAlchemyWatchTargetRepository(session),
            monitoring_service=MonitoringService(
                provider_registry=provider_registry,
                watch_target_repo=SqlAlchemyWatchTargetRepository(session),
                snapshot_repo=SqlAlchemySnapshotRepository(session),
                event_repo=SqlAlchemyDetectionEventRepository(session),
                # redis-py's Redis.publish() returns Awaitable[int] rather
                # than the Coroutine[Any, Any, int] declared by the
                # RedisLike protocol; structurally compatible at runtime.
                event_publisher=RedisEventPublisher(redis_client),  # type: ignore[arg-type]
                task_dispatcher=CeleryTaskDispatcher(celery_app),
            ),
        )

        loop = asyncio.get_running_loop()
        stop_event = asyncio.Event()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop_event.set)

        run_task = asyncio.create_task(scheduler.run_forever())
        await stop_event.wait()
        run_task.cancel()

        for slug in provider_registry.list_active_slugs():
            await provider_registry.get(slug).close()
        await redis_client.aclose()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
