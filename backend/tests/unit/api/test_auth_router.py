from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_auth_service
from app.api.routers.auth import router
from app.application.exceptions import InvalidOtpError, RateLimitExceededError
from app.domain.entities import TokenPair


class FakeAuthService:
    def __init__(self, fail_request: bool = False, fail_verify: bool = False) -> None:
        self.requested: list[str] = []
        self._fail_request = fail_request
        self._fail_verify = fail_verify

    async def request_otp(self, phone_number: str) -> None:
        if self._fail_request:
            raise RateLimitExceededError("too many requests")
        self.requested.append(phone_number)

    async def verify_otp(self, phone_number: str, code: str) -> TokenPair:
        if self._fail_verify:
            raise InvalidOtpError("bad code")
        return TokenPair(access_token="access-123", refresh_token="refresh-456")

    def refresh(self, refresh_token: str) -> TokenPair:
        return TokenPair(access_token="access-789", refresh_token="refresh-000")


def _build_app(fake_service: FakeAuthService) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_auth_service] = lambda: fake_service

    from app.application.exceptions import InvalidOtpError as IOE
    from app.application.exceptions import RateLimitExceededError as RLE
    from fastapi.responses import JSONResponse

    @app.exception_handler(IOE)
    async def _invalid_otp(request, exc):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(RLE)
    async def _rate_limited(request, exc):
        return JSONResponse(status_code=429, content={"detail": str(exc)})

    return app


def test_otp_request_returns_202():
    fake = FakeAuthService()
    client = TestClient(_build_app(fake))

    response = client.post("/api/v1/auth/otp/request", json={"phone_number": "+919999999999"})

    assert response.status_code == 202
    assert fake.requested == ["+919999999999"]


def test_otp_request_rate_limited_returns_429():
    client = TestClient(_build_app(FakeAuthService(fail_request=True)))

    response = client.post("/api/v1/auth/otp/request", json={"phone_number": "+919999999999"})

    assert response.status_code == 429


def test_otp_verify_returns_token_pair():
    client = TestClient(_build_app(FakeAuthService()))

    response = client.post(
        "/api/v1/auth/otp/verify", json={"phone_number": "+919999999999", "code": "123456"}
    )

    assert response.status_code == 200
    assert response.json() == {"access_token": "access-123", "refresh_token": "refresh-456"}


def test_otp_verify_invalid_code_returns_400():
    client = TestClient(_build_app(FakeAuthService(fail_verify=True)))

    response = client.post(
        "/api/v1/auth/otp/verify", json={"phone_number": "+919999999999", "code": "000000"}
    )

    assert response.status_code == 400


def test_refresh_returns_new_token_pair():
    client = TestClient(_build_app(FakeAuthService()))

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": "refresh-456"})

    assert response.status_code == 200
    assert response.json() == {"access_token": "access-789", "refresh_token": "refresh-000"}
