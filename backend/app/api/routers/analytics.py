"""Analytics endpoint router."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_session
from app.api.schemas.analytics import AvailabilitySummarySchema, PricePointSchema
from app.application.analytics import compute_availability_summary
from app.domain.entities import Watch
from app.domain.ports.repositories import (
    DetectionEventRepository,
    SnapshotRepository,
    WatchRepository,
)
from app.infrastructure.db.repositories import (
    SqlAlchemyDetectionEventRepository,
    SqlAlchemySnapshotRepository,
    SqlAlchemyWatchRepository,
)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


def get_watch_repository(
    session: AsyncSession = Depends(get_session),
) -> WatchRepository:
    """Get a watch repository instance.

    Args:
        session: The database session.

    Returns:
        A WatchRepository implementation.
    """
    return SqlAlchemyWatchRepository(session)


def get_snapshot_repository(
    session: AsyncSession = Depends(get_session),
) -> SnapshotRepository:
    """Get a snapshot repository instance.

    Args:
        session: The database session.

    Returns:
        A SnapshotRepository implementation.
    """
    return SqlAlchemySnapshotRepository(session)


def get_detection_event_repository(
    session: AsyncSession = Depends(get_session),
) -> DetectionEventRepository:
    """Get a detection event repository instance.

    Args:
        session: The database session.

    Returns:
        A DetectionEventRepository implementation.
    """
    return SqlAlchemyDetectionEventRepository(session)


async def _owned_watch(
    watch_id: int, user_id: int, watch_repo: WatchRepository
) -> Watch:
    """Look up a watch and verify it belongs to the given user.

    Args:
        watch_id: The ID of the watch to look up.
        user_id: The authenticated user ID.
        watch_repo: The watch repository.

    Returns:
        The owned watch entity.

    Raises:
        HTTPException: With 404 status if watch not found or belongs to another user.
    """
    watch = await watch_repo.get_by_id(watch_id)
    if watch is None or watch.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Watch not found")
    return watch


@router.get("/price-history", response_model=list[PricePointSchema])
async def price_history(
    watch_id: int,
    days: int = 30,
    user_id: int = Depends(get_current_user_id),
    watch_repo: WatchRepository = Depends(get_watch_repository),
    snapshot_repo: SnapshotRepository = Depends(get_snapshot_repository),
) -> list[PricePointSchema]:
    """Get price history points for a watch over a trailing window.

    Verifies that the watch belongs to the authenticated user before returning
    price points scoped to the trailing `days`-day window.

    Args:
        watch_id: The ID of the watch to get price history for.
        days: Size of the trailing window, in days. Defaults to 30.
        user_id: The authenticated user ID.
        watch_repo: The watch repository.
        snapshot_repo: The snapshot repository.

    Returns:
        A list of price points ordered by timestamp ascending.

    Raises:
        HTTPException: With 404 status if watch not found or belongs to another user.
    """
    watch = await _owned_watch(watch_id, user_id, watch_repo)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    snapshots = await snapshot_repo.list_since(watch.watch_target_id, since)
    return [
        PricePointSchema(timestamp=s.timestamp.isoformat(), price=s.price)
        for s in snapshots
    ]


@router.get("/availability", response_model=AvailabilitySummarySchema)
async def availability_summary(
    watch_id: int,
    days: int = 30,
    user_id: int = Depends(get_current_user_id),
    watch_repo: WatchRepository = Depends(get_watch_repository),
    event_repo: DetectionEventRepository = Depends(get_detection_event_repository),
) -> AvailabilitySummarySchema:
    """Get availability/restock metrics for a watch over a trailing window.

    Verifies that the watch belongs to the authenticated user, then scopes
    detection events to the trailing `days`-day window (via `since`) before
    computing the summary, so events from before `period_start` cannot skew
    the result.

    Args:
        watch_id: The ID of the watch to get the availability summary for.
        days: Size of the trailing window, in days. Defaults to 30.
        user_id: The authenticated user ID.
        watch_repo: The watch repository.
        event_repo: The detection event repository.

    Returns:
        The computed availability summary for the window.

    Raises:
        HTTPException: With 404 status if watch not found or belongs to another user.
    """
    watch = await _owned_watch(watch_id, user_id, watch_repo)
    period_end = datetime.now(timezone.utc)
    period_start = period_end - timedelta(days=days)
    events = await event_repo.list_for_watch_target(
        watch.watch_target_id, limit=1000, since=period_start
    )
    summary = compute_availability_summary(events, period_start, period_end)
    return AvailabilitySummarySchema(
        availability_pct=summary.availability_pct,
        restock_count=summary.restock_count,
        total_downtime_minutes=summary.total_downtime_minutes,
        average_downtime_minutes=summary.average_downtime_minutes,
    )
