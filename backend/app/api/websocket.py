"""WebSocket route streaming live detection events to authenticated clients."""

from typing import AsyncIterator

import structlog
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.api.deps import get_auth_service
from app.application.auth_service import AuthService
from app.application.exceptions import InvalidTokenError
from app.domain.ports.repositories import WatchRepository
from app.infrastructure.cache.redis_subscriber import RedisSubscriber
from app.infrastructure.db.repositories import SqlAlchemyWatchRepository

logger = structlog.get_logger(__name__)

router = APIRouter()


async def get_watch_repository(websocket: WebSocket) -> AsyncIterator[WatchRepository]:
    """Yield a `WatchRepository` backed by a session from the app-wide session factory.

    Args:
        websocket: The connecting WebSocket, used to reach the shared
            `session_factory` built once at app startup (see `app.api.main.lifespan`).

    Yields:
        A `SqlAlchemyWatchRepository` bound to a session that is closed
        when the dependency scope exits. The underlying engine/connection
        pool is reused across connections rather than rebuilt per-connection.
    """
    session_factory = websocket.app.state.session_factory
    async with session_factory() as session:
        yield SqlAlchemyWatchRepository(session)


def get_redis_subscriber(websocket: WebSocket) -> RedisSubscriber:
    """Return a `RedisSubscriber` backed by the app-wide shared Redis client.

    Args:
        websocket: The connecting WebSocket, used to reach the shared
            `redis_client` built once at app startup (see `app.api.main.lifespan`)
            and closed at shutdown.

    Returns:
        A `RedisSubscriber` wrapping the shared `redis.asyncio.Redis` client.
    """
    # redis-py's PubSub/Redis types don't structurally match our minimal
    # RedisClientLike/PubSubLike protocols exactly (extra kwargs, differing
    # return types); structurally compatible at runtime. See the same
    # pattern in app/monitor/main.py for RedisEventPublisher.
    return RedisSubscriber(websocket.app.state.redis_client)  # type: ignore[arg-type]


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    auth_service: AuthService = Depends(get_auth_service),
    watch_repo: WatchRepository = Depends(get_watch_repository),
    subscriber: RedisSubscriber = Depends(get_redis_subscriber),
) -> None:
    """Stream live detection events for the authenticated caller's watches.

    Validates `token` via `AuthService.verify_access_token`, closing the
    connection with code 4401 if it is invalid or expired. Loads the
    caller's active watches via `WatchRepository.list_for_user`, closing
    with code 4404 if they have none. Otherwise accepts the connection and
    forwards every message from `RedisSubscriber.listen` (scoped to the
    caller's own watch-target channels) to the client as JSON until the
    client disconnects.

    Args:
        websocket: The incoming WebSocket connection.
        token: The caller's JWT access token, passed as a query parameter.
        auth_service: Service used to verify the access token.
        watch_repo: Repository used to load the caller's watches.
        subscriber: Subscriber used to consume live detection events.
    """
    try:
        user_id = auth_service.verify_access_token(token)
    except InvalidTokenError:
        logger.info("websocket_rejected_invalid_token")
        await websocket.close(code=4401)
        return

    watches = await watch_repo.list_for_user(user_id)
    if not watches:
        logger.info("websocket_rejected_no_active_watches", user_id=user_id)
        await websocket.close(code=4404)
        return

    await websocket.accept()
    channels = [f"events:{watch.watch_target_id}" for watch in watches]
    try:
        async for message in subscriber.listen(channels):
            await websocket.send_json(message)
    except WebSocketDisconnect:
        logger.debug("websocket_client_disconnected", user_id=user_id)
