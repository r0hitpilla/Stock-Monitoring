from datetime import datetime, timedelta, timezone

import pytest

from app.application.auth_service import AuthService
from app.application.exceptions import InvalidOtpError, RateLimitExceededError
from app.core.security import hash_otp_code
from app.domain.entities import OtpChallenge, User


class FakeUserRepo:
    def __init__(self) -> None:
        self.users_by_phone: dict[str, User] = {}
        self._next_id = 1

    async def get_or_create_by_phone(self, phone_number: str) -> User:
        if phone_number not in self.users_by_phone:
            self.users_by_phone[phone_number] = User(
                id=self._next_id,
                phone_number=phone_number,
                email=None,
                created_at=datetime.now(timezone.utc),
            )
            self._next_id += 1
        return self.users_by_phone[phone_number]

    async def get_by_id(self, user_id: int):
        return next((u for u in self.users_by_phone.values() if u.id == user_id), None)


class FakeOtpChallengeRepo:
    def __init__(self, recent_count: int = 0) -> None:
        self._challenges: dict[int, OtpChallenge] = {}
        self._next_id = 1
        self._recent_count = recent_count

    async def create(
        self, phone_number, code_hash, expires_at, created_at
    ) -> OtpChallenge:
        challenge = OtpChallenge(
            id=self._next_id,
            phone_number=phone_number,
            code_hash=code_hash,
            expires_at=expires_at,
            created_at=created_at,
            consumed=False,
            attempt_count=0,
        )
        self._challenges[challenge.id] = challenge
        self._next_id += 1
        return challenge

    async def get_latest(self, phone_number: str):
        matches = [
            c for c in self._challenges.values() if c.phone_number == phone_number
        ]
        return matches[-1] if matches else None

    async def count_recent(self, phone_number: str, window_seconds: int) -> int:
        return self._recent_count

    async def mark_consumed(self, challenge_id: int) -> None:
        self._challenges[challenge_id].consumed = True

    async def increment_attempt(self, challenge_id: int) -> None:
        self._challenges[challenge_id].attempt_count += 1


class FakeOtpProvider:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_otp(self, phone_number: str, code: str) -> None:
        self.sent.append((phone_number, code))


def _service(user_repo=None, otp_repo=None, otp_provider=None) -> AuthService:
    return AuthService(
        user_repo=user_repo or FakeUserRepo(),
        otp_repo=otp_repo or FakeOtpChallengeRepo(),
        otp_provider=otp_provider or FakeOtpProvider(),
        jwt_secret="test-secret",
        jwt_algorithm="HS256",
        access_token_expire_minutes=15,
        refresh_token_expire_days=30,
    )


@pytest.mark.asyncio
async def test_request_then_verify_otp_issues_token_pair_for_correct_code():
    user_repo = FakeUserRepo()
    otp_provider = FakeOtpProvider()
    service = _service(user_repo=user_repo, otp_provider=otp_provider)

    await service.request_otp("+919999999999")
    sent_code = otp_provider.sent[-1][1]

    tokens = await service.verify_otp("+919999999999", sent_code)

    assert tokens.access_token and tokens.refresh_token
    user_id = service.verify_access_token(tokens.access_token)
    assert user_id == user_repo.users_by_phone["+919999999999"].id


@pytest.mark.asyncio
async def test_verify_otp_with_wrong_code_raises_invalid_otp_error():
    service = _service()
    await service.request_otp("+919999999999")

    with pytest.raises(InvalidOtpError):
        await service.verify_otp("+919999999999", "000000")


@pytest.mark.asyncio
async def test_request_otp_raises_when_hourly_cap_exceeded():
    service = _service(otp_repo=FakeOtpChallengeRepo(recent_count=5))

    with pytest.raises(RateLimitExceededError):
        await service.request_otp("+919999999999")
