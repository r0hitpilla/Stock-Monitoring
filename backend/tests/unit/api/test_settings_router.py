from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.api.routers.settings import get_settings_repository, router


class FakeSettingsRepo:
    def __init__(self) -> None:
        self._store: dict[int, dict] = {}

    async def get_for_user(self, user_id: int):
        return self._store.get(user_id, {})

    async def set_for_user(self, user_id: int, key: str, value) -> None:
        self._store.setdefault(user_id, {})[key] = value


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    settings_repo = FakeSettingsRepo()
    app.dependency_overrides[get_current_user_id] = lambda: 10
    app.dependency_overrides[get_settings_repository] = lambda: settings_repo
    return app


def test_set_then_get_setting():
    client = TestClient(_build_app())

    put_response = client.put(
        "/api/v1/settings", json={"key": "timezone", "value": "Asia/Kolkata"}
    )
    assert put_response.status_code == 200

    get_response = client.get("/api/v1/settings")
    assert get_response.json() == {"timezone": "Asia/Kolkata"}
