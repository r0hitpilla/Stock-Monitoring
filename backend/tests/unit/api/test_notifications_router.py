from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.api.routers.notifications import (
    get_notification_channel_repository,
    get_notification_log_repository,
    router,
)
from app.domain.entities import NotificationChannel
from app.domain.enums import NotificationChannelType


class FakeChannelRepo:
    def __init__(self) -> None:
        self._channels: dict[int, NotificationChannel] = {}
        self._next_id = 1

    async def create(self, user_id, type, config, is_verified=False):
        channel = NotificationChannel(
            id=self._next_id,
            user_id=user_id,
            type=type,
            config=config,
            is_verified=is_verified,
        )
        self._channels[channel.id] = channel
        self._next_id += 1
        return channel

    async def list_for_user(self, user_id: int):
        return [c for c in self._channels.values() if c.user_id == user_id]

    async def get_by_id(self, channel_id: int):
        return self._channels.get(channel_id)

    async def delete(self, channel_id: int) -> None:
        self._channels.pop(channel_id, None)

    async def mark_verified(self, channel_id: int) -> None:
        self._channels[channel_id].is_verified = True


class FakeLogRepo:
    async def list_for_user(self, user_id: int, limit: int = 50):
        return []


def _build_app(user_id: int = 10) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    channel_repo = FakeChannelRepo()
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    app.dependency_overrides[get_notification_channel_repository] = lambda: channel_repo
    app.dependency_overrides[get_notification_log_repository] = lambda: FakeLogRepo()
    return app


def test_create_channel_then_verify_it():
    app = _build_app()
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/notifications/channels",
        json={"type": "telegram", "config": {"chat_id": "123"}},
    )
    assert create_response.status_code == 201
    channel_id = create_response.json()["id"]
    assert create_response.json()["is_verified"] is False

    verify_response = client.post(f"/api/v1/notifications/channels/{channel_id}/verify")
    assert verify_response.status_code == 200

    list_response = client.get("/api/v1/notifications/channels")
    assert list_response.json()[0]["is_verified"] is True
