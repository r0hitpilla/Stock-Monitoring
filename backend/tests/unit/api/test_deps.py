from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_auth_service, get_current_user_id
from app.application.exceptions import InvalidTokenError


class FakeAuthService:
    def verify_access_token(self, token: str) -> int:
        if token == "valid-token":
            return 7
        raise InvalidTokenError("bad token")


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()

    @app.get("/whoami")
    async def whoami(user_id: int = Depends(get_current_user_id)):
        return {"user_id": user_id}

    return app


def test_get_current_user_id_returns_user_id_for_valid_bearer_token():
    client = TestClient(_build_test_app())
    response = client.get("/whoami", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    assert response.json() == {"user_id": 7}


def test_get_current_user_id_rejects_missing_header():
    client = TestClient(_build_test_app())
    response = client.get("/whoami")
    assert response.status_code == 401


def test_get_current_user_id_rejects_invalid_token():
    client = TestClient(_build_test_app())
    response = client.get("/whoami", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401
