"""Retailers endpoint router."""

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user_id, get_session
from app.api.schemas.retailers import RetailerSchema
from app.domain.ports.repositories import RetailerRepository
from app.infrastructure.db.repositories import SqlAlchemyRetailerRepository

router = APIRouter(prefix="/api/v1/retailers", tags=["retailers"])


def get_retailer_repository(
    session: AsyncSession = Depends(get_session),
) -> RetailerRepository:
    """Get a retailer repository instance.

    Args:
        session: The database session.

    Returns:
        A RetailerRepository implementation.
    """
    return SqlAlchemyRetailerRepository(session)


@router.get("", response_model=list[RetailerSchema])
async def list_retailers(
    user_id: int = Depends(get_current_user_id),
    repo: RetailerRepository = Depends(get_retailer_repository),
) -> list[RetailerSchema]:
    """List all retailers.

    Args:
        user_id: The authenticated user ID.
        repo: The retailer repository.

    Returns:
        A list of all available retailers.
    """
    retailers = await repo.list_all()
    return [
        RetailerSchema(slug=r.slug, name=r.name, is_active=r.is_active)
        for r in retailers
    ]
