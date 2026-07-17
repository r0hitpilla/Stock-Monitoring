from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_session
from app.api.schemas.logs import SystemLogSchema
from app.domain.ports.repositories import SystemLogRepository
from app.infrastructure.db.repositories import SqlAlchemySystemLogRepository

router = APIRouter(prefix="/api/v1/logs", tags=["logs"])


def get_system_log_repository(
    session: AsyncSession = Depends(get_session),
) -> SystemLogRepository:
    """Provide a SystemLogRepository backed by the request's DB session."""
    return SqlAlchemySystemLogRepository(session)


@router.get("", response_model=list[SystemLogSchema])
async def list_logs(
    user_id: int = Depends(get_current_user_id),
    repo: SystemLogRepository = Depends(get_system_log_repository),
) -> list[SystemLogSchema]:
    """List the most recent system log entries, most recent first."""
    logs = await repo.list_recent()
    return [
        SystemLogSchema(
            id=log.id,
            level=log.level,
            message=log.message,
            context=log.context,
            created_at=log.created_at,
        )
        for log in logs
    ]
