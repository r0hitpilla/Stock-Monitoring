from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.api.routers.retailers import get_retailer_repository, router
from app.domain.entities import Retailer


class FakeRetailerRepo:
    async def list_all(self) -> list[Retailer]:
        return [
            Retailer(id=1, slug="blinkit", name="Blinkit", is_active=True),
            Retailer(id=2, slug="zepto", name="Zepto", is_active=True),
        ]


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user_id] = lambda: 1
    app.dependency_overrides[get_retailer_repository] = lambda: FakeRetailerRepo()
    return app


def test_list_retailers_returns_seeded_retailers() -> None:
    client = TestClient(_build_app())

    response = client.get("/api/v1/retailers")

    assert response.status_code == 200
    slugs = [r["slug"] for r in response.json()]
    assert slugs == ["blinkit", "zepto"]
