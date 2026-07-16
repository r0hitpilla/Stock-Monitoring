from app.core.config import get_settings


def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.database_url == "sqlite+aiosqlite:///./test.db"
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.jwt_secret == "test-secret"
    assert settings.jwt_algorithm == "HS256"
    assert settings.otp_provider == "console"
