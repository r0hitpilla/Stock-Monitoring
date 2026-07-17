"""WebSocket route streaming live detection events to authenticated clients."""

import structlog
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_auth_service
from app.application.auth_service import AuthService
from app.application.exceptions import InvalidTokenError
from app.domain.ports.repositories import WatchRepository
from app.infrastructure.cache.redis_subscriber import RedisSubscriber
from app.infrastructure.db.repositories import SqlAlchemyWatchRepository

logger = structlog.get_logger(__name__)

router = APIRouter()


def get_watch_repository(session: AsyncSession) -> WatchRepository:
    """Build a `WatchRepository` bound to the given session.

    Not a FastAPI dependency: constructing a repository does no I/O of its
    own, so this is called directly inside `websocket_endpoint`, within a
    short-lived `async with session_factory() as session:` block scoped
    tightly around the one `list_for_user` lookup. That keeps the DB
    session (and its pooled connection) held only for that lookup rather
    than for the WebSocket connection's full, potentially long-lived,
    streaming lifetime.

    Args:
        session: A session from the app-wide session factory (see
            `app.api.main.lifespan`).

    Returns:
        A `SqlAlchemyWatchRepository` bound to `session`.
    """
    return SqlAlchemyWatchRepository(session)


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

    The watch lookup opens its own short-lived DB session (via
    `websocket.app.state.session_factory`) that is closed immediately after
    the lookup, well before the long-lived streaming loop begins, so the
    connection's pooled DB session isn't held for the WebSocket's full
    lifetime.

    Args:
        websocket: The incoming WebSocket connection.
        token: The caller's JWT access token, passed as a query parameter.
        auth_service: Service used to verify the access token.
        subscriber: Subscriber used to consume live detection events.
    """
    try:
        user_id = auth_service.verify_access_token(token)
    except InvalidTokenError:
        logger.info("websocket_rejected_invalid_token")
        await websocket.close(code=4401)
        return

    session_factory = websocket.app.state.session_factory
    async with session_factory() as session:
        watch_repo = get_watch_repository(session)
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
