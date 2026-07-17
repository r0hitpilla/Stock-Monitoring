from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.api.routers.products import get_product_repository, router
from app.domain.entities import Product


class FakeProductRepo:
    def __init__(self) -> None:
        self._products: dict[int, Product] = {}
        self._next_id = 1

    async def create(
        self, user_id: int, name: str, keyword: str, canonical_image_url: str | None
    ) -> Product:
        product = Product(
            id=self._next_id,
            user_id=user_id,
            name=name,
            keyword=keyword,
            canonical_image_url=canonical_image_url,
        )
        self._products[product.id] = product
        self._next_id += 1
        return product

    async def list_for_user(self, user_id: int) -> list[Product]:
        return [p for p in self._products.values() if p.user_id == user_id]

    async def get_by_id(self, product_id: int) -> Product | None:
        return self._products.get(product_id)

    async def delete(self, product_id: int) -> None:
        self._products.pop(product_id, None)


def _build_app(repo: FakeProductRepo, user_id: int = 10) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    app.dependency_overrides[get_product_repository] = lambda: repo
    return app


def test_create_and_list_products():
    repo = FakeProductRepo()
    client = TestClient(_build_app(repo))

    create_response = client.post(
        "/api/v1/products", json={"name": "Milk", "keyword": "amul milk 500ml"}
    )
    assert create_response.status_code == 201

    list_response = client.get("/api/v1/products")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["keyword"] == "amul milk 500ml"


def test_delete_product_owned_by_someone_else_returns_404():
    repo = FakeProductRepo()
    client_owner = TestClient(_build_app(repo, user_id=1))
    client_owner.post("/api/v1/products", json={"name": "Milk", "keyword": "milk"})

    client_other = TestClient(_build_app(repo, user_id=2))
    response = client_other.delete("/api/v1/products/1")

    assert response.status_code == 404
