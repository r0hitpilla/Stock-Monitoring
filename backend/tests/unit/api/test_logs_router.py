from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.api.routers.logs import get_system_log_repository, router
from app.domain.entities import SystemLog


class FakeSystemLogRepo:
    async def list_recent(self, limit: int = 100):
        return [
            SystemLog(
                id=1,
                level="error",
                message="provider crashed",
                context={},
                created_at=datetime.now(timezone.utc),
            )
        ]


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user_id] = lambda: 10
    app.dependency_overrides[get_system_log_repository] = lambda: FakeSystemLogRepo()
    return app


def test_list_logs_returns_recent_entries():
    client = TestClient(_build_app())

    response = client.get("/api/v1/logs")

    assert response.status_code == 200
    assert response.json()[0]["message"] == "provider crashed"
