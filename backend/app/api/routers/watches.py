from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user_id, get_session
from app.api.schemas.watches import WatchCreateSchema, WatchSchema
from app.domain.ports.repositories import (
    ProductRepository,
    WatchRepository,
    WatchTargetRepository,
)
from app.infrastructure.db.repositories import (
    SqlAlchemyProductRepository,
    SqlAlchemyWatchRepository,
    SqlAlchemyWatchTargetRepository,
)

router = APIRouter(prefix="/api/v1/watches", tags=["watches"])


def get_product_repository(
    session: AsyncSession = Depends(get_session),
) -> ProductRepository:
    return SqlAlchemyProductRepository(session)


def get_watch_target_repository(
    session: AsyncSession = Depends(get_session),
) -> WatchTargetRepository:
    return SqlAlchemyWatchTargetRepository(session)


def get_watch_repository(
    session: AsyncSession = Depends(get_session),
) -> WatchRepository:
    return SqlAlchemyWatchRepository(session)


@router.post("", response_model=WatchSchema, status_code=status.HTTP_201_CREATED)
async def create_watch(
    body: WatchCreateSchema,
    user_id: int = Depends(get_current_user_id),
    product_repo: ProductRepository = Depends(get_product_repository),
    watch_target_repo: WatchTargetRepository = Depends(get_watch_target_repository),
    watch_repo: WatchRepository = Depends(get_watch_repository),
) -> WatchSchema:
    product = await product_repo.get_by_id(body.product_id)
    if product is None or product.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    watch_target = await watch_target_repo.get_or_create(
        body.retailer_slug,
        body.city,
        body.pincode,
        product.keyword,
        body.interval_seconds,
    )
    assert product.id is not None
    assert watch_target.id is not None
    watch = await watch_repo.create(
        user_id, product.id, watch_target.id, body.interval_seconds
    )
    return WatchSchema(
        id=watch.id,
        product_id=watch.product_id,
        watch_target_id=watch.watch_target_id,
        interval_seconds=watch.interval_seconds,
        is_active=watch.is_active,
    )


@router.get("", response_model=list[WatchSchema])
async def list_watches(
    user_id: int = Depends(get_current_user_id),
    watch_repo: WatchRepository = Depends(get_watch_repository),
) -> list[WatchSchema]:
    watches = await watch_repo.list_for_user(user_id)
    return [
        WatchSchema(
            id=w.id,
            product_id=w.product_id,
            watch_target_id=w.watch_target_id,
            interval_seconds=w.interval_seconds,
            is_active=w.is_active,
        )
        for w in watches
    ]


@router.delete("/{watch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watch(
    watch_id: int,
    user_id: int = Depends(get_current_user_id),
    watch_repo: WatchRepository = Depends(get_watch_repository),
) -> None:
    watch = await watch_repo.get_by_id(watch_id)
    if watch is None or watch.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Watch not found")
    await watch_repo.deactivate(watch_id)
