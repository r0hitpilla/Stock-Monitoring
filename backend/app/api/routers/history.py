"""History endpoint router."""

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user_id, get_session
from app.api.schemas.history import HistoryEntrySchema, SnapshotSchema
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

router = APIRouter(prefix="/api/v1/history", tags=["history"])


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


@router.get("", response_model=list[HistoryEntrySchema])
async def get_history(
    watch_id: int,
    user_id: int = Depends(get_current_user_id),
    watch_repo: WatchRepository = Depends(get_watch_repository),
    event_repo: DetectionEventRepository = Depends(get_detection_event_repository),
    snapshot_repo: SnapshotRepository = Depends(get_snapshot_repository),
) -> list[HistoryEntrySchema]:
    """Get detection event history for a watch.

    Verifies that the watch belongs to the authenticated user before returning events.
    Returns events newest-first with associated snapshots.

    Args:
        watch_id: The ID of the watch to get history for.
        user_id: The authenticated user ID.
        watch_repo: The watch repository.
        event_repo: The detection event repository.
        snapshot_repo: The snapshot repository.

    Returns:
        A list of history entries (detection events with snapshots) newest-first.

    Raises:
        HTTPException: With 404 status if watch not found or belongs to another user.
    """
    watch = await watch_repo.get_by_id(watch_id)
    if watch is None or watch.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Watch not found")

    events = await event_repo.list_for_watch_target(watch.watch_target_id)
    entries = []
    for event in events:
        snapshot = await snapshot_repo.get_by_id(event.snapshot_id)
        if snapshot is None:
            continue
        entries.append(
            HistoryEntrySchema(
                event_id=event.id,
                event_type=event.event_type.value,
                created_at=event.created_at,
                snapshot=SnapshotSchema(
                    availability=(
                        snapshot.availability.value
                        if hasattr(snapshot.availability, "value")
                        else snapshot.availability
                    ),
                    price=snapshot.price,
                    mrp=snapshot.mrp,
                    discount_pct=snapshot.discount_pct,
                    eta_minutes=snapshot.eta_minutes,
                    store_name=snapshot.store_name,
                    image_url=snapshot.image_url,
                    quantity_label=snapshot.quantity_label,
                    variants=snapshot.variants,
                    product_url=snapshot.product_url,
                ),
            )
        )
    return entries
