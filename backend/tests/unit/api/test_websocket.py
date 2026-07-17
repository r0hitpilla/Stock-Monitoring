import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api.deps import get_auth_service
from app.api.websocket import get_redis_subscriber, get_watch_repository, router
from app.application.exceptions import InvalidTokenError
from app.domain.entities import Watch


class FakeAuthService:
    def verify_access_token(self, token: str) -> int:
        if token == "valid-token":
            return 10
        raise InvalidTokenError("bad token")


class FakeWatchRepo:
    def __init__(self, watches: list[Watch]) -> None:
        self._watches = watches

    async def list_for_user(self, user_id: int):
        return self._watches


class FakeSubscriber:
    def __init__(self, messages: list[dict]) -> None:
        self._messages = messages

    async def listen(self, channels: list[str]):
        for message in self._messages:
            yield message


def _build_app(watches, messages) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_watch_repository] = lambda: FakeWatchRepo(watches)
    app.dependency_overrides[get_redis_subscriber] = lambda: FakeSubscriber(messages)
    return app


def test_websocket_streams_events_for_users_watch_targets():
    watch = Watch(
        id=1, user_id=10, product_id=1, watch_target_id=7, interval_seconds=300
    )
    app = _build_app([watch], [{"event_type": "stock_available"}])
    client = TestClient(app)

    with client.websocket_connect("/ws?token=valid-token") as websocket:
        data = websocket.receive_json()

    assert data == {"event_type": "stock_available"}


def test_websocket_closes_with_4401_on_invalid_token():
    app = _build_app([], [])
    client = TestClient(app)

    # The server closes the connection with code 4401 before accepting it,
    # so the close is surfaced as a WebSocketDisconnect raised on connect,
    # not on a subsequent receive.
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws?token=garbage") as websocket:
            websocket.receive_json()

    assert exc_info.value.code == 4401


def test_websocket_closes_with_4404_when_user_has_no_watches():
    app = _build_app([], [])
    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws?token=valid-token") as websocket:
            websocket.receive_json()

    assert exc_info.value.code == 4404
