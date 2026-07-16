import pytest
from sqlalchemy import text

from app.infrastructure.db.models import Base
from app.infrastructure.db.session import get_engine


@pytest.mark.asyncio
async def test_create_all_tables_and_watch_target_dedup_constraint():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        tables = {row[0] for row in result.fetchall()}

    assert "watch_targets" in tables
    assert "users" in tables
    assert "snapshots" in tables
    await engine.dispose()
