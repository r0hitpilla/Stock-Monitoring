from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.api.routers.watches import (
    get_product_repository,
    get_watch_repository,
    get_watch_target_repository,
    router,
)
from app.domain.entities import Product, Watch, WatchTarget


class FakeProductRepo:
    def __init__(self, product: Product | None) -> None:
        self._product = product

    async def get_by_id(self, product_id: int) -> Product | None:
        return self._product


class FakeWatchTargetRepo:
    async def get_or_create(
        self,
        retailer_slug: str,
        city: str,
        pincode: str,
        keyword: str,
        interval_seconds: int,
    ) -> WatchTarget:
        return WatchTarget(
            id=99,
            retailer_slug=retailer_slug,
            city=city,
            pincode=pincode,
            keyword=keyword,
            interval_seconds=interval_seconds,
        )


class FakeWatchRepo:
    def __init__(self) -> None:
        self.created: list[Watch] = []

    async def create(
        self, user_id: int, product_id: int, watch_target_id: int, interval_seconds: int
    ) -> Watch:
        watch = Watch(
            id=1,
            user_id=user_id,
            product_id=product_id,
            watch_target_id=watch_target_id,
            interval_seconds=interval_seconds,
        )
        self.created.append(watch)
        return watch

    async def list_for_user(self, user_id: int) -> list[Watch]:
        return [w for w in self.created if w.user_id == user_id]


def _build_app(product: Product | None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user_id] = lambda: 10
    app.dependency_overrides[get_product_repository] = lambda: FakeProductRepo(product)
    app.dependency_overrides[get_watch_target_repository] = lambda: FakeWatchTargetRepo()
    app.dependency_overrides[get_watch_repository] = lambda: FakeWatchRepo()
    return app


def test_create_watch_dedupes_via_watch_target_and_returns_it():
    product = Product(
        id=1,
        user_id=10,
        name="Milk",
        keyword="amul milk 500ml",
        canonical_image_url=None,
    )
    client = TestClient(_build_app(product))

    response = client.post(
        "/api/v1/watches",
        json={
            "product_id": 1,
            "retailer_slug": "blinkit",
            "city": "Bengaluru",
            "pincode": "560001",
            "interval_seconds": 300,
        },
    )

    assert response.status_code == 201
    assert response.json()["watch_target_id"] == 99


def test_create_watch_for_someone_elses_product_returns_404():
    product = Product(
        id=1, user_id=999, name="Milk", keyword="milk", canonical_image_url=None
    )
    client = TestClient(_build_app(product))

    response = client.post(
        "/api/v1/watches",
        json={
            "product_id": 1,
            "retailer_slug": "blinkit",
            "city": "Bengaluru",
            "pincode": "560001",
            "interval_seconds": 300,
        },
    )

    assert response.status_code == 404
