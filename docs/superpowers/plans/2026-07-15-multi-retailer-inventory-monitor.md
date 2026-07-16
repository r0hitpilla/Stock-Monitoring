# Multi-Retailer Inventory Monitoring Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a multi-user, multi-retailer (Blinkit, Zepto, Swiggy Instamart, BigBasket) inventory/price monitoring platform that scrapes via Playwright, detects state changes, and notifies users — with zero purchasing, cart, checkout, or payment automation anywhere in the system.

**Architecture:** Clean Architecture Python backend (`domain` → `application` → `infrastructure`/`api`) split across two runtime processes (`api` FastAPI service, `monitor` asyncio scraping scheduler) plus Celery for notification/analytics side-effects, Redis for pub/sub and broker, Postgres/SQLite for storage, and a React+TS frontend. See the design spec for full rationale.

**Tech Stack:** Python 3.13, FastAPI, Playwright, AsyncIO, SQLAlchemy, Alembic, Pydantic, Celery, Redis, SQLite/PostgreSQL, Pytest, React 18, TypeScript, Vite, TailwindCSS, shadcn/ui, Framer Motion, Chart.js, Docker/Docker Compose.

**Spec:** `docs/superpowers/specs/2026-07-15-multi-retailer-inventory-monitor-design.md`

## Global Constraints

- MUST NOT automatically add products to a cart, complete checkout, or purchase a product — for any user, any retailer, ever.
- MUST NOT store payment methods or hold/manage a monetary balance ("wallet") for any user.
- Only supported retailers: Blinkit, Zepto, Swiggy Instamart, BigBasket — each behind `BaseRetailProvider` so adding a retailer never requires touching `application`, `api`, `monitor`, or `tasks` code.
- Python 3.13. Type hints on every function signature. Docstrings on public interfaces (classes/ABCs, service methods).
- Formatting/linting: Black, Ruff, MyPy (strict on `domain`/`application`).
- Test framework: Pytest. Target ≥90% coverage on `domain`/`application`/`api`. Default test run must not make live network calls — provider extraction logic is tested against local HTML fixtures, not live retailer sites.
- Frontend: React 18 + TypeScript + Vite + TailwindCSS + shadcn/ui + Framer Motion + Chart.js. Dark-mode-first.
- DB layer: SQLAlchemy (async) + Alembic migrations. SQLite for local dev, PostgreSQL for production, selected via `DATABASE_URL` env var only (no code branching on DB vendor).
- Every commit is a working, tested state (frequent commits, TDD: failing test → implementation → passing test → commit).

---

## Phase 0: Foundations

### Task 1: Backend project scaffold, config, logging

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/logging.py`
- Create: `backend/tests/conftest.py`
- Test: `backend/tests/unit/core/test_config.py`
- Test: `backend/tests/__init__.py`, `backend/tests/unit/__init__.py`, `backend/tests/unit/core/__init__.py` (empty)

**Interfaces:**
- Produces: `Settings` (pydantic-settings `BaseSettings`) in `app.core.config` with fields `database_url: str`, `redis_url: str`, `jwt_secret: str`, `jwt_algorithm: str = "HS256"`, `access_token_expire_minutes: int = 15`, `refresh_token_expire_days: int = 30`, `otp_provider: str = "console"`, `timezone: str = "Asia/Kolkata"`, `environment: str = "development"`, `log_level: str = "INFO"`. Cached accessor `get_settings() -> Settings`.
- Produces: `configure_logging(settings: Settings) -> None` in `app.core.logging` — structured JSON logging via `structlog`.
- Produces: `backend/tests/conftest.py` — a session-scoped autouse fixture that sets `DATABASE_URL=sqlite+aiosqlite:///:memory:`, `REDIS_URL=redis://localhost:6379/0`, `JWT_SECRET=test-secret` in the environment before any test module is collected. Every later task's tests rely on this being present: several modules (e.g. Task 13's `app.tasks.celery_app`) call `get_settings()` at import time, which requires these env vars to already exist.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/core/test_config.py
import os
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/core/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: Write minimal implementation**

```toml
# backend/pyproject.toml
[project]
name = "inventory-monitor-backend"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "playwright>=1.48",
    "sqlalchemy[asyncio]>=2.0",
    "alembic>=1.13",
    "pydantic>=2.9",
    "pydantic-settings>=2.6",
    "celery>=5.4",
    "redis>=5.1",
    "asyncpg>=0.30",
    "aiosqlite>=0.20",
    "structlog>=24.4",
    "tenacity>=9.0",
    "pyjwt>=2.9",
    "python-multipart>=0.0.12",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "pytest-cov>=6.0",
    "httpx>=0.27",
    "black>=24.10",
    "ruff>=0.7",
    "mypy>=1.13",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.mypy]
strict = true
```

```python
# backend/app/__init__.py
```

```python
# backend/app/core/__init__.py
```

```python
# backend/app/core/config.py
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    otp_provider: str = "console"
    timezone: str = "Asia/Kolkata"
    environment: str = "development"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

```python
# backend/tests/conftest.py
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-secret")
```

```python
# backend/app/core/logging.py
import logging
import sys

import structlog

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        format="%(message)s", stream=sys.stdout, level=settings.log_level
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/unit/core/test_config.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/app backend/tests
git commit -m "feat: add backend scaffold with settings and structured logging"
```

---

### Task 2: Domain entities and enums

**Files:**
- Create: `backend/app/domain/__init__.py`
- Create: `backend/app/domain/enums.py`
- Create: `backend/app/domain/entities.py`
- Test: `backend/tests/unit/domain/test_entities.py`
- Test: `backend/tests/unit/domain/__init__.py` (empty)

**Interfaces:**
- Produces `Availability(str, Enum)`: `AVAILABLE`, `OUT_OF_STOCK`, `LOW_STOCK`.
- Produces `EventType(str, Enum)`: `STOCK_AVAILABLE`, `OUT_OF_STOCK`, `LOW_STOCK`, `PRICE_CHANGED`, `NEW_VARIANT`, `ETA_CHANGED`, `STORE_CHANGED`.
- Produces `NotificationChannelType(str, Enum)`: `TELEGRAM`, `DISCORD`, `EMAIL`, `PUSH`.
- Produces dataclass `LocationContext(city: str, pincode: str)`.
- Produces Pydantic model `ProviderProductResult` in `app.domain.entities` with fields: `retailer_slug: str`, `keyword: str`, `product_name: str`, `availability: Availability`, `price: float | None`, `mrp: float | None`, `discount_pct: float | None`, `eta_minutes: int | None`, `store_name: str | None`, `image_url: str | None`, `quantity_label: str | None`, `variants: list[str] = []`, `product_url: str | None`, `scraped_at: datetime`.
- Produces dataclasses `WatchTarget(id, retailer_slug, city, pincode, keyword, interval_seconds)`, `Snapshot(id, watch_target_id, timestamp, availability, price, mrp, discount_pct, eta_minutes, store_name, image_url, quantity_label, variants, product_url)`, `DetectionEvent(id, watch_target_id, snapshot_id, previous_snapshot_id, event_type, created_at)`. These mirror the DB rows and are what `application` services operate on (kept separate from SQLAlchemy models per Clean Architecture).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/domain/test_entities.py
from datetime import datetime, timezone

from app.domain.entities import ProviderProductResult
from app.domain.enums import Availability


def test_provider_product_result_defaults_variants_to_empty_list():
    result = ProviderProductResult(
        retailer_slug="blinkit",
        keyword="milk",
        product_name="Amul Milk 500ml",
        availability=Availability.AVAILABLE,
        price=29.0,
        mrp=32.0,
        discount_pct=9.4,
        eta_minutes=10,
        store_name="Blinkit Koramangala",
        image_url="https://example.com/milk.jpg",
        quantity_label="500 ml",
        product_url="https://blinkit.com/prn/milk/123",
        scraped_at=datetime.now(timezone.utc),
    )

    assert result.variants == []
    assert result.availability is Availability.AVAILABLE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/domain/test_entities.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.domain'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/domain/__init__.py
```

```python
# backend/app/domain/enums.py
from enum import Enum


class Availability(str, Enum):
    AVAILABLE = "available"
    OUT_OF_STOCK = "out_of_stock"
    LOW_STOCK = "low_stock"


class EventType(str, Enum):
    STOCK_AVAILABLE = "stock_available"
    OUT_OF_STOCK = "out_of_stock"
    LOW_STOCK = "low_stock"
    PRICE_CHANGED = "price_changed"
    NEW_VARIANT = "new_variant"
    ETA_CHANGED = "eta_changed"
    STORE_CHANGED = "store_changed"


class NotificationChannelType(str, Enum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    EMAIL = "email"
    PUSH = "push"
```

```python
# backend/app/domain/entities.py
from dataclasses import dataclass, field
from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import Availability, EventType


@dataclass(frozen=True)
class LocationContext:
    city: str
    pincode: str


class ProviderProductResult(BaseModel):
    retailer_slug: str
    keyword: str
    product_name: str
    availability: Availability
    price: float | None = None
    mrp: float | None = None
    discount_pct: float | None = None
    eta_minutes: int | None = None
    store_name: str | None = None
    image_url: str | None = None
    quantity_label: str | None = None
    variants: list[str] = []
    product_url: str | None = None
    scraped_at: datetime


@dataclass
class WatchTarget:
    id: int | None
    retailer_slug: str
    city: str
    pincode: str
    keyword: str
    interval_seconds: int = 300


@dataclass
class Snapshot:
    id: int | None
    watch_target_id: int
    timestamp: datetime
    availability: Availability
    price: float | None
    mrp: float | None
    discount_pct: float | None
    eta_minutes: int | None
    store_name: str | None
    image_url: str | None
    quantity_label: str | None
    variants: list[str]
    product_url: str | None


@dataclass
class DetectionEvent:
    id: int | None
    watch_target_id: int
    snapshot_id: int
    previous_snapshot_id: int | None
    event_type: EventType
    created_at: datetime
```

Note: `field` import is unused if no dataclass field uses it — remove the `field` import from the `dataclasses` import line above (`from dataclasses import dataclass` only) before running.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/unit/domain/test_entities.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain backend/tests/unit/domain
git commit -m "feat: add domain enums and entities"
```

---

### Task 3: SQLAlchemy models, async session, Alembic migration

**Files:**
- Create: `backend/app/infrastructure/__init__.py`
- Create: `backend/app/infrastructure/db/__init__.py`
- Create: `backend/app/infrastructure/db/session.py`
- Create: `backend/app/infrastructure/db/models.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial_schema.py`
- Test: `backend/tests/unit/infrastructure/test_models.py`
- Test: `backend/tests/unit/infrastructure/__init__.py` (empty)

**Interfaces:**
- Produces `Base` (SQLAlchemy `DeclarativeBase`) and `get_engine(database_url: str)`, `get_sessionmaker(engine) -> async_sessionmaker[AsyncSession]` in `app.infrastructure.db.session`.
- Produces ORM models in `app.infrastructure.db.models`: `UserModel`, `OtpChallengeModel`, `RetailerModel`, `ProductModel`, `WatchTargetModel`, `WatchModel`, `SnapshotModel`, `DetectionEventModel`, `NotificationChannelModel`, `NotificationLogModel`, `SettingsModel`. Table names are snake_case plurals (`users`, `otp_challenges`, `retailers`, `products`, `watch_targets`, `watches`, `snapshots`, `detection_events`, `notification_channels`, `notification_logs`, `settings`).
- `WatchTargetModel` has a unique constraint on `(retailer_slug, city, pincode, keyword)` — this is what makes cross-user scrape dedup work.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/infrastructure/test_models.py
import pytest
from sqlalchemy import text

from app.infrastructure.db.models import Base
from app.infrastructure.db.session import get_engine, get_sessionmaker


@pytest.mark.asyncio
async def test_create_all_tables_and_watch_target_dedup_constraint():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        tables = {row[0] for row in result.fetchall()}

    assert "watch_targets" in tables
    assert "users" in tables
    assert "snapshots" in tables
    await engine.dispose()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/infrastructure/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.infrastructure'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/infrastructure/__init__.py
```

```python
# backend/app/infrastructure/db/__init__.py
```

```python
# backend/app/infrastructure/db/session.py
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def get_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, pool_pre_ping=True)


def get_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
```

```python
# backend/app/infrastructure/db/models.py
from datetime import datetime

from sqlalchemy import ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime]


class OtpChallengeModel(Base):
    __tablename__ = "otp_challenges"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str] = mapped_column(index=True)
    code_hash: Mapped[str]
    expires_at: Mapped[datetime]
    consumed: Mapped[bool] = mapped_column(default=False)
    attempt_count: Mapped[int] = mapped_column(default=0)


class RetailerModel(Base):
    __tablename__ = "retailers"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)


class ProductModel(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]
    keyword: Mapped[str]
    canonical_image_url: Mapped[str | None] = mapped_column(nullable=True)


class WatchTargetModel(Base):
    __tablename__ = "watch_targets"
    __table_args__ = (
        UniqueConstraint(
            "retailer_slug", "city", "pincode", "keyword", name="uq_watch_target"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    retailer_slug: Mapped[str]
    city: Mapped[str]
    pincode: Mapped[str]
    keyword: Mapped[str]
    interval_seconds: Mapped[int] = mapped_column(default=300)
    last_checked_at: Mapped[datetime | None] = mapped_column(nullable=True)


class WatchModel(Base):
    __tablename__ = "watches"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    watch_target_id: Mapped[int] = mapped_column(ForeignKey("watch_targets.id"))
    interval_seconds: Mapped[int] = mapped_column(default=300)
    is_active: Mapped[bool] = mapped_column(default=True)


class SnapshotModel(Base):
    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    watch_target_id: Mapped[int] = mapped_column(ForeignKey("watch_targets.id"), index=True)
    timestamp: Mapped[datetime]
    availability: Mapped[str]
    price: Mapped[float | None]
    mrp: Mapped[float | None]
    discount_pct: Mapped[float | None]
    eta_minutes: Mapped[int | None]
    store_name: Mapped[str | None]
    image_url: Mapped[str | None]
    quantity_label: Mapped[str | None]
    variants: Mapped[list[str]] = mapped_column(JSON, default=list)
    product_url: Mapped[str | None]


class DetectionEventModel(Base):
    __tablename__ = "detection_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    watch_target_id: Mapped[int] = mapped_column(ForeignKey("watch_targets.id"), index=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"))
    previous_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("snapshots.id"), nullable=True)
    event_type: Mapped[str]
    created_at: Mapped[datetime]


class NotificationChannelModel(Base):
    __tablename__ = "notification_channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str]
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    is_verified: Mapped[bool] = mapped_column(default=False)


class NotificationLogModel(Base):
    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    detection_event_id: Mapped[int] = mapped_column(ForeignKey("detection_events.id"))
    channel_id: Mapped[int] = mapped_column(ForeignKey("notification_channels.id"))
    status: Mapped[str]
    sent_at: Mapped[datetime]
    dedup_key: Mapped[str] = mapped_column(index=True)


class SettingsModel(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    key: Mapped[str]
    value_json: Mapped[dict] = mapped_column(JSON, default=dict)
```

```ini
# backend/alembic.ini
[alembic]
script_location = alembic
sqlalchemy.url =

[loggers]
keys = root

[logger_root]
level = WARN
handlers = console

[handlers]
keys = console

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatters]
keys = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

```python
# backend/alembic/env.py
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.infrastructure.db.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=get_settings().database_url, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(get_settings().database_url)
    async with engine.connect() as connection:
        await connection.run_sync(
            lambda sync_conn: context.configure(
                connection=sync_conn, target_metadata=target_metadata
            )
        )
        await connection.run_sync(lambda _: context.run_migrations())
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

```python
# backend/alembic/versions/0001_initial_schema.py
"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-15
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("phone_number", sa.String, unique=True, index=True, nullable=False),
        sa.Column("email", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "otp_challenges",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("phone_number", sa.String, index=True, nullable=False),
        sa.Column("code_hash", sa.String, nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("consumed", sa.Boolean, default=False, nullable=False),
        sa.Column("attempt_count", sa.Integer, default=0, nullable=False),
    )
    op.create_table(
        "retailers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String, unique=True, nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
    )
    op.create_table(
        "products",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("keyword", sa.String, nullable=False),
        sa.Column("canonical_image_url", sa.String, nullable=True),
    )
    op.create_table(
        "watch_targets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("retailer_slug", sa.String, nullable=False),
        sa.Column("city", sa.String, nullable=False),
        sa.Column("pincode", sa.String, nullable=False),
        sa.Column("keyword", sa.String, nullable=False),
        sa.Column("interval_seconds", sa.Integer, default=300, nullable=False),
        sa.Column("last_checked_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint(
            "retailer_slug", "city", "pincode", "keyword", name="uq_watch_target"
        ),
    )
    op.create_table(
        "watches",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id"), nullable=False),
        sa.Column(
            "watch_target_id", sa.Integer, sa.ForeignKey("watch_targets.id"), nullable=False
        ),
        sa.Column("interval_seconds", sa.Integer, default=300, nullable=False),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
    )
    op.create_table(
        "snapshots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "watch_target_id", sa.Integer, sa.ForeignKey("watch_targets.id"), nullable=False, index=True
        ),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("availability", sa.String, nullable=False),
        sa.Column("price", sa.Float, nullable=True),
        sa.Column("mrp", sa.Float, nullable=True),
        sa.Column("discount_pct", sa.Float, nullable=True),
        sa.Column("eta_minutes", sa.Integer, nullable=True),
        sa.Column("store_name", sa.String, nullable=True),
        sa.Column("image_url", sa.String, nullable=True),
        sa.Column("quantity_label", sa.String, nullable=True),
        sa.Column("variants", sa.JSON, nullable=False, default=list),
        sa.Column("product_url", sa.String, nullable=True),
    )
    op.create_table(
        "detection_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "watch_target_id", sa.Integer, sa.ForeignKey("watch_targets.id"), nullable=False, index=True
        ),
        sa.Column("snapshot_id", sa.Integer, sa.ForeignKey("snapshots.id"), nullable=False),
        sa.Column(
            "previous_snapshot_id", sa.Integer, sa.ForeignKey("snapshots.id"), nullable=True
        ),
        sa.Column("event_type", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "notification_channels",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String, nullable=False),
        sa.Column("config_json", sa.JSON, nullable=False, default=dict),
        sa.Column("is_verified", sa.Boolean, default=False, nullable=False),
    )
    op.create_table(
        "notification_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "detection_event_id", sa.Integer, sa.ForeignKey("detection_events.id"), nullable=False
        ),
        sa.Column(
            "channel_id", sa.Integer, sa.ForeignKey("notification_channels.id"), nullable=False
        ),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("sent_at", sa.DateTime, nullable=False),
        sa.Column("dedup_key", sa.String, nullable=False, index=True),
    )
    op.create_table(
        "settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("key", sa.String, nullable=False),
        sa.Column("value_json", sa.JSON, nullable=False, default=dict),
    )


def downgrade() -> None:
    for table in [
        "settings",
        "notification_logs",
        "notification_channels",
        "detection_events",
        "snapshots",
        "watches",
        "watch_targets",
        "products",
        "retailers",
        "otp_challenges",
        "users",
    ]:
        op.drop_table(table)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/unit/infrastructure/test_models.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure backend/alembic backend/alembic.ini backend/tests/unit/infrastructure
git commit -m "feat: add SQLAlchemy models and initial Alembic migration"
```

---

## Phase 1: Repositories

### Task 4: WatchTarget/Snapshot/DetectionEvent repositories

**Files:**
- Create: `backend/app/domain/ports/__init__.py`
- Create: `backend/app/domain/ports/repositories.py`
- Create: `backend/app/infrastructure/db/repositories.py`
- Test: `backend/tests/unit/infrastructure/test_repositories.py`

**Interfaces:**
- Produces ABCs in `app.domain.ports.repositories`: `WatchTargetRepository` (`get_or_create(retailer_slug, city, pincode, keyword, interval_seconds) -> WatchTarget`, `list_due(now: datetime) -> list[WatchTarget]`, `mark_checked(watch_target_id: int, when: datetime) -> None`), `SnapshotRepository` (`get_latest(watch_target_id: int) -> Snapshot | None`, `create(watch_target_id, result: ProviderProductResult) -> Snapshot`), `DetectionEventRepository` (`create(watch_target_id, snapshot_id, previous_snapshot_id, event_type, when) -> DetectionEvent`, `list_for_watch_target(watch_target_id: int, limit: int = 50) -> list[DetectionEvent]`).
- Produces SQLAlchemy implementations `SqlAlchemyWatchTargetRepository`, `SqlAlchemySnapshotRepository`, `SqlAlchemyDetectionEventRepository` in `app.infrastructure.db.repositories`, each constructed with an `AsyncSession`.
- **Note for later tasks:** `UserRepository`/`OtpChallengeRepository` are added in Task 14 (auth); `WatchRepository`/`NotificationChannelRepository`/`NotificationLogRepository` in Task 11 (notification pipeline, which needs them wired to real data, not just the application-layer port); `ProductRepository` in Task 18 (products API, the only layer that needs it) — each added to these same two files (ports in `repositories.py`, impls in `db/repositories.py`) when the task that first needs them is implemented, not before (YAGNI).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/infrastructure/test_repositories.py
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.domain.entities import ProviderProductResult
from app.domain.enums import Availability, EventType
from app.infrastructure.db.models import Base
from app.infrastructure.db.repositories import (
    SqlAlchemyDetectionEventRepository,
    SqlAlchemySnapshotRepository,
    SqlAlchemyWatchTargetRepository,
)
from app.infrastructure.db.session import get_engine, get_sessionmaker


@pytest.fixture
async def session_factory():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield get_sessionmaker(engine)
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_or_create_is_idempotent_and_list_due_finds_new_targets(
    session_factory: async_sessionmaker,
):
    async with session_factory() as session:
        repo = SqlAlchemyWatchTargetRepository(session)

        first = await repo.get_or_create("blinkit", "Bengaluru", "560001", "milk", 300)
        second = await repo.get_or_create("blinkit", "Bengaluru", "560001", "milk", 300)
        await session.commit()

        assert first.id == second.id

        due = await repo.list_due(datetime.now(timezone.utc))
        assert any(t.id == first.id for t in due)


@pytest.mark.asyncio
async def test_snapshot_and_detection_event_repositories_roundtrip(
    session_factory: async_sessionmaker,
):
    async with session_factory() as session:
        watch_target_repo = SqlAlchemyWatchTargetRepository(session)
        snapshot_repo = SqlAlchemySnapshotRepository(session)
        event_repo = SqlAlchemyDetectionEventRepository(session)

        target = await watch_target_repo.get_or_create(
            "blinkit", "Bengaluru", "560001", "milk", 300
        )
        await session.commit()

        assert await snapshot_repo.get_latest(target.id) is None

        result = ProviderProductResult(
            retailer_slug="blinkit",
            keyword="milk",
            product_name="Amul Milk 500ml",
            availability=Availability.AVAILABLE,
            price=29.0,
            mrp=32.0,
            discount_pct=9.4,
            eta_minutes=10,
            store_name="Blinkit Koramangala",
            image_url=None,
            quantity_label="500 ml",
            product_url="https://blinkit.com/prn/milk/123",
            scraped_at=datetime.now(timezone.utc),
        )
        snapshot = await snapshot_repo.create(target.id, result)
        await session.commit()

        latest = await snapshot_repo.get_latest(target.id)
        assert latest is not None
        assert latest.price == 29.0

        event = await event_repo.create(
            target.id, snapshot.id, None, EventType.STOCK_AVAILABLE, datetime.now(timezone.utc)
        )
        await session.commit()

        events = await event_repo.list_for_watch_target(target.id)
        assert events[0].id == event.id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/infrastructure/test_repositories.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.domain.ports'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/domain/ports/__init__.py
```

```python
# backend/app/domain/ports/repositories.py
from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities import DetectionEvent, ProviderProductResult, Snapshot, WatchTarget
from app.domain.enums import EventType


class WatchTargetRepository(ABC):
    @abstractmethod
    async def get_or_create(
        self, retailer_slug: str, city: str, pincode: str, keyword: str, interval_seconds: int
    ) -> WatchTarget: ...

    @abstractmethod
    async def list_due(self, now: datetime) -> list[WatchTarget]: ...

    @abstractmethod
    async def mark_checked(self, watch_target_id: int, when: datetime) -> None: ...


class SnapshotRepository(ABC):
    @abstractmethod
    async def get_latest(self, watch_target_id: int) -> Snapshot | None: ...

    @abstractmethod
    async def create(self, watch_target_id: int, result: ProviderProductResult) -> Snapshot: ...


class DetectionEventRepository(ABC):
    @abstractmethod
    async def create(
        self,
        watch_target_id: int,
        snapshot_id: int,
        previous_snapshot_id: int | None,
        event_type: EventType,
        when: datetime,
    ) -> DetectionEvent: ...

    @abstractmethod
    async def list_for_watch_target(
        self, watch_target_id: int, limit: int = 50
    ) -> list[DetectionEvent]: ...
```

```python
# backend/app/infrastructure/db/repositories.py
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import DetectionEvent, ProviderProductResult, Snapshot, WatchTarget
from app.domain.enums import EventType
from app.domain.ports.repositories import (
    DetectionEventRepository,
    SnapshotRepository,
    WatchTargetRepository,
)
from app.infrastructure.db.models import DetectionEventModel, SnapshotModel, WatchTargetModel


def _to_watch_target(model: WatchTargetModel) -> WatchTarget:
    return WatchTarget(
        id=model.id,
        retailer_slug=model.retailer_slug,
        city=model.city,
        pincode=model.pincode,
        keyword=model.keyword,
        interval_seconds=model.interval_seconds,
    )


class SqlAlchemyWatchTargetRepository(WatchTargetRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(
        self, retailer_slug: str, city: str, pincode: str, keyword: str, interval_seconds: int
    ) -> WatchTarget:
        stmt = select(WatchTargetModel).where(
            WatchTargetModel.retailer_slug == retailer_slug,
            WatchTargetModel.city == city,
            WatchTargetModel.pincode == pincode,
            WatchTargetModel.keyword == keyword,
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            if interval_seconds < existing.interval_seconds:
                existing.interval_seconds = interval_seconds
            return _to_watch_target(existing)

        model = WatchTargetModel(
            retailer_slug=retailer_slug,
            city=city,
            pincode=pincode,
            keyword=keyword,
            interval_seconds=interval_seconds,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_watch_target(model)

    async def list_due(self, now: datetime) -> list[WatchTarget]:
        stmt = select(WatchTargetModel)
        models = (await self._session.execute(stmt)).scalars().all()
        due = []
        for model in models:
            if model.last_checked_at is None:
                due.append(model)
                continue
            elapsed = (now - model.last_checked_at).total_seconds()
            if elapsed >= model.interval_seconds:
                due.append(model)
        return [_to_watch_target(m) for m in due]

    async def mark_checked(self, watch_target_id: int, when: datetime) -> None:
        stmt = select(WatchTargetModel).where(WatchTargetModel.id == watch_target_id)
        model = (await self._session.execute(stmt)).scalar_one()
        model.last_checked_at = when


class SqlAlchemySnapshotRepository(SnapshotRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest(self, watch_target_id: int) -> Snapshot | None:
        stmt = (
            select(SnapshotModel)
            .where(SnapshotModel.watch_target_id == watch_target_id)
            .order_by(SnapshotModel.timestamp.desc())
            .limit(1)
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is None:
            return None
        return Snapshot(
            id=model.id,
            watch_target_id=model.watch_target_id,
            timestamp=model.timestamp,
            availability=model.availability,
            price=model.price,
            mrp=model.mrp,
            discount_pct=model.discount_pct,
            eta_minutes=model.eta_minutes,
            store_name=model.store_name,
            image_url=model.image_url,
            quantity_label=model.quantity_label,
            variants=model.variants,
            product_url=model.product_url,
        )

    async def create(self, watch_target_id: int, result: ProviderProductResult) -> Snapshot:
        model = SnapshotModel(
            watch_target_id=watch_target_id,
            timestamp=result.scraped_at,
            availability=result.availability.value,
            price=result.price,
            mrp=result.mrp,
            discount_pct=result.discount_pct,
            eta_minutes=result.eta_minutes,
            store_name=result.store_name,
            image_url=result.image_url,
            quantity_label=result.quantity_label,
            variants=result.variants,
            product_url=result.product_url,
        )
        self._session.add(model)
        await self._session.flush()
        return Snapshot(
            id=model.id,
            watch_target_id=model.watch_target_id,
            timestamp=model.timestamp,
            availability=model.availability,
            price=model.price,
            mrp=model.mrp,
            discount_pct=model.discount_pct,
            eta_minutes=model.eta_minutes,
            store_name=model.store_name,
            image_url=model.image_url,
            quantity_label=model.quantity_label,
            variants=model.variants,
            product_url=model.product_url,
        )


class SqlAlchemyDetectionEventRepository(DetectionEventRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        watch_target_id: int,
        snapshot_id: int,
        previous_snapshot_id: int | None,
        event_type: EventType,
        when: datetime,
    ) -> DetectionEvent:
        model = DetectionEventModel(
            watch_target_id=watch_target_id,
            snapshot_id=snapshot_id,
            previous_snapshot_id=previous_snapshot_id,
            event_type=event_type.value,
            created_at=when,
        )
        self._session.add(model)
        await self._session.flush()
        return DetectionEvent(
            id=model.id,
            watch_target_id=model.watch_target_id,
            snapshot_id=model.snapshot_id,
            previous_snapshot_id=model.previous_snapshot_id,
            event_type=EventType(model.event_type),
            created_at=model.created_at,
        )

    async def list_for_watch_target(
        self, watch_target_id: int, limit: int = 50
    ) -> list[DetectionEvent]:
        stmt = (
            select(DetectionEventModel)
            .where(DetectionEventModel.watch_target_id == watch_target_id)
            .order_by(DetectionEventModel.created_at.desc())
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [
            DetectionEvent(
                id=m.id,
                watch_target_id=m.watch_target_id,
                snapshot_id=m.snapshot_id,
                previous_snapshot_id=m.previous_snapshot_id,
                event_type=EventType(m.event_type),
                created_at=m.created_at,
            )
            for m in models
        ]
```

Note: remove the unused `timedelta` and `sqlite_insert` imports from the top of `repositories.py` — they aren't used by the implementation above.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/unit/infrastructure/test_repositories.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain/ports backend/app/infrastructure/db/repositories.py backend/tests/unit/infrastructure/test_repositories.py
git commit -m "feat: add watch target, snapshot, and detection event repositories"
```

---

## Phase 2: Provider Framework

### Task 5: BaseRetailProvider interface and provider registry

**Files:**
- Create: `backend/app/domain/ports/provider.py`
- Create: `backend/app/infrastructure/providers/__init__.py`
- Create: `backend/app/infrastructure/providers/registry.py`
- Test: `backend/tests/unit/providers/test_registry.py`
- Test: `backend/tests/unit/providers/__init__.py` (empty)

**Interfaces:**
- Produces ABC `BaseRetailProvider` in `app.domain.ports.provider` with `slug: ClassVar[str]` and abstract async methods exactly matching the spec: `initialize(self, location: LocationContext) -> None`, `search_product(self, keyword: str) -> list[ProviderProductResult]`, `get_product(self, product_url: str) -> ProviderProductResult`, `check_availability(self, product_url: str) -> Availability`, `extract_price(self, page: Page) -> tuple[float | None, float | None, float | None]` (price, mrp, discount_pct), `extract_eta(self, page: Page) -> int | None`, `extract_store(self, page: Page) -> str | None`, `extract_image(self, page: Page) -> str | None`, `extract_quantity(self, page: Page) -> str | None`, `extract_variants(self, page: Page) -> list[str]`, `health_check(self) -> bool`, plus `close(self) -> None` for cleanup (not in the spec's named list but required for graceful shutdown — implemented, not abstract, default no-op overridable).
- Produces ABC `ProviderRegistry` in `app.domain.ports.provider` with `get(self, retailer_slug: str) -> BaseRetailProvider` and `list_active_slugs(self) -> list[str]`.
- Produces `InMemoryProviderRegistry` in `app.infrastructure.providers.registry` — a Factory/Strategy pattern registry constructed with `dict[str, Callable[[], BaseRetailProvider]]` factories, lazily instantiates and caches one provider instance per slug.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/providers/test_registry.py
import pytest

from app.domain.entities import LocationContext, ProviderProductResult
from app.domain.enums import Availability
from app.domain.ports.provider import BaseRetailProvider
from app.infrastructure.providers.registry import InMemoryProviderRegistry


class FakeProvider(BaseRetailProvider):
    slug = "fake"

    async def initialize(self, location: LocationContext) -> None:
        self.initialized_with = location

    async def search_product(self, keyword: str) -> list[ProviderProductResult]:
        return []

    async def get_product(self, product_url: str) -> ProviderProductResult:
        raise NotImplementedError

    async def check_availability(self, product_url: str) -> Availability:
        return Availability.AVAILABLE

    async def extract_price(self, page):
        return (0.0, 0.0, 0.0)

    async def extract_eta(self, page):
        return None

    async def extract_store(self, page):
        return None

    async def extract_image(self, page):
        return None

    async def extract_quantity(self, page):
        return None

    async def extract_variants(self, page):
        return []

    async def health_check(self) -> bool:
        return True


def test_registry_lazily_instantiates_and_caches_one_instance_per_slug():
    registry = InMemoryProviderRegistry({"fake": FakeProvider})

    first = registry.get("fake")
    second = registry.get("fake")

    assert isinstance(first, FakeProvider)
    assert first is second
    assert registry.list_active_slugs() == ["fake"]


def test_registry_raises_key_error_for_unknown_slug():
    registry = InMemoryProviderRegistry({})

    with pytest.raises(KeyError):
        registry.get("unknown")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/providers/test_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.domain.ports.provider'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/domain/ports/provider.py
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from app.domain.entities import LocationContext, ProviderProductResult
from app.domain.enums import Availability

Page = Any  # playwright.async_api.Page — kept as Any here to avoid a hard
            # infrastructure dependency inside the domain layer


class BaseRetailProvider(ABC):
    """Common contract every retailer adapter must implement."""

    slug: ClassVar[str]

    @abstractmethod
    async def initialize(self, location: LocationContext) -> None: ...

    @abstractmethod
    async def search_product(self, keyword: str) -> list[ProviderProductResult]: ...

    @abstractmethod
    async def get_product(self, product_url: str) -> ProviderProductResult: ...

    @abstractmethod
    async def check_availability(self, product_url: str) -> Availability: ...

    @abstractmethod
    async def extract_price(self, page: Page) -> tuple[float | None, float | None, float | None]: ...

    @abstractmethod
    async def extract_eta(self, page: Page) -> int | None: ...

    @abstractmethod
    async def extract_store(self, page: Page) -> str | None: ...

    @abstractmethod
    async def extract_image(self, page: Page) -> str | None: ...

    @abstractmethod
    async def extract_quantity(self, page: Page) -> str | None: ...

    @abstractmethod
    async def extract_variants(self, page: Page) -> list[str]: ...

    @abstractmethod
    async def health_check(self) -> bool: ...

    async def close(self) -> None:
        """Release browser resources. Default no-op; override if needed."""
        return None


class ProviderRegistry(ABC):
    @abstractmethod
    def get(self, retailer_slug: str) -> BaseRetailProvider: ...

    @abstractmethod
    def list_active_slugs(self) -> list[str]: ...
```

```python
# backend/app/infrastructure/providers/__init__.py
```

```python
# backend/app/infrastructure/providers/registry.py
from typing import Callable

from app.domain.ports.provider import BaseRetailProvider, ProviderRegistry


class InMemoryProviderRegistry(ProviderRegistry):
    def __init__(self, factories: dict[str, Callable[[], BaseRetailProvider]]) -> None:
        self._factories = factories
        self._instances: dict[str, BaseRetailProvider] = {}

    def get(self, retailer_slug: str) -> BaseRetailProvider:
        if retailer_slug not in self._factories:
            raise KeyError(f"No provider registered for '{retailer_slug}'")
        if retailer_slug not in self._instances:
            self._instances[retailer_slug] = self._factories[retailer_slug]()
        return self._instances[retailer_slug]

    def list_active_slugs(self) -> list[str]:
        return list(self._instances.keys())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/unit/providers/test_registry.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain/ports/provider.py backend/app/infrastructure/providers backend/tests/unit/providers
git commit -m "feat: add BaseRetailProvider interface and provider registry"
```

---

### Task 6: Snapshot diff logic

**Files:**
- Create: `backend/app/application/__init__.py`
- Create: `backend/app/application/diffing.py`
- Test: `backend/tests/unit/application/test_diffing.py`
- Test: `backend/tests/unit/application/__init__.py` (empty)

**Interfaces:**
- Produces pure function `diff_snapshots(previous: Snapshot | None, current: ProviderProductResult) -> list[EventType]` in `app.application.diffing`. No I/O — fully unit-testable. Rules: `previous is None` and `current.availability != OUT_OF_STOCK` → `[STOCK_AVAILABLE]`. Otherwise compare field by field: availability OOS→AVAILABLE/LOW_STOCK → `STOCK_AVAILABLE`; availability AVAILABLE/LOW_STOCK→OUT_OF_STOCK → `OUT_OF_STOCK`; availability →LOW_STOCK (from AVAILABLE) → `LOW_STOCK`; `price` changed → `PRICE_CHANGED`; new entries in `variants` vs previous → `NEW_VARIANT`; `eta_minutes` changed → `ETA_CHANGED`; `store_name` changed → `STORE_CHANGED`. Multiple event types can fire from one diff (returns a list, possibly empty if nothing changed).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/application/test_diffing.py
from datetime import datetime, timezone

from app.application.diffing import diff_snapshots
from app.domain.entities import ProviderProductResult, Snapshot
from app.domain.enums import Availability, EventType


def _snapshot(**overrides) -> Snapshot:
    base = dict(
        id=1,
        watch_target_id=1,
        timestamp=datetime.now(timezone.utc),
        availability=Availability.OUT_OF_STOCK,
        price=29.0,
        mrp=32.0,
        discount_pct=9.4,
        eta_minutes=10,
        store_name="Blinkit Koramangala",
        image_url=None,
        quantity_label="500 ml",
        variants=["500 ml"],
        product_url="https://blinkit.com/prn/milk/123",
    )
    base.update(overrides)
    return Snapshot(**base)


def _result(**overrides) -> ProviderProductResult:
    base = dict(
        retailer_slug="blinkit",
        keyword="milk",
        product_name="Amul Milk 500ml",
        availability=Availability.AVAILABLE,
        price=29.0,
        mrp=32.0,
        discount_pct=9.4,
        eta_minutes=10,
        store_name="Blinkit Koramangala",
        image_url=None,
        quantity_label="500 ml",
        variants=["500 ml"],
        product_url="https://blinkit.com/prn/milk/123",
        scraped_at=datetime.now(timezone.utc),
    )
    base.update(overrides)
    return ProviderProductResult(**base)


def test_first_ever_snapshot_that_is_in_stock_emits_stock_available():
    events = diff_snapshots(None, _result(availability=Availability.AVAILABLE))
    assert events == [EventType.STOCK_AVAILABLE]


def test_out_of_stock_to_available_emits_stock_available():
    previous = _snapshot(availability=Availability.OUT_OF_STOCK)
    events = diff_snapshots(previous, _result(availability=Availability.AVAILABLE))
    assert EventType.STOCK_AVAILABLE in events


def test_available_to_out_of_stock_emits_out_of_stock():
    previous = _snapshot(availability=Availability.AVAILABLE)
    events = diff_snapshots(previous, _result(availability=Availability.OUT_OF_STOCK))
    assert events == [EventType.OUT_OF_STOCK]


def test_price_change_emits_price_changed():
    previous = _snapshot(availability=Availability.AVAILABLE, price=29.0)
    events = diff_snapshots(previous, _result(availability=Availability.AVAILABLE, price=25.0))
    assert events == [EventType.PRICE_CHANGED]


def test_new_variant_emits_new_variant():
    previous = _snapshot(availability=Availability.AVAILABLE, variants=["500 ml"])
    events = diff_snapshots(
        previous, _result(availability=Availability.AVAILABLE, variants=["500 ml", "1 L"])
    )
    assert events == [EventType.NEW_VARIANT]


def test_no_changes_emits_no_events():
    previous = _snapshot(availability=Availability.AVAILABLE)
    events = diff_snapshots(previous, _result(availability=Availability.AVAILABLE))
    assert events == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/application/test_diffing.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.application'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/application/__init__.py
```

```python
# backend/app/application/diffing.py
from app.domain.entities import ProviderProductResult, Snapshot
from app.domain.enums import Availability, EventType


def diff_snapshots(
    previous: Snapshot | None, current: ProviderProductResult
) -> list[EventType]:
    events: list[EventType] = []

    previous_availability = previous.availability if previous else Availability.OUT_OF_STOCK

    if previous_availability == Availability.OUT_OF_STOCK and current.availability in (
        Availability.AVAILABLE,
        Availability.LOW_STOCK,
    ):
        events.append(EventType.STOCK_AVAILABLE)
    elif (
        previous_availability in (Availability.AVAILABLE, Availability.LOW_STOCK)
        and current.availability == Availability.OUT_OF_STOCK
    ):
        events.append(EventType.OUT_OF_STOCK)
    elif previous_availability == Availability.AVAILABLE and current.availability == Availability.LOW_STOCK:
        events.append(EventType.LOW_STOCK)

    if previous is None:
        return events

    if previous.price != current.price:
        events.append(EventType.PRICE_CHANGED)

    if set(current.variants) - set(previous.variants):
        events.append(EventType.NEW_VARIANT)

    if previous.eta_minutes != current.eta_minutes:
        events.append(EventType.ETA_CHANGED)

    if previous.store_name != current.store_name:
        events.append(EventType.STORE_CHANGED)

    return events
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/unit/application/test_diffing.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/application backend/tests/unit/application
git commit -m "feat: add pure snapshot diffing logic"
```

---

### Task 7: Blinkit provider

**Files:**
- Create: `backend/app/infrastructure/providers/blinkit/__init__.py`
- Create: `backend/app/infrastructure/providers/blinkit/selectors.py`
- Create: `backend/app/infrastructure/providers/blinkit/provider.py`
- Create: `backend/tests/fixtures/blinkit_product_available.html`
- Create: `backend/tests/fixtures/blinkit_product_out_of_stock.html`
- Test: `backend/tests/unit/providers/test_blinkit_provider.py`

**Interfaces:**
- Produces `BlinkitProvider(BaseRetailProvider)` in `app.infrastructure.providers.blinkit.provider` with `slug = "blinkit"`, implementing every abstract method from Task 5. Extraction methods (`extract_price`, `extract_eta`, `extract_store`, `extract_image`, `extract_quantity`, `extract_variants`) and the internal `check_availability_from_page(page) -> Availability` helper operate on an already-loaded `playwright.async_api.Page` and contain **no navigation** — this is what makes them unit-testable against local HTML fixtures instead of the live site. `initialize`, `search_product`, `get_product`, `check_availability`, `health_check` own all navigation/network I/O and are covered later by the opt-in integration tier (Task 7 does not add integration tests — see Global Constraints on live network calls).
- Consumes: `BaseRetailProvider`, `LocationContext`, `ProviderProductResult`, `Availability` from Tasks 2 and 5.

**Selector maintenance note:** the selectors below target `data-test-id` attributes, which are the most robust hook available on this kind of frontend. Retailer frontends change; if extraction starts returning `None` for fields that should be populated, the fix is to open the live product page in a browser, inspect the current DOM, and update `BLINKIT_SELECTORS` — this is expected, ongoing scraper maintenance, not a defect in this task's code. No cart/checkout selectors are ever clicked by this provider — `add-to-cart` presence is used only as an availability signal, never actuated.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/providers/test_blinkit_provider.py
from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from app.domain.enums import Availability
from app.infrastructure.providers.blinkit.provider import BlinkitProvider

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


@pytest.fixture
async def page():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        pg = await browser.new_page()
        yield pg
        await browser.close()


@pytest.mark.asyncio
async def test_extracts_available_product_fields(page):
    html = (FIXTURES / "blinkit_product_available.html").read_text()
    await page.set_content(html)
    provider = BlinkitProvider()

    availability = await provider.check_availability_from_page(page)
    price, mrp, discount_pct = await provider.extract_price(page)
    eta_minutes = await provider.extract_eta(page)
    store_name = await provider.extract_store(page)
    quantity_label = await provider.extract_quantity(page)
    variants = await provider.extract_variants(page)
    image_url = await provider.extract_image(page)

    assert availability == Availability.AVAILABLE
    assert price == 29.0
    assert mrp == 32.0
    assert discount_pct == 9.4
    assert eta_minutes == 10
    assert store_name == "Blinkit Koramangala"
    assert quantity_label == "500 ml"
    assert variants == ["500 ml", "1 L"]
    assert image_url == "https://cdn.blinkit.com/milk.jpg"


@pytest.mark.asyncio
async def test_extracts_out_of_stock_product(page):
    html = (FIXTURES / "blinkit_product_out_of_stock.html").read_text()
    await page.set_content(html)
    provider = BlinkitProvider()

    availability = await provider.check_availability_from_page(page)

    assert availability == Availability.OUT_OF_STOCK


@pytest.mark.asyncio
async def test_health_check_returns_false_before_initialize():
    provider = BlinkitProvider()
    assert await provider.health_check() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/providers/test_blinkit_provider.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.infrastructure.providers.blinkit'`

- [ ] **Step 3: Write minimal implementation**

```html
<!-- backend/tests/fixtures/blinkit_product_available.html -->
<!DOCTYPE html>
<html>
<body>
  <h1 data-test-id="product-name">Amul Milk 500ml</h1>
  <div data-test-id="product-price">₹29</div>
  <div data-test-id="product-mrp">₹32</div>
  <div data-test-id="eta">10 MINS</div>
  <div data-test-id="store-name">Blinkit Koramangala</div>
  <div data-test-id="product-image"><img src="https://cdn.blinkit.com/milk.jpg"></div>
  <div data-test-id="product-quantity">500 ml</div>
  <div data-test-id="variant-option">500 ml</div>
  <div data-test-id="variant-option">1 L</div>
  <button data-test-id="add-to-cart">ADD</button>
</body>
</html>
```

```html
<!-- backend/tests/fixtures/blinkit_product_out_of_stock.html -->
<!DOCTYPE html>
<html>
<body>
  <h1 data-test-id="product-name">Amul Milk 500ml</h1>
  <div data-test-id="out-of-stock">Currently unavailable</div>
</body>
</html>
```

```python
# backend/app/infrastructure/providers/blinkit/__init__.py
```

```python
# backend/app/infrastructure/providers/blinkit/selectors.py
BLINKIT_SELECTORS = {
    "location_trigger": "[data-test-id='select-location']",
    "location_input": "[data-test-id='location-search-input']",
    "location_confirm": "[data-test-id='location-confirm']",
    "search_result_card": "[data-test-id='plp-product-card'] a",
    "product_name": "[data-test-id='product-name']",
    "price": "[data-test-id='product-price']",
    "mrp": "[data-test-id='product-mrp']",
    "eta": "[data-test-id='eta']",
    "store": "[data-test-id='store-name']",
    "image": "[data-test-id='product-image'] img",
    "quantity": "[data-test-id='product-quantity']",
    "variants": "[data-test-id='variant-option']",
    "out_of_stock_badge": "[data-test-id='out-of-stock']",
    "low_stock_badge": "[data-test-id='low-stock']",
}
```

```python
# backend/app/infrastructure/providers/blinkit/provider.py
import re
from datetime import datetime, timezone

from playwright.async_api import Browser, Page, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from tenacity import retry, stop_after_attempt, wait_exponential

from app.domain.entities import LocationContext, ProviderProductResult
from app.domain.enums import Availability
from app.domain.ports.provider import BaseRetailProvider
from app.infrastructure.providers.blinkit.selectors import BLINKIT_SELECTORS

BASE_URL = "https://blinkit.com"


class BlinkitProvider(BaseRetailProvider):
    slug = "blinkit"

    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None

    async def initialize(self, location: LocationContext) -> None:
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
        page = await self._browser.new_page()
        try:
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
            try:
                await page.click(BLINKIT_SELECTORS["location_trigger"], timeout=5000)
                await page.fill(BLINKIT_SELECTORS["location_input"], location.pincode)
                await page.click(BLINKIT_SELECTORS["location_confirm"], timeout=5000)
            except PlaywrightTimeoutError:
                pass  # location UI may already be set from a saved session
        finally:
            await page.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def search_product(self, keyword: str) -> list[ProviderProductResult]:
        assert self._browser is not None, "call initialize() first"
        page = await self._browser.new_page()
        try:
            await page.goto(f"{BASE_URL}/s/?q={keyword}", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_selector(BLINKIT_SELECTORS["search_result_card"], timeout=10000)
            cards = await page.query_selector_all(BLINKIT_SELECTORS["search_result_card"])
            urls = [await card.get_attribute("href") for card in cards]
            return [await self.get_product(f"{BASE_URL}{url}") for url in urls if url]
        finally:
            await page.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def get_product(self, product_url: str) -> ProviderProductResult:
        assert self._browser is not None, "call initialize() first"
        page = await self._browser.new_page()
        try:
            await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
            name_el = await page.query_selector(BLINKIT_SELECTORS["product_name"])
            product_name = (await name_el.inner_text()).strip() if name_el else ""
            availability = await self.check_availability_from_page(page)
            price, mrp, discount_pct = await self.extract_price(page)
            return ProviderProductResult(
                retailer_slug=self.slug,
                keyword=product_name,
                product_name=product_name,
                availability=availability,
                price=price,
                mrp=mrp,
                discount_pct=discount_pct,
                eta_minutes=await self.extract_eta(page),
                store_name=await self.extract_store(page),
                image_url=await self.extract_image(page),
                quantity_label=await self.extract_quantity(page),
                variants=await self.extract_variants(page),
                product_url=product_url,
                scraped_at=datetime.now(timezone.utc),
            )
        finally:
            await page.close()

    async def check_availability(self, product_url: str) -> Availability:
        assert self._browser is not None, "call initialize() first"
        page = await self._browser.new_page()
        try:
            await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
            return await self.check_availability_from_page(page)
        finally:
            await page.close()

    async def check_availability_from_page(self, page: Page) -> Availability:
        if await page.query_selector(BLINKIT_SELECTORS["out_of_stock_badge"]):
            return Availability.OUT_OF_STOCK
        if await page.query_selector(BLINKIT_SELECTORS["low_stock_badge"]):
            return Availability.LOW_STOCK
        return Availability.AVAILABLE

    async def extract_price(self, page: Page) -> tuple[float | None, float | None, float | None]:
        price = await self._extract_number(page, BLINKIT_SELECTORS["price"])
        mrp = await self._extract_number(page, BLINKIT_SELECTORS["mrp"])
        discount_pct = None
        if price is not None and mrp:
            discount_pct = round((1 - price / mrp) * 100, 1)
        return price, mrp, discount_pct

    async def extract_eta(self, page: Page) -> int | None:
        el = await page.query_selector(BLINKIT_SELECTORS["eta"])
        if not el:
            return None
        match = re.search(r"(\d+)", await el.inner_text())
        return int(match.group(1)) if match else None

    async def extract_store(self, page: Page) -> str | None:
        el = await page.query_selector(BLINKIT_SELECTORS["store"])
        return (await el.inner_text()).strip() if el else None

    async def extract_image(self, page: Page) -> str | None:
        el = await page.query_selector(BLINKIT_SELECTORS["image"])
        return await el.get_attribute("src") if el else None

    async def extract_quantity(self, page: Page) -> str | None:
        el = await page.query_selector(BLINKIT_SELECTORS["quantity"])
        return (await el.inner_text()).strip() if el else None

    async def extract_variants(self, page: Page) -> list[str]:
        elements = await page.query_selector_all(BLINKIT_SELECTORS["variants"])
        return [(await el.inner_text()).strip() for el in elements]

    async def _extract_number(self, page: Page, selector: str) -> float | None:
        el = await page.query_selector(selector)
        if not el:
            return None
        match = re.search(r"[\d,]+\.?\d*", (await el.inner_text()).replace(",", ""))
        return float(match.group(0)) if match else None

    async def health_check(self) -> bool:
        if self._browser is None:
            return False
        try:
            page = await self._browser.new_page()
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=10000)
            await page.close()
            return True
        except PlaywrightTimeoutError:
            return False

    async def close(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && playwright install chromium && python -m pytest tests/unit/providers/test_blinkit_provider.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure/providers/blinkit backend/tests/fixtures backend/tests/unit/providers/test_blinkit_provider.py
git commit -m "feat: add Blinkit provider with fixture-tested extraction logic"
```

---

## Phase 3: Monitoring Engine

### Task 8: MonitoringService application use case

**Files:**
- Create: `backend/app/domain/ports/messaging.py`
- Create: `backend/app/application/monitoring_service.py`
- Test: `backend/tests/unit/application/test_monitoring_service.py`

**Interfaces:**
- Produces ABCs in `app.domain.ports.messaging`: `EventPublisher` (`async def publish(self, watch_target_id: int, event: DetectionEvent) -> None`), `TaskDispatcher` (`def dispatch_detection_event(self, event_id: int) -> None`).
- Produces `MonitoringService` in `app.application.monitoring_service`, constructed with `(provider_registry: ProviderRegistry, watch_target_repo: WatchTargetRepository, snapshot_repo: SnapshotRepository, event_repo: DetectionEventRepository, event_publisher: EventPublisher, task_dispatcher: TaskDispatcher)`. Exposes `async def check_watch_target(self, watch_target: WatchTarget) -> list[DetectionEvent]` — the single orchestration point Task 10's scheduler calls per due target: initializes the provider for the target's location, searches by keyword, diffs against the latest snapshot (via `diff_snapshots` from Task 6), and on any change persists a new snapshot + one `DetectionEvent` per changed field, publishes each event, and dispatches a Celery job per event. Always marks the target checked (via `watch_target_repo.mark_checked`) whether or not anything changed, so `list_due` (Task 4) stops returning it until its interval elapses again.
- Consumes: `ProviderRegistry`, `BaseRetailProvider` (Task 5); `diff_snapshots` (Task 6); `WatchTargetRepository`, `SnapshotRepository`, `DetectionEventRepository` (Task 4).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/application/test_monitoring_service.py
from datetime import datetime, timezone

import pytest

from app.application.monitoring_service import MonitoringService
from app.domain.entities import LocationContext, ProviderProductResult, WatchTarget
from app.domain.enums import Availability, EventType
from app.domain.ports.provider import BaseRetailProvider


class FakeProvider(BaseRetailProvider):
    slug = "blinkit"

    def __init__(self, result: ProviderProductResult) -> None:
        self._result = result
        self.initialized_with: LocationContext | None = None

    async def initialize(self, location: LocationContext) -> None:
        self.initialized_with = location

    async def search_product(self, keyword: str) -> list[ProviderProductResult]:
        return [self._result]

    async def get_product(self, product_url: str) -> ProviderProductResult:
        return self._result

    async def check_availability(self, product_url: str) -> Availability:
        return self._result.availability

    async def extract_price(self, page):
        return (self._result.price, self._result.mrp, self._result.discount_pct)

    async def extract_eta(self, page):
        return self._result.eta_minutes

    async def extract_store(self, page):
        return self._result.store_name

    async def extract_image(self, page):
        return self._result.image_url

    async def extract_quantity(self, page):
        return self._result.quantity_label

    async def extract_variants(self, page):
        return self._result.variants

    async def health_check(self) -> bool:
        return True


class FakeProviderRegistry:
    def __init__(self, provider: BaseRetailProvider) -> None:
        self._provider = provider

    def get(self, retailer_slug: str) -> BaseRetailProvider:
        return self._provider

    def list_active_slugs(self) -> list[str]:
        return [self._provider.slug]


class FakeWatchTargetRepo:
    def __init__(self) -> None:
        self.checked_at: dict[int, datetime] = {}

    async def get_or_create(self, *args, **kwargs):
        raise NotImplementedError

    async def list_due(self, now):
        raise NotImplementedError

    async def mark_checked(self, watch_target_id: int, when: datetime) -> None:
        self.checked_at[watch_target_id] = when


class FakeSnapshotRepo:
    def __init__(self, latest=None) -> None:
        self._latest = latest
        self.created = []

    async def get_latest(self, watch_target_id: int):
        return self._latest

    async def create(self, watch_target_id: int, result: ProviderProductResult):
        from app.domain.entities import Snapshot

        snapshot = Snapshot(
            id=len(self.created) + 1,
            watch_target_id=watch_target_id,
            timestamp=result.scraped_at,
            availability=result.availability,
            price=result.price,
            mrp=result.mrp,
            discount_pct=result.discount_pct,
            eta_minutes=result.eta_minutes,
            store_name=result.store_name,
            image_url=result.image_url,
            quantity_label=result.quantity_label,
            variants=result.variants,
            product_url=result.product_url,
        )
        self.created.append(snapshot)
        return snapshot


class FakeDetectionEventRepo:
    def __init__(self) -> None:
        self.created = []

    async def create(self, watch_target_id, snapshot_id, previous_snapshot_id, event_type, when):
        from app.domain.entities import DetectionEvent

        event = DetectionEvent(
            id=len(self.created) + 1,
            watch_target_id=watch_target_id,
            snapshot_id=snapshot_id,
            previous_snapshot_id=previous_snapshot_id,
            event_type=event_type,
            created_at=when,
        )
        self.created.append(event)
        return event

    async def list_for_watch_target(self, watch_target_id, limit=50):
        return self.created


class FakeEventPublisher:
    def __init__(self) -> None:
        self.published = []

    async def publish(self, watch_target_id, event):
        self.published.append((watch_target_id, event))


class FakeTaskDispatcher:
    def __init__(self) -> None:
        self.dispatched = []

    def dispatch_detection_event(self, event_id: int) -> None:
        self.dispatched.append(event_id)


@pytest.mark.asyncio
async def test_check_watch_target_persists_snapshot_and_publishes_event_on_restock():
    result = ProviderProductResult(
        retailer_slug="blinkit",
        keyword="milk",
        product_name="Amul Milk 500ml",
        availability=Availability.AVAILABLE,
        price=29.0,
        mrp=32.0,
        discount_pct=9.4,
        eta_minutes=10,
        store_name="Blinkit Koramangala",
        image_url=None,
        quantity_label="500 ml",
        variants=["500 ml"],
        product_url="https://blinkit.com/prn/milk/123",
        scraped_at=datetime.now(timezone.utc),
    )
    provider = FakeProvider(result)
    watch_target_repo = FakeWatchTargetRepo()
    snapshot_repo = FakeSnapshotRepo(latest=None)
    event_repo = FakeDetectionEventRepo()
    publisher = FakeEventPublisher()
    dispatcher = FakeTaskDispatcher()

    service = MonitoringService(
        provider_registry=FakeProviderRegistry(provider),
        watch_target_repo=watch_target_repo,
        snapshot_repo=snapshot_repo,
        event_repo=event_repo,
        event_publisher=publisher,
        task_dispatcher=dispatcher,
    )

    watch_target = WatchTarget(
        id=1, retailer_slug="blinkit", city="Bengaluru", pincode="560001", keyword="milk"
    )

    events = await service.check_watch_target(watch_target)

    assert len(events) == 1
    assert events[0].event_type == EventType.STOCK_AVAILABLE
    assert provider.initialized_with == LocationContext("Bengaluru", "560001")
    assert len(snapshot_repo.created) == 1
    assert len(publisher.published) == 1
    assert dispatcher.dispatched == [events[0].id]
    assert 1 in watch_target_repo.checked_at


@pytest.mark.asyncio
async def test_check_watch_target_marks_checked_but_persists_nothing_when_unchanged():
    result = ProviderProductResult(
        retailer_slug="blinkit",
        keyword="milk",
        product_name="Amul Milk 500ml",
        availability=Availability.OUT_OF_STOCK,
        price=None,
        mrp=None,
        discount_pct=None,
        eta_minutes=None,
        store_name=None,
        image_url=None,
        quantity_label=None,
        variants=[],
        product_url="https://blinkit.com/prn/milk/123",
        scraped_at=datetime.now(timezone.utc),
    )
    provider = FakeProvider(result)
    watch_target_repo = FakeWatchTargetRepo()
    snapshot_repo = FakeSnapshotRepo(latest=None)
    event_repo = FakeDetectionEventRepo()
    publisher = FakeEventPublisher()
    dispatcher = FakeTaskDispatcher()

    service = MonitoringService(
        provider_registry=FakeProviderRegistry(provider),
        watch_target_repo=watch_target_repo,
        snapshot_repo=snapshot_repo,
        event_repo=event_repo,
        event_publisher=publisher,
        task_dispatcher=dispatcher,
    )
    watch_target = WatchTarget(
        id=1, retailer_slug="blinkit", city="Bengaluru", pincode="560001", keyword="milk"
    )

    events = await service.check_watch_target(watch_target)

    assert events == []
    assert snapshot_repo.created == []
    assert publisher.published == []
    assert 1 in watch_target_repo.checked_at
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/application/test_monitoring_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.application.monitoring_service'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/domain/ports/messaging.py
from abc import ABC, abstractmethod

from app.domain.entities import DetectionEvent


class EventPublisher(ABC):
    @abstractmethod
    async def publish(self, watch_target_id: int, event: DetectionEvent) -> None: ...


class TaskDispatcher(ABC):
    @abstractmethod
    def dispatch_detection_event(self, event_id: int) -> None: ...
```

```python
# backend/app/application/monitoring_service.py
from app.application.diffing import diff_snapshots
from app.domain.entities import DetectionEvent, WatchTarget
from app.domain.entities import LocationContext
from app.domain.ports.messaging import EventPublisher, TaskDispatcher
from app.domain.ports.provider import ProviderRegistry
from app.domain.ports.repositories import (
    DetectionEventRepository,
    SnapshotRepository,
    WatchTargetRepository,
)


class MonitoringService:
    def __init__(
        self,
        provider_registry: ProviderRegistry,
        watch_target_repo: WatchTargetRepository,
        snapshot_repo: SnapshotRepository,
        event_repo: DetectionEventRepository,
        event_publisher: EventPublisher,
        task_dispatcher: TaskDispatcher,
    ) -> None:
        self._provider_registry = provider_registry
        self._watch_target_repo = watch_target_repo
        self._snapshot_repo = snapshot_repo
        self._event_repo = event_repo
        self._event_publisher = event_publisher
        self._task_dispatcher = task_dispatcher

    async def check_watch_target(self, watch_target: WatchTarget) -> list[DetectionEvent]:
        provider = self._provider_registry.get(watch_target.retailer_slug)
        await provider.initialize(LocationContext(watch_target.city, watch_target.pincode))

        results = await provider.search_product(watch_target.keyword)
        if not results:
            await self._watch_target_repo.mark_checked(watch_target.id, watch_target.id and __import__("datetime").datetime.now(__import__("datetime").timezone.utc))
            return []
        result = results[0]

        previous = await self._snapshot_repo.get_latest(watch_target.id)
        event_types = diff_snapshots(previous, result)

        if not event_types:
            await self._watch_target_repo.mark_checked(watch_target.id, result.scraped_at)
            return []

        snapshot = await self._snapshot_repo.create(watch_target.id, result)
        events: list[DetectionEvent] = []
        for event_type in event_types:
            event = await self._event_repo.create(
                watch_target.id,
                snapshot.id,
                previous.id if previous else None,
                event_type,
                result.scraped_at,
            )
            events.append(event)
            await self._event_publisher.publish(watch_target.id, event)
            self._task_dispatcher.dispatch_detection_event(event.id)

        await self._watch_target_repo.mark_checked(watch_target.id, result.scraped_at)
        return events
```

Clean up the inline `__import__("datetime")` hack from the "no results" branch before running — replace it with a proper top-level import:

```python
# top of backend/app/application/monitoring_service.py, add:
from datetime import datetime, timezone
```

```python
# and replace the "no results" branch body with:
        if not results:
            await self._watch_target_repo.mark_checked(watch_target.id, datetime.now(timezone.utc))
            return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/unit/application/test_monitoring_service.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain/ports/messaging.py backend/app/application/monitoring_service.py backend/tests/unit/application/test_monitoring_service.py
git commit -m "feat: add MonitoringService orchestrating provider checks and diffing"
```

---

### Task 9: Redis event publisher and Celery task dispatcher adapters

**Files:**
- Create: `backend/app/infrastructure/cache/__init__.py`
- Create: `backend/app/infrastructure/cache/redis_publisher.py`
- Create: `backend/app/infrastructure/tasks_dispatch.py`
- Test: `backend/tests/unit/infrastructure/test_redis_publisher.py`
- Test: `backend/tests/unit/infrastructure/test_task_dispatcher.py`

**Interfaces:**
- Produces `RedisEventPublisher(EventPublisher)` in `app.infrastructure.cache.redis_publisher`, constructed with any object exposing `async def publish(self, channel: str, message: str) -> int` (matches `redis.asyncio.Redis`). Publishes to channel `f"events:{watch_target_id}"` with a JSON payload `{"event_id", "watch_target_id", "event_type", "snapshot_id", "created_at"}`.
- Produces `CeleryTaskDispatcher(TaskDispatcher)` in `app.infrastructure.tasks_dispatch`, constructed with any object exposing `def send_task(self, name: str, args: list) -> Any` (matches a Celery `Celery` app instance). Calls `send_task("app.tasks.notifications.process_detection_event", args=[event_id])` — dispatches by task **name string**, not by importing the task function, so this module never needs to import `app.tasks` (avoids a circular import with Task 13, which defines that task and lives in a different process).
- Consumes: `EventPublisher`, `TaskDispatcher` (Task 8); `DetectionEvent` (Task 2).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/infrastructure/test_redis_publisher.py
import json
from datetime import datetime, timezone

import pytest

from app.domain.entities import DetectionEvent
from app.domain.enums import EventType
from app.infrastructure.cache.redis_publisher import RedisEventPublisher


class FakeRedisClient:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []

    async def publish(self, channel: str, message: str) -> int:
        self.published.append((channel, message))
        return 1


@pytest.mark.asyncio
async def test_publish_sends_json_payload_to_watch_target_channel():
    fake_redis = FakeRedisClient()
    publisher = RedisEventPublisher(fake_redis)
    event = DetectionEvent(
        id=42,
        watch_target_id=7,
        snapshot_id=100,
        previous_snapshot_id=99,
        event_type=EventType.STOCK_AVAILABLE,
        created_at=datetime.now(timezone.utc),
    )

    await publisher.publish(7, event)

    assert len(fake_redis.published) == 1
    channel, message = fake_redis.published[0]
    assert channel == "events:7"
    payload = json.loads(message)
    assert payload["event_id"] == 42
    assert payload["event_type"] == "stock_available"
```

```python
# backend/tests/unit/infrastructure/test_task_dispatcher.py
from app.infrastructure.tasks_dispatch import CeleryTaskDispatcher


class FakeCeleryApp:
    def __init__(self) -> None:
        self.sent: list[tuple[str, list]] = []

    def send_task(self, name: str, args: list):
        self.sent.append((name, args))


def test_dispatch_detection_event_sends_task_by_name():
    fake_app = FakeCeleryApp()
    dispatcher = CeleryTaskDispatcher(fake_app)

    dispatcher.dispatch_detection_event(42)

    assert fake_app.sent == [("app.tasks.notifications.process_detection_event", [42])]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/infrastructure/test_redis_publisher.py tests/unit/infrastructure/test_task_dispatcher.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/infrastructure/cache/__init__.py
```

```python
# backend/app/infrastructure/cache/redis_publisher.py
import json
from typing import Protocol

from app.domain.entities import DetectionEvent
from app.domain.ports.messaging import EventPublisher


class RedisLike(Protocol):
    async def publish(self, channel: str, message: str) -> int: ...


class RedisEventPublisher(EventPublisher):
    def __init__(self, redis_client: RedisLike) -> None:
        self._redis = redis_client

    async def publish(self, watch_target_id: int, event: DetectionEvent) -> None:
        payload = {
            "event_id": event.id,
            "watch_target_id": watch_target_id,
            "event_type": event.event_type.value,
            "snapshot_id": event.snapshot_id,
            "created_at": event.created_at.isoformat(),
        }
        await self._redis.publish(f"events:{watch_target_id}", json.dumps(payload))
```

```python
# backend/app/infrastructure/tasks_dispatch.py
from typing import Any, Protocol

from app.domain.ports.messaging import TaskDispatcher


class CeleryAppLike(Protocol):
    def send_task(self, name: str, args: list) -> Any: ...


class CeleryTaskDispatcher(TaskDispatcher):
    def __init__(self, celery_app: CeleryAppLike) -> None:
        self._celery_app = celery_app

    def dispatch_detection_event(self, event_id: int) -> None:
        self._celery_app.send_task(
            "app.tasks.notifications.process_detection_event", args=[event_id]
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/unit/infrastructure/test_redis_publisher.py tests/unit/infrastructure/test_task_dispatcher.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure/cache backend/app/infrastructure/tasks_dispatch.py backend/tests/unit/infrastructure/test_redis_publisher.py backend/tests/unit/infrastructure/test_task_dispatcher.py
git commit -m "feat: add Redis event publisher and Celery task dispatcher adapters"
```

---

### Task 10: Asyncio monitoring scheduler

**Files:**
- Create: `backend/app/monitor/__init__.py`
- Create: `backend/app/monitor/scheduler.py`
- Create: `backend/app/monitor/main.py`
- Test: `backend/tests/unit/monitor/test_scheduler.py`
- Test: `backend/tests/unit/monitor/__init__.py` (empty)

**Interfaces:**
- Produces `Scheduler` in `app.monitor.scheduler`, constructed with `(watch_target_repo: WatchTargetRepository, monitoring_service: MonitoringService, now_fn: Callable[[], datetime] = utcnow, concurrency_per_retailer: int = 4)`. Exposes `async def tick(self) -> list[DetectionEvent]` — runs one scheduling pass: fetches due targets via `list_due(now_fn())`, groups them by `retailer_slug`, and runs each retailer's group with an `asyncio.Semaphore(concurrency_per_retailer)` bounding concurrent `check_watch_target` calls; a single target's exception is caught and logged (via `structlog`), never aborts the tick for other targets. Also exposes `async def run_forever(self, poll_interval_seconds: float = 1.0) -> None` which loops `tick()` on an interval until cancelled (used by `main.py`, not unit tested — covered by `tick()` tests plus manual verification).
- Produces `backend/app/monitor/main.py` as the process entrypoint: builds the DB session, repositories, provider registry (empty until Task 23-25 register the remaining providers; Blinkit is registered here), Redis client, Celery app, `MonitoringService`, `Scheduler`, and calls `asyncio.run(scheduler.run_forever())` with a `SIGTERM`/`SIGINT` handler that calls `close()` on every registered provider before exiting (graceful shutdown).
- Consumes: `WatchTargetRepository` (Task 4), `MonitoringService` (Task 8).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/monitor/test_scheduler.py
from datetime import datetime, timezone

import pytest

from app.domain.entities import WatchTarget
from app.monitor.scheduler import Scheduler


class FakeWatchTargetRepo:
    def __init__(self, due: list[WatchTarget]) -> None:
        self._due = due

    async def list_due(self, now):
        return self._due


class FakeMonitoringService:
    def __init__(self, fail_for: set[int] | None = None) -> None:
        self.checked: list[int] = []
        self._fail_for = fail_for or set()

    async def check_watch_target(self, watch_target: WatchTarget):
        if watch_target.id in self._fail_for:
            raise RuntimeError("provider crashed")
        self.checked.append(watch_target.id)
        return []


@pytest.mark.asyncio
async def test_tick_checks_every_due_target():
    targets = [
        WatchTarget(id=1, retailer_slug="blinkit", city="Bengaluru", pincode="560001", keyword="milk"),
        WatchTarget(id=2, retailer_slug="zepto", city="Bengaluru", pincode="560001", keyword="bread"),
    ]
    repo = FakeWatchTargetRepo(due=targets)
    service = FakeMonitoringService()
    scheduler = Scheduler(watch_target_repo=repo, monitoring_service=service)

    await scheduler.tick()

    assert sorted(service.checked) == [1, 2]


@pytest.mark.asyncio
async def test_tick_continues_past_a_failing_target():
    targets = [
        WatchTarget(id=1, retailer_slug="blinkit", city="Bengaluru", pincode="560001", keyword="milk"),
        WatchTarget(id=2, retailer_slug="blinkit", city="Bengaluru", pincode="560001", keyword="bread"),
    ]
    repo = FakeWatchTargetRepo(due=targets)
    service = FakeMonitoringService(fail_for={1})
    scheduler = Scheduler(watch_target_repo=repo, monitoring_service=service)

    await scheduler.tick()

    assert service.checked == [2]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/monitor/test_scheduler.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.monitor'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/monitor/__init__.py
```

```python
# backend/app/monitor/scheduler.py
import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable

import structlog

from app.application.monitoring_service import MonitoringService
from app.domain.ports.repositories import WatchTargetRepository

logger = structlog.get_logger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Scheduler:
    def __init__(
        self,
        watch_target_repo: WatchTargetRepository,
        monitoring_service: MonitoringService,
        now_fn: Callable[[], datetime] = utcnow,
        concurrency_per_retailer: int = 4,
    ) -> None:
        self._watch_target_repo = watch_target_repo
        self._monitoring_service = monitoring_service
        self._now_fn = now_fn
        self._concurrency_per_retailer = concurrency_per_retailer

    async def tick(self) -> None:
        due_targets = await self._watch_target_repo.list_due(self._now_fn())
        by_retailer: dict[str, list] = defaultdict(list)
        for target in due_targets:
            by_retailer[target.retailer_slug].append(target)

        await asyncio.gather(
            *(self._run_retailer_group(group) for group in by_retailer.values())
        )

    async def _run_retailer_group(self, targets: list) -> None:
        semaphore = asyncio.Semaphore(self._concurrency_per_retailer)

        async def _check(target):
            async with semaphore:
                try:
                    await self._monitoring_service.check_watch_target(target)
                except Exception:
                    logger.exception("watch_target_check_failed", watch_target_id=target.id)

        await asyncio.gather(*(_check(target) for target in targets))

    async def run_forever(self, poll_interval_seconds: float = 1.0) -> None:
        while True:
            await self.tick()
            await asyncio.sleep(poll_interval_seconds)
```

```python
# backend/app/monitor/main.py
import asyncio
import signal

import redis.asyncio as redis
from celery import Celery

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.application.monitoring_service import MonitoringService
from app.infrastructure.cache.redis_publisher import RedisEventPublisher
from app.infrastructure.db.repositories import (
    SqlAlchemyDetectionEventRepository,
    SqlAlchemySnapshotRepository,
    SqlAlchemyWatchTargetRepository,
)
from app.infrastructure.db.session import get_engine, get_sessionmaker
from app.infrastructure.providers.blinkit.provider import BlinkitProvider
from app.infrastructure.providers.registry import InMemoryProviderRegistry
from app.infrastructure.tasks_dispatch import CeleryTaskDispatcher
from app.monitor.scheduler import Scheduler


async def main() -> None:
    settings = get_settings()
    configure_logging(settings)

    engine = get_engine(settings.database_url)
    session_factory = get_sessionmaker(engine)
    redis_client = redis.from_url(settings.redis_url)
    celery_app = Celery("monitor", broker=settings.redis_url)

    provider_registry = InMemoryProviderRegistry({"blinkit": BlinkitProvider})

    async with session_factory() as session:
        scheduler = Scheduler(
            watch_target_repo=SqlAlchemyWatchTargetRepository(session),
            monitoring_service=MonitoringService(
                provider_registry=provider_registry,
                watch_target_repo=SqlAlchemyWatchTargetRepository(session),
                snapshot_repo=SqlAlchemySnapshotRepository(session),
                event_repo=SqlAlchemyDetectionEventRepository(session),
                event_publisher=RedisEventPublisher(redis_client),
                task_dispatcher=CeleryTaskDispatcher(celery_app),
            ),
        )

        loop = asyncio.get_running_loop()
        stop_event = asyncio.Event()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop_event.set)

        run_task = asyncio.create_task(scheduler.run_forever())
        await stop_event.wait()
        run_task.cancel()

        for slug in provider_registry.list_active_slugs():
            await provider_registry.get(slug).close()
        await redis_client.aclose()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/unit/monitor/test_scheduler.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/monitor backend/tests/unit/monitor
git commit -m "feat: add asyncio monitoring scheduler and monitor process entrypoint"
```

---

## Phase 4: Notifications

### Task 11: Notification pipeline — repositories, NotificationSender interface, NotificationService

**Files:**
- Modify: `backend/app/domain/entities.py` (add `Watch`, `NotificationChannel`, `NotificationLog`, `NotificationContext` dataclasses)
- Modify: `backend/app/domain/ports/repositories.py` (add `get_by_id` to `WatchTargetRepository`, `SnapshotRepository`, `DetectionEventRepository`; add `WatchRepository`, `NotificationChannelRepository`, `NotificationLogRepository` ABCs)
- Modify: `backend/app/infrastructure/db/repositories.py` (implement the additions above)
- Create: `backend/app/domain/ports/notification.py`
- Create: `backend/app/application/notification_service.py`
- Test: `backend/tests/unit/application/test_notification_service.py`

**Interfaces:**
- Produces `NotificationSender` ABC in `app.domain.ports.notification`: `channel_type: ClassVar[NotificationChannelType]`, `async def send(self, channel: NotificationChannel, event: DetectionEvent, context: NotificationContext) -> bool`.
- Produces `NotificationContext(keyword: str, retailer_slug: str, event_type: EventType, snapshot: Snapshot)` dataclass — everything a sender needs to compose a message, without depending on `ProductRepository`.
- Produces `WatchRepository` (`async def list_by_watch_target(self, watch_target_id: int) -> list[Watch]`), `NotificationChannelRepository` (`async def list_for_user(self, user_id: int) -> list[NotificationChannel]`), `NotificationLogRepository` (`async def exists_recent(self, dedup_key: str, cooldown_seconds: int) -> bool`, `async def create(self, user_id, detection_event_id, channel_id, status, dedup_key) -> NotificationLog`) — ports plus `SqlAlchemy*` implementations.
- Produces `NotificationService` in `app.application.notification_service`, constructed with `(watch_target_repo, snapshot_repo, event_repo, watch_repo, channel_repo, notification_log_repo, senders: dict[NotificationChannelType, NotificationSender], cooldown_seconds: int = 900)`. Exposes `async def process_event(self, event_id: int) -> None` — the body of the Celery task in Task 13: loads the event/watch target/snapshot, finds every distinct user subscribed to that watch target, skips a user if an identical `(user, watch_target, event_type)` notification fired within `cooldown_seconds` (dedup — Global Constraint: only notify on real state transitions, no alert storms), otherwise sends through every one of that user's channels and logs the result.
- Consumes: `WatchTargetRepository`, `SnapshotRepository`, `DetectionEventRepository` (Task 4, extended here); `DetectionEvent`, `EventType` (Task 2).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/application/test_notification_service.py
from datetime import datetime, timezone

import pytest

from app.application.notification_service import NotificationService
from app.domain.entities import (
    DetectionEvent,
    NotificationChannel,
    NotificationContext,
    Snapshot,
    Watch,
    WatchTarget,
)
from app.domain.enums import Availability, EventType, NotificationChannelType
from app.domain.ports.notification import NotificationSender


def _watch_target():
    return WatchTarget(id=7, retailer_slug="blinkit", city="Bengaluru", pincode="560001", keyword="milk")


def _snapshot():
    return Snapshot(
        id=100, watch_target_id=7, timestamp=datetime.now(timezone.utc),
        availability=Availability.AVAILABLE, price=29.0, mrp=32.0, discount_pct=9.4,
        eta_minutes=10, store_name="Blinkit Koramangala", image_url=None,
        quantity_label="500 ml", variants=["500 ml"], product_url="https://blinkit.com/prn/milk/123",
    )


def _event():
    return DetectionEvent(
        id=42, watch_target_id=7, snapshot_id=100, previous_snapshot_id=None,
        event_type=EventType.STOCK_AVAILABLE, created_at=datetime.now(timezone.utc),
    )


class FakeWatchTargetRepo:
    async def get_by_id(self, watch_target_id: int):
        return _watch_target()


class FakeSnapshotRepo:
    async def get_by_id(self, snapshot_id: int):
        return _snapshot()


class FakeDetectionEventRepo:
    async def get_by_id(self, event_id: int):
        return _event()


class FakeWatchRepo:
    def __init__(self, watches: list[Watch]) -> None:
        self._watches = watches

    async def list_by_watch_target(self, watch_target_id: int):
        return self._watches


class FakeChannelRepo:
    def __init__(self, channels_by_user: dict[int, list[NotificationChannel]]) -> None:
        self._channels_by_user = channels_by_user

    async def list_for_user(self, user_id: int):
        return self._channels_by_user.get(user_id, [])


class FakeNotificationLogRepo:
    def __init__(self, recent_keys: set[str] | None = None) -> None:
        self._recent_keys = recent_keys or set()
        self.created: list[dict] = []

    async def exists_recent(self, dedup_key: str, cooldown_seconds: int) -> bool:
        return dedup_key in self._recent_keys

    async def create(self, user_id, detection_event_id, channel_id, status, dedup_key):
        self.created.append(
            {"user_id": user_id, "channel_id": channel_id, "status": status, "dedup_key": dedup_key}
        )


class FakeSender(NotificationSender):
    channel_type = NotificationChannelType.TELEGRAM

    def __init__(self) -> None:
        self.sent_to: list[NotificationChannel] = []

    async def send(self, channel, event, context: NotificationContext) -> bool:
        self.sent_to.append(channel)
        return True


@pytest.mark.asyncio
async def test_process_event_sends_to_every_channel_of_every_subscribed_user():
    watches = [Watch(id=1, user_id=10, product_id=1, watch_target_id=7, interval_seconds=300)]
    channel = NotificationChannel(id=1, user_id=10, type=NotificationChannelType.TELEGRAM, config={}, is_verified=True)
    sender = FakeSender()
    log_repo = FakeNotificationLogRepo()

    service = NotificationService(
        watch_target_repo=FakeWatchTargetRepo(),
        snapshot_repo=FakeSnapshotRepo(),
        event_repo=FakeDetectionEventRepo(),
        watch_repo=FakeWatchRepo(watches),
        channel_repo=FakeChannelRepo({10: [channel]}),
        notification_log_repo=log_repo,
        senders={NotificationChannelType.TELEGRAM: sender},
    )

    await service.process_event(42)

    assert sender.sent_to == [channel]
    assert log_repo.created == [
        {"user_id": 10, "channel_id": 1, "status": "sent", "dedup_key": "10:7:stock_available"}
    ]


@pytest.mark.asyncio
async def test_process_event_skips_user_within_cooldown():
    watches = [Watch(id=1, user_id=10, product_id=1, watch_target_id=7, interval_seconds=300)]
    channel = NotificationChannel(id=1, user_id=10, type=NotificationChannelType.TELEGRAM, config={}, is_verified=True)
    sender = FakeSender()
    log_repo = FakeNotificationLogRepo(recent_keys={"10:7:stock_available"})

    service = NotificationService(
        watch_target_repo=FakeWatchTargetRepo(),
        snapshot_repo=FakeSnapshotRepo(),
        event_repo=FakeDetectionEventRepo(),
        watch_repo=FakeWatchRepo(watches),
        channel_repo=FakeChannelRepo({10: [channel]}),
        notification_log_repo=log_repo,
        senders={NotificationChannelType.TELEGRAM: sender},
    )

    await service.process_event(42)

    assert sender.sent_to == []
    assert log_repo.created == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/application/test_notification_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.application.notification_service'`

- [ ] **Step 3: Write minimal implementation**

Add to `backend/app/domain/entities.py`:

```python
from app.domain.enums import NotificationChannelType


@dataclass
class Watch:
    id: int | None
    user_id: int
    product_id: int
    watch_target_id: int
    interval_seconds: int
    is_active: bool = True


@dataclass
class NotificationChannel:
    id: int | None
    user_id: int
    type: NotificationChannelType
    config: dict
    is_verified: bool = False


@dataclass
class NotificationLog:
    id: int | None
    user_id: int
    detection_event_id: int
    channel_id: int
    status: str
    sent_at: datetime
    dedup_key: str


@dataclass
class NotificationContext:
    keyword: str
    retailer_slug: str
    event_type: EventType
    snapshot: "Snapshot"
```

Add `get_by_id` to each existing repository ABC in `backend/app/domain/ports/repositories.py`:

```python
class WatchTargetRepository(ABC):
    # ... existing methods from Task 4 ...
    @abstractmethod
    async def get_by_id(self, watch_target_id: int) -> WatchTarget | None: ...


class SnapshotRepository(ABC):
    # ... existing methods from Task 4 ...
    @abstractmethod
    async def get_by_id(self, snapshot_id: int) -> Snapshot | None: ...


class DetectionEventRepository(ABC):
    # ... existing methods from Task 4 ...
    @abstractmethod
    async def get_by_id(self, event_id: int) -> DetectionEvent | None: ...
```

Append the three new ABCs to the same file:

```python
from app.domain.entities import NotificationChannel, NotificationLog, Watch


class WatchRepository(ABC):
    @abstractmethod
    async def list_by_watch_target(self, watch_target_id: int) -> list[Watch]: ...


class NotificationChannelRepository(ABC):
    @abstractmethod
    async def list_for_user(self, user_id: int) -> list[NotificationChannel]: ...


class NotificationLogRepository(ABC):
    @abstractmethod
    async def exists_recent(self, dedup_key: str, cooldown_seconds: int) -> bool: ...

    @abstractmethod
    async def create(
        self, user_id: int, detection_event_id: int, channel_id: int, status: str, dedup_key: str
    ) -> NotificationLog: ...
```

Add matching `get_by_id` methods to `SqlAlchemyWatchTargetRepository`, `SqlAlchemySnapshotRepository`, `SqlAlchemyDetectionEventRepository` in `backend/app/infrastructure/db/repositories.py` (each is a one-`SELECT`-by-primary-key method reusing the same `_to_*`/inline-construction pattern already used by `get_or_create`/`create`/`list_*` in that file), then append:

```python
from datetime import datetime, timedelta, timezone

from app.domain.entities import NotificationChannel, NotificationLog, Watch
from app.domain.ports.repositories import (
    NotificationChannelRepository,
    NotificationLogRepository,
    WatchRepository,
)
from app.infrastructure.db.models import NotificationChannelModel, NotificationLogModel, WatchModel


class SqlAlchemyWatchRepository(WatchRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_watch_target(self, watch_target_id: int) -> list[Watch]:
        stmt = select(WatchModel).where(
            WatchModel.watch_target_id == watch_target_id, WatchModel.is_active.is_(True)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [
            Watch(
                id=m.id, user_id=m.user_id, product_id=m.product_id,
                watch_target_id=m.watch_target_id, interval_seconds=m.interval_seconds,
                is_active=m.is_active,
            )
            for m in models
        ]


class SqlAlchemyNotificationChannelRepository(NotificationChannelRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(self, user_id: int) -> list[NotificationChannel]:
        stmt = select(NotificationChannelModel).where(
            NotificationChannelModel.user_id == user_id
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [
            NotificationChannel(
                id=m.id, user_id=m.user_id, type=NotificationChannelType(m.type),
                config=m.config_json, is_verified=m.is_verified,
            )
            for m in models
        ]


class SqlAlchemyNotificationLogRepository(NotificationLogRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def exists_recent(self, dedup_key: str, cooldown_seconds: int) -> bool:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=cooldown_seconds)
        stmt = select(NotificationLogModel).where(
            NotificationLogModel.dedup_key == dedup_key, NotificationLogModel.sent_at >= cutoff
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def create(
        self, user_id: int, detection_event_id: int, channel_id: int, status: str, dedup_key: str
    ) -> NotificationLog:
        model = NotificationLogModel(
            user_id=user_id, detection_event_id=detection_event_id, channel_id=channel_id,
            status=status, sent_at=datetime.now(timezone.utc), dedup_key=dedup_key,
        )
        self._session.add(model)
        await self._session.flush()
        return NotificationLog(
            id=model.id, user_id=model.user_id, detection_event_id=model.detection_event_id,
            channel_id=model.channel_id, status=model.status, sent_at=model.sent_at,
            dedup_key=model.dedup_key,
        )
```

```python
# backend/app/domain/ports/notification.py
from abc import ABC, abstractmethod
from typing import ClassVar

from app.domain.entities import DetectionEvent, NotificationChannel, NotificationContext
from app.domain.enums import NotificationChannelType


class NotificationSender(ABC):
    channel_type: ClassVar[NotificationChannelType]

    @abstractmethod
    async def send(
        self, channel: NotificationChannel, event: DetectionEvent, context: NotificationContext
    ) -> bool: ...
```

```python
# backend/app/application/notification_service.py
from app.domain.entities import NotificationContext
from app.domain.enums import NotificationChannelType
from app.domain.ports.notification import NotificationSender
from app.domain.ports.repositories import (
    DetectionEventRepository,
    NotificationChannelRepository,
    NotificationLogRepository,
    SnapshotRepository,
    WatchRepository,
    WatchTargetRepository,
)


class NotificationService:
    def __init__(
        self,
        watch_target_repo: WatchTargetRepository,
        snapshot_repo: SnapshotRepository,
        event_repo: DetectionEventRepository,
        watch_repo: WatchRepository,
        channel_repo: NotificationChannelRepository,
        notification_log_repo: NotificationLogRepository,
        senders: dict[NotificationChannelType, NotificationSender],
        cooldown_seconds: int = 900,
    ) -> None:
        self._watch_target_repo = watch_target_repo
        self._snapshot_repo = snapshot_repo
        self._event_repo = event_repo
        self._watch_repo = watch_repo
        self._channel_repo = channel_repo
        self._notification_log_repo = notification_log_repo
        self._senders = senders
        self._cooldown_seconds = cooldown_seconds

    async def process_event(self, event_id: int) -> None:
        event = await self._event_repo.get_by_id(event_id)
        if event is None:
            return

        watch_target = await self._watch_target_repo.get_by_id(event.watch_target_id)
        snapshot = await self._snapshot_repo.get_by_id(event.snapshot_id)
        if watch_target is None or snapshot is None:
            return

        context = NotificationContext(
            keyword=watch_target.keyword,
            retailer_slug=watch_target.retailer_slug,
            event_type=event.event_type,
            snapshot=snapshot,
        )

        watches = await self._watch_repo.list_by_watch_target(event.watch_target_id)
        seen_users: set[int] = set()
        for watch in watches:
            if watch.user_id in seen_users:
                continue
            seen_users.add(watch.user_id)

            dedup_key = f"{watch.user_id}:{event.watch_target_id}:{event.event_type.value}"
            if await self._notification_log_repo.exists_recent(dedup_key, self._cooldown_seconds):
                continue

            channels = await self._channel_repo.list_for_user(watch.user_id)
            for channel in channels:
                sender = self._senders.get(channel.type)
                if sender is None:
                    continue
                success = await sender.send(channel, event, context)
                await self._notification_log_repo.create(
                    user_id=watch.user_id,
                    detection_event_id=event.id,
                    channel_id=channel.id,
                    status="sent" if success else "failed",
                    dedup_key=dedup_key,
                )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/unit/application/test_notification_service.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain backend/app/infrastructure/db/repositories.py backend/tests/unit/application/test_notification_service.py
git commit -m "feat: add notification pipeline repositories and NotificationService"
```

---

### Task 12: Telegram and Discord notification senders

**Files:**
- Create: `backend/app/infrastructure/notifications/__init__.py`
- Create: `backend/app/infrastructure/notifications/formatting.py`
- Create: `backend/app/infrastructure/notifications/telegram.py`
- Create: `backend/app/infrastructure/notifications/discord.py`
- Test: `backend/tests/unit/notifications/test_formatting.py`
- Test: `backend/tests/unit/notifications/test_telegram_sender.py`
- Test: `backend/tests/unit/notifications/test_discord_sender.py`
- Test: `backend/tests/unit/notifications/__init__.py` (empty)

**Interfaces:**
- Produces `format_message(context: NotificationContext) -> str` in `app.infrastructure.notifications.formatting`, shared by every channel adapter.
- Produces `TelegramSender(NotificationSender)` (`channel_type = TELEGRAM`), constructed with `(http_client: HttpClientLike, bot_token: str)`. Reads `channel.config["chat_id"]`; POSTs to `https://api.telegram.org/bot{token}/sendMessage`.
- Produces `DiscordSender(NotificationSender)` (`channel_type = DISCORD`), constructed with `(http_client: HttpClientLike,)`. Reads `channel.config["webhook_url"]`; POSTs `{"content": text}` to it.
- Both depend on `HttpClientLike` Protocol: `async def post(self, url: str, json: dict) -> HttpResponseLike` where `HttpResponseLike` has `.status_code: int` — satisfied by `httpx.AsyncClient.post`.
- Consumes: `NotificationSender`, `NotificationContext` (Task 11).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/notifications/test_formatting.py
from datetime import datetime, timezone

from app.domain.entities import NotificationContext, Snapshot
from app.domain.enums import Availability, EventType
from app.infrastructure.notifications.formatting import format_message


def test_format_message_includes_keyword_retailer_and_price():
    snapshot = Snapshot(
        id=1, watch_target_id=7, timestamp=datetime.now(timezone.utc),
        availability=Availability.AVAILABLE, price=29.0, mrp=32.0, discount_pct=9.4,
        eta_minutes=10, store_name="Blinkit Koramangala", image_url=None,
        quantity_label="500 ml", variants=["500 ml"], product_url="https://blinkit.com/prn/milk/123",
    )
    context = NotificationContext(
        keyword="milk", retailer_slug="blinkit", event_type=EventType.STOCK_AVAILABLE, snapshot=snapshot
    )

    message = format_message(context)

    assert "milk" in message
    assert "Blinkit" in message
    assert "back in stock" in message
    assert "29" in message
```

```python
# backend/tests/unit/notifications/test_telegram_sender.py
from datetime import datetime, timezone

import pytest

from app.domain.entities import DetectionEvent, NotificationChannel, NotificationContext, Snapshot
from app.domain.enums import Availability, EventType, NotificationChannelType
from app.infrastructure.notifications.telegram import TelegramSender


class FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class FakeHttpClient:
    def __init__(self, status_code: int = 200) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._status_code = status_code

    async def post(self, url: str, json: dict):
        self.calls.append((url, json))
        return FakeResponse(self._status_code)


def _context():
    snapshot = Snapshot(
        id=1, watch_target_id=7, timestamp=datetime.now(timezone.utc),
        availability=Availability.AVAILABLE, price=29.0, mrp=32.0, discount_pct=9.4,
        eta_minutes=10, store_name="Blinkit Koramangala", image_url=None,
        quantity_label="500 ml", variants=["500 ml"], product_url="https://blinkit.com/prn/milk/123",
    )
    return NotificationContext(
        keyword="milk", retailer_slug="blinkit", event_type=EventType.STOCK_AVAILABLE, snapshot=snapshot
    )


def _event():
    return DetectionEvent(
        id=1, watch_target_id=7, snapshot_id=1, previous_snapshot_id=None,
        event_type=EventType.STOCK_AVAILABLE, created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_telegram_sender_posts_to_bot_api_with_chat_id():
    http_client = FakeHttpClient()
    sender = TelegramSender(http_client, bot_token="TEST_TOKEN")
    channel = NotificationChannel(
        id=1, user_id=10, type=NotificationChannelType.TELEGRAM,
        config={"chat_id": "123456"}, is_verified=True,
    )

    result = await sender.send(channel, _event(), _context())

    assert result is True
    url, payload = http_client.calls[0]
    assert url == "https://api.telegram.org/botTEST_TOKEN/sendMessage"
    assert payload["chat_id"] == "123456"


@pytest.mark.asyncio
async def test_telegram_sender_returns_false_when_chat_id_missing():
    http_client = FakeHttpClient()
    sender = TelegramSender(http_client, bot_token="TEST_TOKEN")
    channel = NotificationChannel(
        id=1, user_id=10, type=NotificationChannelType.TELEGRAM, config={}, is_verified=False
    )

    result = await sender.send(channel, _event(), _context())

    assert result is False
    assert http_client.calls == []
```

```python
# backend/tests/unit/notifications/test_discord_sender.py
from datetime import datetime, timezone

import pytest

from app.domain.entities import DetectionEvent, NotificationChannel, NotificationContext, Snapshot
from app.domain.enums import Availability, EventType, NotificationChannelType
from app.infrastructure.notifications.discord import DiscordSender


class FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class FakeHttpClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def post(self, url: str, json: dict):
        self.calls.append((url, json))
        return FakeResponse(204)


@pytest.mark.asyncio
async def test_discord_sender_posts_content_to_webhook_url():
    http_client = FakeHttpClient()
    sender = DiscordSender(http_client)
    channel = NotificationChannel(
        id=2, user_id=10, type=NotificationChannelType.DISCORD,
        config={"webhook_url": "https://discord.com/api/webhooks/abc/xyz"}, is_verified=True,
    )
    snapshot = Snapshot(
        id=1, watch_target_id=7, timestamp=datetime.now(timezone.utc),
        availability=Availability.AVAILABLE, price=29.0, mrp=32.0, discount_pct=9.4,
        eta_minutes=10, store_name="Blinkit Koramangala", image_url=None,
        quantity_label="500 ml", variants=["500 ml"], product_url="https://blinkit.com/prn/milk/123",
    )
    context = NotificationContext(
        keyword="milk", retailer_slug="blinkit", event_type=EventType.STOCK_AVAILABLE, snapshot=snapshot
    )
    event = DetectionEvent(
        id=1, watch_target_id=7, snapshot_id=1, previous_snapshot_id=None,
        event_type=EventType.STOCK_AVAILABLE, created_at=datetime.now(timezone.utc),
    )

    result = await sender.send(channel, event, context)

    assert result is True
    url, payload = http_client.calls[0]
    assert url == "https://discord.com/api/webhooks/abc/xyz"
    assert "content" in payload
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/notifications -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.infrastructure.notifications'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/infrastructure/notifications/__init__.py
```

```python
# backend/app/infrastructure/notifications/formatting.py
from app.domain.entities import NotificationContext
from app.domain.enums import EventType

_EVENT_LABELS = {
    EventType.STOCK_AVAILABLE: "back in stock",
    EventType.OUT_OF_STOCK: "out of stock",
    EventType.LOW_STOCK: "running low",
    EventType.PRICE_CHANGED: "price changed",
    EventType.NEW_VARIANT: "a new variant available",
    EventType.ETA_CHANGED: "a changed delivery time",
    EventType.STORE_CHANGED: "a changed fulfilling store",
}


def format_message(context: NotificationContext) -> str:
    label = _EVENT_LABELS[context.event_type]
    price_part = f" — ₹{context.snapshot.price:.0f}" if context.snapshot.price is not None else ""
    return f"{context.keyword} on {context.retailer_slug.title()} is now {label}{price_part}."
```

```python
# backend/app/infrastructure/notifications/telegram.py
from typing import Protocol

from app.domain.entities import DetectionEvent, NotificationChannel, NotificationContext
from app.domain.enums import NotificationChannelType
from app.domain.ports.notification import NotificationSender
from app.infrastructure.notifications.formatting import format_message


class HttpResponseLike(Protocol):
    status_code: int


class HttpClientLike(Protocol):
    async def post(self, url: str, json: dict) -> HttpResponseLike: ...


class TelegramSender(NotificationSender):
    channel_type = NotificationChannelType.TELEGRAM

    def __init__(self, http_client: HttpClientLike, bot_token: str) -> None:
        self._http_client = http_client
        self._bot_token = bot_token

    async def send(
        self, channel: NotificationChannel, event: DetectionEvent, context: NotificationContext
    ) -> bool:
        chat_id = channel.config.get("chat_id")
        if not chat_id:
            return False
        response = await self._http_client.post(
            f"https://api.telegram.org/bot{self._bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": format_message(context)},
        )
        return response.status_code == 200
```

```python
# backend/app/infrastructure/notifications/discord.py
from app.domain.entities import DetectionEvent, NotificationChannel, NotificationContext
from app.domain.enums import NotificationChannelType
from app.domain.ports.notification import NotificationSender
from app.infrastructure.notifications.formatting import format_message
from app.infrastructure.notifications.telegram import HttpClientLike


class DiscordSender(NotificationSender):
    channel_type = NotificationChannelType.DISCORD

    def __init__(self, http_client: HttpClientLike) -> None:
        self._http_client = http_client

    async def send(
        self, channel: NotificationChannel, event: DetectionEvent, context: NotificationContext
    ) -> bool:
        webhook_url = channel.config.get("webhook_url")
        if not webhook_url:
            return False
        response = await self._http_client.post(webhook_url, json={"content": format_message(context)})
        return response.status_code in (200, 204)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/unit/notifications -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure/notifications backend/tests/unit/notifications
git commit -m "feat: add Telegram and Discord notification senders"
```

---

### Task 13: Email sender, Celery app, and `process_detection_event` task

**Files:**
- Modify: `backend/app/core/config.py` (add SMTP/Telegram settings fields)
- Create: `backend/app/infrastructure/notifications/email.py`
- Create: `backend/app/tasks/__init__.py`
- Create: `backend/app/tasks/celery_app.py`
- Create: `backend/app/tasks/notifications.py`
- Test: `backend/tests/unit/notifications/test_email_sender.py`
- Test: `backend/tests/unit/tasks/test_notifications_task.py`
- Test: `backend/tests/unit/tasks/__init__.py` (empty)

**Interfaces:**
- Adds to `Settings` (`app.core.config`): `telegram_bot_token: str = ""`, `smtp_host: str = ""`, `smtp_port: int = 587`, `smtp_username: str = ""`, `smtp_password: str = ""`, `smtp_from_address: str = ""`.
- Produces `EmailSender(NotificationSender)` (`channel_type = EMAIL`) in `app.infrastructure.notifications.email`, constructed with `(smtp_host, smtp_port, smtp_username, smtp_password, from_address)`. Reads `channel.config["email"]`; sends synchronously via `smtplib.SMTP` inside `asyncio.to_thread` (keeps the async `NotificationSender` contract without needing an async SMTP library).
- Produces `celery_app` (a configured `Celery` instance) in `app.tasks.celery_app`.
- Produces the Celery task `app.tasks.notifications.process_detection_event(event_id: int) -> None`, registered under exactly that dotted name (matches the string `CeleryTaskDispatcher` from Task 9 sends to). Internally builds a fresh DB session + `httpx.AsyncClient` + all three senders + `NotificationService` (Task 11) and calls `process_event(event_id)`, committing the session on completion. The task body delegates to a separate `async def _process_detection_event_async(event_id: int) -> None` so it stays testable without a real Celery worker.
- Consumes: `NotificationService` (Task 11); `TelegramSender`, `DiscordSender` (Task 12); `SqlAlchemy*Repository` classes (Tasks 4, 11).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/notifications/test_email_sender.py
from datetime import datetime, timezone

import pytest

from app.domain.entities import DetectionEvent, NotificationChannel, NotificationContext, Snapshot
from app.domain.enums import Availability, EventType, NotificationChannelType
from app.infrastructure.notifications.email import EmailSender


class FakeSmtp:
    sent_messages: list = []

    def __init__(self, host, port):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        pass

    def login(self, username, password):
        pass

    def send_message(self, message):
        FakeSmtp.sent_messages.append(message)


@pytest.mark.asyncio
async def test_email_sender_sends_via_smtp(monkeypatch):
    import smtplib

    FakeSmtp.sent_messages = []
    monkeypatch.setattr(smtplib, "SMTP", FakeSmtp)

    sender = EmailSender("smtp.example.com", 587, "user", "pass", "alerts@example.com")
    channel = NotificationChannel(
        id=1, user_id=10, type=NotificationChannelType.EMAIL,
        config={"email": "friend@example.com"}, is_verified=True,
    )
    snapshot = Snapshot(
        id=1, watch_target_id=7, timestamp=datetime.now(timezone.utc),
        availability=Availability.AVAILABLE, price=29.0, mrp=32.0, discount_pct=9.4,
        eta_minutes=10, store_name="Blinkit Koramangala", image_url=None,
        quantity_label="500 ml", variants=["500 ml"], product_url="https://blinkit.com/prn/milk/123",
    )
    context = NotificationContext(
        keyword="milk", retailer_slug="blinkit", event_type=EventType.STOCK_AVAILABLE, snapshot=snapshot
    )
    event = DetectionEvent(
        id=1, watch_target_id=7, snapshot_id=1, previous_snapshot_id=None,
        event_type=EventType.STOCK_AVAILABLE, created_at=datetime.now(timezone.utc),
    )

    result = await sender.send(channel, event, context)

    assert result is True
    assert len(FakeSmtp.sent_messages) == 1
    assert FakeSmtp.sent_messages[0]["To"] == "friend@example.com"


@pytest.mark.asyncio
async def test_email_sender_returns_false_without_address():
    sender = EmailSender("smtp.example.com", 587, "user", "pass", "alerts@example.com")
    channel = NotificationChannel(
        id=1, user_id=10, type=NotificationChannelType.EMAIL, config={}, is_verified=False
    )
    result = await sender.send(channel, None, None)  # type: ignore[arg-type]
    assert result is False
```

```python
# backend/tests/unit/tasks/test_notifications_task.py
from app.tasks import notifications as notifications_task


def test_process_detection_event_task_is_registered_under_expected_name():
    assert "app.tasks.notifications.process_detection_event" in notifications_task.celery_app.tasks


def test_process_detection_event_invokes_async_processor(monkeypatch):
    called_with = {}

    async def fake_processor(event_id: int) -> None:
        called_with["event_id"] = event_id

    monkeypatch.setattr(notifications_task, "_process_detection_event_async", fake_processor)

    notifications_task.process_detection_event.run(42)

    assert called_with["event_id"] == 42
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/notifications/test_email_sender.py tests/unit/tasks -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.infrastructure.notifications.email'`

- [ ] **Step 3: Write minimal implementation**

Add to `Settings` in `backend/app/core/config.py`:

```python
    telegram_bot_token: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_address: str = ""
```

```python
# backend/app/infrastructure/notifications/email.py
import asyncio
import smtplib
from email.message import EmailMessage

from app.domain.entities import DetectionEvent, NotificationChannel, NotificationContext
from app.domain.enums import NotificationChannelType
from app.domain.ports.notification import NotificationSender
from app.infrastructure.notifications.formatting import format_message


class EmailSender(NotificationSender):
    channel_type = NotificationChannelType.EMAIL

    def __init__(
        self, smtp_host: str, smtp_port: int, smtp_username: str, smtp_password: str, from_address: str
    ) -> None:
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_username = smtp_username
        self._smtp_password = smtp_password
        self._from_address = from_address

    async def send(
        self, channel: NotificationChannel, event: DetectionEvent, context: NotificationContext
    ) -> bool:
        to_address = channel.config.get("email")
        if not to_address:
            return False
        return await asyncio.to_thread(self._send_sync, to_address, context)

    def _send_sync(self, to_address: str, context: NotificationContext) -> bool:
        message = EmailMessage()
        message["Subject"] = f"{context.keyword} update"
        message["From"] = self._from_address
        message["To"] = to_address
        message.set_content(format_message(context))
        try:
            with smtplib.SMTP(self._smtp_host, self._smtp_port) as smtp:
                smtp.starttls()
                smtp.login(self._smtp_username, self._smtp_password)
                smtp.send_message(message)
            return True
        except OSError:
            return False
```

```python
# backend/app/tasks/__init__.py
```

```python
# backend/app/tasks/celery_app.py
from celery import Celery

from app.core.config import get_settings


def create_celery_app() -> Celery:
    settings = get_settings()
    app = Celery("inventory_monitor", broker=settings.redis_url, backend=settings.redis_url)
    app.conf.task_routes = {"app.tasks.notifications.*": {"queue": "notifications"}}
    return app


celery_app = create_celery_app()
```

```python
# backend/app/tasks/notifications.py
import asyncio

import httpx

from app.application.notification_service import NotificationService
from app.core.config import get_settings
from app.domain.enums import NotificationChannelType
from app.infrastructure.db.repositories import (
    SqlAlchemyDetectionEventRepository,
    SqlAlchemyNotificationChannelRepository,
    SqlAlchemyNotificationLogRepository,
    SqlAlchemySnapshotRepository,
    SqlAlchemyWatchRepository,
    SqlAlchemyWatchTargetRepository,
)
from app.infrastructure.db.session import get_engine, get_sessionmaker
from app.infrastructure.notifications.discord import DiscordSender
from app.infrastructure.notifications.email import EmailSender
from app.infrastructure.notifications.telegram import TelegramSender
from app.tasks.celery_app import celery_app


async def _process_detection_event_async(event_id: int) -> None:
    settings = get_settings()
    engine = get_engine(settings.database_url)
    session_factory = get_sessionmaker(engine)
    async with session_factory() as session, httpx.AsyncClient() as http_client:
        senders = {
            NotificationChannelType.TELEGRAM: TelegramSender(http_client, settings.telegram_bot_token),
            NotificationChannelType.DISCORD: DiscordSender(http_client),
            NotificationChannelType.EMAIL: EmailSender(
                settings.smtp_host,
                settings.smtp_port,
                settings.smtp_username,
                settings.smtp_password,
                settings.smtp_from_address,
            ),
        }
        service = NotificationService(
            watch_target_repo=SqlAlchemyWatchTargetRepository(session),
            snapshot_repo=SqlAlchemySnapshotRepository(session),
            event_repo=SqlAlchemyDetectionEventRepository(session),
            watch_repo=SqlAlchemyWatchRepository(session),
            channel_repo=SqlAlchemyNotificationChannelRepository(session),
            notification_log_repo=SqlAlchemyNotificationLogRepository(session),
            senders=senders,
        )
        await service.process_event(event_id)
        await session.commit()
    await engine.dispose()


@celery_app.task(name="app.tasks.notifications.process_detection_event")
def process_detection_event(event_id: int) -> None:
    asyncio.run(_process_detection_event_async(event_id))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/unit/notifications/test_email_sender.py tests/unit/tasks -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/config.py backend/app/infrastructure/notifications/email.py backend/app/tasks backend/tests/unit/notifications/test_email_sender.py backend/tests/unit/tasks
git commit -m "feat: add email sender and wire process_detection_event Celery task"
```

---

## Phase 5: Auth

### Task 14: OTP auth — repositories, OtpProvider, AuthService, JWT

**Files:**
- Modify: `backend/app/infrastructure/db/models.py` (add `created_at: Mapped[datetime]` to `OtpChallengeModel`)
- Modify: `backend/alembic/versions/0001_initial_schema.py` (add matching `created_at` column to the `otp_challenges` table)
- Modify: `backend/app/domain/entities.py` (add `User`, `OtpChallenge`, `TokenPair` dataclasses)
- Create: `backend/app/core/security.py`
- Create: `backend/app/domain/ports/otp.py`
- Create: `backend/app/application/exceptions.py`
- Create: `backend/app/application/auth_service.py`
- Create: `backend/app/infrastructure/sms/__init__.py`
- Create: `backend/app/infrastructure/sms/console_provider.py`
- Test: `backend/tests/unit/application/test_auth_service.py`

**Interfaces:**
- Adds `User(id, phone_number, email, created_at)`, `OtpChallenge(id, phone_number, code_hash, expires_at, created_at, consumed, attempt_count)`, `TokenPair(access_token: str, refresh_token: str)` to `app.domain.entities`.
- Produces `generate_otp_code() -> str`, `hash_otp_code(code: str) -> str`, `verify_otp_code(code: str, code_hash: str) -> bool` in `app.core.security`.
- Produces `OtpProvider` ABC (`async def send_otp(self, phone_number: str, code: str) -> None`) in `app.domain.ports.otp`; `ConsoleOtpProvider` implementation in `app.infrastructure.sms.console_provider` logs the code via `structlog` instead of sending a real SMS — the default for local development, selected when `settings.otp_provider == "console"`.
- Produces `UserRepository` (`async def get_or_create_by_phone(self, phone_number: str) -> User`, `async def get_by_id(self, user_id: int) -> User | None`) and `OtpChallengeRepository` (`async def create(self, phone_number, code_hash, expires_at, created_at) -> OtpChallenge`, `async def get_latest(self, phone_number: str) -> OtpChallenge | None`, `async def count_recent(self, phone_number: str, window_seconds: int) -> int`, `async def mark_consumed(self, challenge_id: int) -> None`, `async def increment_attempt(self, challenge_id: int) -> None`) ports in `app.domain.ports.repositories`, plus `SqlAlchemy*` implementations in `app.infrastructure.db.repositories`.
- Produces `RateLimitExceededError`, `InvalidOtpError`, `InvalidTokenError` in `app.application.exceptions`.
- Produces `AuthService` in `app.application.auth_service`, constructed with `(user_repo, otp_repo, otp_provider, jwt_secret, jwt_algorithm, access_token_expire_minutes, refresh_token_expire_days, otp_ttl_seconds=300, otp_cooldown_seconds=30, otp_max_per_hour=5, otp_max_attempts=5)`. Exposes `async def request_otp(self, phone_number: str) -> None` (raises `RateLimitExceededError` past the hourly cap), `async def verify_otp(self, phone_number: str, code: str) -> TokenPair` (raises `InvalidOtpError` on wrong/expired/exhausted code; on success, get-or-creates the `User` and issues a token pair), `def verify_access_token(self, token: str) -> int` (returns `user_id`, raises `InvalidTokenError`), `def refresh(self, refresh_token: str) -> TokenPair`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/application/test_auth_service.py
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
                id=self._next_id, phone_number=phone_number, email=None,
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

    async def create(self, phone_number, code_hash, expires_at, created_at) -> OtpChallenge:
        challenge = OtpChallenge(
            id=self._next_id, phone_number=phone_number, code_hash=code_hash,
            expires_at=expires_at, created_at=created_at, consumed=False, attempt_count=0,
        )
        self._challenges[challenge.id] = challenge
        self._next_id += 1
        return challenge

    async def get_latest(self, phone_number: str):
        matches = [c for c in self._challenges.values() if c.phone_number == phone_number]
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/application/test_auth_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.application.auth_service'`

- [ ] **Step 3: Write minimal implementation**

Add `created_at: Mapped[datetime]` to `OtpChallengeModel` in `backend/app/infrastructure/db/models.py`, and `sa.Column("created_at", sa.DateTime, nullable=False)` to the `otp_challenges` table in `backend/alembic/versions/0001_initial_schema.py`.

Add to `backend/app/domain/entities.py`:

```python
@dataclass
class User:
    id: int | None
    phone_number: str
    email: str | None
    created_at: datetime


@dataclass
class OtpChallenge:
    id: int | None
    phone_number: str
    code_hash: str
    expires_at: datetime
    created_at: datetime
    consumed: bool = False
    attempt_count: int = 0


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
```

```python
# backend/app/core/security.py
import hashlib
import hmac
import secrets


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def hash_otp_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def verify_otp_code(code: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_otp_code(code), code_hash)
```

```python
# backend/app/domain/ports/otp.py
from abc import ABC, abstractmethod


class OtpProvider(ABC):
    @abstractmethod
    async def send_otp(self, phone_number: str, code: str) -> None: ...
```

```python
# backend/app/infrastructure/sms/__init__.py
```

```python
# backend/app/infrastructure/sms/console_provider.py
import structlog

from app.domain.ports.otp import OtpProvider

logger = structlog.get_logger(__name__)


class ConsoleOtpProvider(OtpProvider):
    """Local-dev OTP delivery: logs the code instead of sending a real SMS."""

    async def send_otp(self, phone_number: str, code: str) -> None:
        logger.info("otp_code_generated", phone_number=phone_number, code=code)
```

```python
# backend/app/application/exceptions.py
class RateLimitExceededError(Exception):
    pass


class InvalidOtpError(Exception):
    pass


class InvalidTokenError(Exception):
    pass
```

```python
# backend/app/application/auth_service.py
from datetime import datetime, timedelta, timezone

import jwt

from app.application.exceptions import InvalidOtpError, InvalidTokenError, RateLimitExceededError
from app.core.security import generate_otp_code, hash_otp_code, verify_otp_code
from app.domain.entities import TokenPair
from app.domain.ports.otp import OtpProvider
from app.domain.ports.repositories import OtpChallengeRepository, UserRepository


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        otp_repo: OtpChallengeRepository,
        otp_provider: OtpProvider,
        jwt_secret: str,
        jwt_algorithm: str,
        access_token_expire_minutes: int,
        refresh_token_expire_days: int,
        otp_ttl_seconds: int = 300,
        otp_cooldown_seconds: int = 30,
        otp_max_per_hour: int = 5,
        otp_max_attempts: int = 5,
    ) -> None:
        self._user_repo = user_repo
        self._otp_repo = otp_repo
        self._otp_provider = otp_provider
        self._jwt_secret = jwt_secret
        self._jwt_algorithm = jwt_algorithm
        self._access_token_expire_minutes = access_token_expire_minutes
        self._refresh_token_expire_days = refresh_token_expire_days
        self._otp_ttl_seconds = otp_ttl_seconds
        self._otp_max_per_hour = otp_max_per_hour
        self._otp_max_attempts = otp_max_attempts

    async def request_otp(self, phone_number: str) -> None:
        recent_count = await self._otp_repo.count_recent(phone_number, window_seconds=3600)
        if recent_count >= self._otp_max_per_hour:
            raise RateLimitExceededError(f"Too many OTP requests for {phone_number}")

        now = datetime.now(timezone.utc)
        code = generate_otp_code()
        await self._otp_repo.create(
            phone_number=phone_number,
            code_hash=hash_otp_code(code),
            expires_at=now + timedelta(seconds=self._otp_ttl_seconds),
            created_at=now,
        )
        await self._otp_provider.send_otp(phone_number, code)

    async def verify_otp(self, phone_number: str, code: str) -> TokenPair:
        challenge = await self._otp_repo.get_latest(phone_number)
        now = datetime.now(timezone.utc)
        if (
            challenge is None
            or challenge.consumed
            or challenge.expires_at < now
            or challenge.attempt_count >= self._otp_max_attempts
        ):
            raise InvalidOtpError("OTP is invalid, expired, or exhausted")

        if not verify_otp_code(code, challenge.code_hash):
            await self._otp_repo.increment_attempt(challenge.id)
            raise InvalidOtpError("Incorrect OTP code")

        await self._otp_repo.mark_consumed(challenge.id)
        user = await self._user_repo.get_or_create_by_phone(phone_number)
        return TokenPair(
            access_token=self._issue_token(
                user.id, timedelta(minutes=self._access_token_expire_minutes), "access"
            ),
            refresh_token=self._issue_token(
                user.id, timedelta(days=self._refresh_token_expire_days), "refresh"
            ),
        )

    def verify_access_token(self, token: str) -> int:
        return self._verify_token(token, expected_type="access")

    def refresh(self, refresh_token: str) -> TokenPair:
        user_id = self._verify_token(refresh_token, expected_type="refresh")
        return TokenPair(
            access_token=self._issue_token(
                user_id, timedelta(minutes=self._access_token_expire_minutes), "access"
            ),
            refresh_token=self._issue_token(
                user_id, timedelta(days=self._refresh_token_expire_days), "refresh"
            ),
        )

    def _verify_token(self, token: str, expected_type: str) -> int:
        try:
            payload = jwt.decode(token, self._jwt_secret, algorithms=[self._jwt_algorithm])
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc
        if payload.get("type") != expected_type:
            raise InvalidTokenError(f"Expected a {expected_type} token")
        return int(payload["sub"])

    def _issue_token(self, user_id: int, expires_delta: timedelta, token_type: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {"sub": str(user_id), "type": token_type, "iat": now, "exp": now + expires_delta}
        return jwt.encode(payload, self._jwt_secret, algorithm=self._jwt_algorithm)
```

Append `UserRepository`/`OtpChallengeRepository` ABCs to `backend/app/domain/ports/repositories.py` and their `SqlAlchemy*` implementations to `backend/app/infrastructure/db/repositories.py`, following the exact same query/construct/return pattern already used by every other repository in that file (`select(...)`, map `Model` → dataclass, `flush()` on writes).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/unit/application/test_auth_service.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure/db/models.py backend/alembic backend/app/domain backend/app/core/security.py backend/app/application/exceptions.py backend/app/application/auth_service.py backend/app/infrastructure/sms backend/tests/unit/application/test_auth_service.py
git commit -m "feat: add phone+OTP AuthService with JWT issuance"
```

---

## Phase 6: API Layer

### Task 15: FastAPI app scaffold, DI container, auth dependency, `/health`

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/main.py`
- Test: `backend/tests/unit/api/__init__.py` (empty)
- Test: `backend/tests/unit/api/test_deps.py`
- Test: `backend/tests/unit/api/test_main.py`

**Interfaces:**
- Produces DI providers in `app.api.deps`: `get_settings` (re-exported from `app.core.config`), `get_session(request: Request) -> AsyncIterator[AsyncSession]` (yields a session from `request.app.state.session_factory`), `get_otp_provider(settings=Depends) -> OtpProvider` (returns `ConsoleOtpProvider()` when `settings.otp_provider == "console"`; any other value raises `NotImplementedError` with a message pointing at implementing a new `OtpProvider` adapter — this is the intended extension point for a paid SMS provider, not a stub to fill in later), `get_auth_service(session=Depends, otp_provider=Depends, settings=Depends) -> AuthService`, and `get_current_user_id(authorization: str = Header(...), auth_service: AuthService = Depends(get_auth_service)) -> int` — parses `Bearer <token>`, calls `verify_access_token`, raises `HTTPException(401)` on `InvalidTokenError` or a malformed/missing header.
- Produces `create_app() -> FastAPI` and module-level `app` in `app.api.main`: registers a `lifespan` that builds the engine/session factory once at startup and disposes it at shutdown, adds exception handlers mapping `InvalidOtpError`→400, `InvalidTokenError`→401, `RateLimitExceededError`→429, and exposes `GET /health -> {"status": "ok"}`. Routers from Tasks 16–21 are included here as they're built (each task adds one `app.include_router(...)` line).
- Consumes: `AuthService` (Task 14); `ConsoleOtpProvider` (Task 14); `get_engine`/`get_sessionmaker` (Task 3).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/api/test_main.py
from fastapi.testclient import TestClient

from app.api.main import app


def test_health_endpoint_returns_ok():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

```python
# backend/tests/unit/api/test_deps.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/api -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.api.main'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/api/__init__.py
```

```python
# backend/app/api/deps.py
from typing import AsyncIterator

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.auth_service import AuthService
from app.application.exceptions import InvalidTokenError
from app.core.config import Settings, get_settings
from app.domain.ports.otp import OtpProvider
from app.infrastructure.db.repositories import SqlAlchemyOtpChallengeRepository, SqlAlchemyUserRepository
from app.infrastructure.sms.console_provider import ConsoleOtpProvider


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


def get_otp_provider(settings: Settings = Depends(get_settings)) -> OtpProvider:
    if settings.otp_provider == "console":
        return ConsoleOtpProvider()
    raise NotImplementedError(
        f"No OtpProvider adapter registered for '{settings.otp_provider}'. "
        "Implement one against app.domain.ports.otp.OtpProvider and wire it here."
    )


def get_auth_service(
    session: AsyncSession = Depends(get_session),
    otp_provider: OtpProvider = Depends(get_otp_provider),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(
        user_repo=SqlAlchemyUserRepository(session),
        otp_repo=SqlAlchemyOtpChallengeRepository(session),
        otp_provider=otp_provider,
        jwt_secret=settings.jwt_secret,
        jwt_algorithm=settings.jwt_algorithm,
        access_token_expire_minutes=settings.access_token_expire_minutes,
        refresh_token_expire_days=settings.refresh_token_expire_days,
    )


def get_current_user_id(
    authorization: str = Header(...),
    auth_service: AuthService = Depends(get_auth_service),
) -> int:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.removeprefix("Bearer ")
    try:
        return auth_service.verify_access_token(token)
    except InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
```

```python
# backend/app/api/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.application.exceptions import InvalidOtpError, InvalidTokenError, RateLimitExceededError
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.infrastructure.db.session import get_engine, get_sessionmaker


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings)
    engine = get_engine(settings.database_url)
    app.state.engine = engine
    app.state.session_factory = get_sessionmaker(engine)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    application = FastAPI(title="Multi-Retailer Inventory Monitor", lifespan=lifespan)

    @application.exception_handler(InvalidOtpError)
    async def _invalid_otp(request: Request, exc: InvalidOtpError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @application.exception_handler(InvalidTokenError)
    async def _invalid_token(request: Request, exc: InvalidTokenError):
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @application.exception_handler(RateLimitExceededError)
    async def _rate_limited(request: Request, exc: RateLimitExceededError):
        return JSONResponse(status_code=429, content={"detail": str(exc)})

    @application.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return application


app = create_app()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/unit/api -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api backend/tests/unit/api
git commit -m "feat: add FastAPI app scaffold, DI container, and auth dependency"
```

---

### Task 16: Auth router (`/api/v1/auth`)

**Files:**
- Create: `backend/app/api/schemas/__init__.py`
- Create: `backend/app/api/schemas/auth.py`
- Create: `backend/app/api/routers/__init__.py`
- Create: `backend/app/api/routers/auth.py`
- Modify: `backend/app/api/main.py` (register the router)
- Test: `backend/tests/unit/api/test_auth_router.py`

**Interfaces:**
- Produces Pydantic schemas in `app.api.schemas.auth`: `OtpRequestSchema(phone_number: str)`, `OtpVerifySchema(phone_number: str, code: str)`, `RefreshRequestSchema(refresh_token: str)`, `TokenPairSchema(access_token: str, refresh_token: str)`.
- Produces `router = APIRouter(prefix="/api/v1/auth", tags=["auth"])` in `app.api.routers.auth` with `POST /otp/request` (202, no body — calls `AuthService.request_otp`), `POST /otp/verify` (200 `TokenPairSchema` — calls `AuthService.verify_otp`), `POST /refresh` (200 `TokenPairSchema` — calls `AuthService.refresh`). Domain exceptions propagate to the handlers registered in Task 15 (`InvalidOtpError`→400, `RateLimitExceededError`→429).
- Consumes: `get_auth_service` (Task 15); `AuthService` (Task 14).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/api/test_auth_router.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/api/test_auth_router.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.api.routers'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/api/schemas/__init__.py
```

```python
# backend/app/api/schemas/auth.py
from pydantic import BaseModel


class OtpRequestSchema(BaseModel):
    phone_number: str


class OtpVerifySchema(BaseModel):
    phone_number: str
    code: str


class RefreshRequestSchema(BaseModel):
    refresh_token: str


class TokenPairSchema(BaseModel):
    access_token: str
    refresh_token: str
```

```python
# backend/app/api/routers/__init__.py
```

```python
# backend/app/api/routers/auth.py
from fastapi import APIRouter, Depends, status

from app.api.deps import get_auth_service
from app.api.schemas.auth import OtpRequestSchema, OtpVerifySchema, RefreshRequestSchema, TokenPairSchema
from app.application.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/otp/request", status_code=status.HTTP_202_ACCEPTED)
async def request_otp(
    body: OtpRequestSchema, auth_service: AuthService = Depends(get_auth_service)
) -> None:
    await auth_service.request_otp(body.phone_number)


@router.post("/otp/verify", response_model=TokenPairSchema)
async def verify_otp(
    body: OtpVerifySchema, auth_service: AuthService = Depends(get_auth_service)
) -> TokenPairSchema:
    tokens = await auth_service.verify_otp(body.phone_number, body.code)
    return TokenPairSchema(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/refresh", response_model=TokenPairSchema)
async def refresh(
    body: RefreshRequestSchema, auth_service: AuthService = Depends(get_auth_service)
) -> TokenPairSchema:
    tokens = auth_service.refresh(body.refresh_token)
    return TokenPairSchema(access_token=tokens.access_token, refresh_token=tokens.refresh_token)
```

Add to `backend/app/api/main.py`, inside `create_app()` before `return application`:

```python
    from app.api.routers.auth import router as auth_router

    application.include_router(auth_router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/unit/api/test_auth_router.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api backend/tests/unit/api/test_auth_router.py
git commit -m "feat: add auth router for OTP request/verify and token refresh"
```

---

### Task 17: Retailers and History routers

**Files:**
- Modify: `backend/app/domain/entities.py` (add `Retailer(id, slug, name, is_active)` dataclass)
- Modify: `backend/app/domain/ports/repositories.py` (add `RetailerRepository` ABC with `list_all() -> list[Retailer]`; add `get_by_id(self, watch_id: int) -> Watch | None` to `WatchRepository`)
- Modify: `backend/app/infrastructure/db/repositories.py` (add `SqlAlchemyRetailerRepository`; add `get_by_id` to `SqlAlchemyWatchRepository`)
- Create: `backend/app/infrastructure/db/seed.py`
- Create: `backend/app/api/schemas/retailers.py`
- Create: `backend/app/api/schemas/history.py`
- Create: `backend/app/api/routers/retailers.py`
- Create: `backend/app/api/routers/history.py`
- Modify: `backend/app/api/main.py` (seed retailers in `lifespan`; register both routers)
- Test: `backend/tests/unit/api/test_retailers_router.py`
- Test: `backend/tests/unit/api/test_history_router.py`

**Interfaces:**
- Produces `SUPPORTED_RETAILERS: list[tuple[str, str]]` (the four `(slug, name)` pairs) and `async def ensure_retailers_seeded(session: AsyncSession) -> None` in `app.infrastructure.db.seed` — idempotent upsert-by-slug, called once during API `lifespan` startup.
- Produces `GET /api/v1/retailers` → `list[RetailerSchema]` (`slug`, `name`, `is_active`), auth-protected like every non-`/health`/non-`/auth` endpoint.
- Produces `GET /api/v1/history?watch_id=<int>` → `list[HistoryEntrySchema]` (`event_id`, `event_type`, `created_at`, `snapshot: SnapshotSchema`). Verifies `watch.user_id == current_user_id` (404 if the watch doesn't exist or belongs to someone else — no information leak about other users' watches), then returns that watch's `watch_target`'s detection events newest-first via `DetectionEventRepository.list_for_watch_target` + `SnapshotRepository.get_by_id` per event.
- Consumes: `get_current_user_id` (Task 15); `WatchRepository`, `DetectionEventRepository`, `SnapshotRepository` (Tasks 4, 11, extended here).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/api/test_retailers_router.py
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.api.routers.retailers import get_retailer_repository, router
from app.domain.entities import Retailer


class FakeRetailerRepo:
    async def list_all(self):
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


def test_list_retailers_returns_seeded_retailers():
    client = TestClient(_build_app())

    response = client.get("/api/v1/retailers")

    assert response.status_code == 200
    slugs = [r["slug"] for r in response.json()]
    assert slugs == ["blinkit", "zepto"]
```

```python
# backend/tests/unit/api/test_history_router.py
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.api.routers.history import get_detection_event_repository, get_snapshot_repository, get_watch_repository, router
from app.domain.entities import DetectionEvent, Snapshot, Watch
from app.domain.enums import Availability, EventType


class FakeWatchRepo:
    def __init__(self, watch: Watch | None) -> None:
        self._watch = watch

    async def get_by_id(self, watch_id: int):
        return self._watch


class FakeDetectionEventRepo:
    async def list_for_watch_target(self, watch_target_id: int, limit: int = 50):
        return [
            DetectionEvent(
                id=1, watch_target_id=watch_target_id, snapshot_id=100, previous_snapshot_id=None,
                event_type=EventType.STOCK_AVAILABLE, created_at=datetime.now(timezone.utc),
            )
        ]


class FakeSnapshotRepo:
    async def get_by_id(self, snapshot_id: int):
        return Snapshot(
            id=snapshot_id, watch_target_id=7, timestamp=datetime.now(timezone.utc),
            availability=Availability.AVAILABLE, price=29.0, mrp=32.0, discount_pct=9.4,
            eta_minutes=10, store_name="Blinkit Koramangala", image_url=None,
            quantity_label="500 ml", variants=["500 ml"], product_url="https://blinkit.com/prn/milk/123",
        )


def _build_app(watch: Watch | None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user_id] = lambda: 10
    app.dependency_overrides[get_watch_repository] = lambda: FakeWatchRepo(watch)
    app.dependency_overrides[get_detection_event_repository] = lambda: FakeDetectionEventRepo()
    app.dependency_overrides[get_snapshot_repository] = lambda: FakeSnapshotRepo()
    return app


def test_history_returns_events_for_owned_watch():
    watch = Watch(id=5, user_id=10, product_id=1, watch_target_id=7, interval_seconds=300)
    client = TestClient(_build_app(watch))

    response = client.get("/api/v1/history", params={"watch_id": 5})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["event_type"] == "stock_available"
    assert body[0]["snapshot"]["price"] == 29.0


def test_history_returns_404_for_watch_owned_by_someone_else():
    watch = Watch(id=5, user_id=999, product_id=1, watch_target_id=7, interval_seconds=300)
    client = TestClient(_build_app(watch))

    response = client.get("/api/v1/history", params={"watch_id": 5})

    assert response.status_code == 404


def test_history_returns_404_for_missing_watch():
    client = TestClient(_build_app(None))

    response = client.get("/api/v1/history", params={"watch_id": 999})

    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/api/test_retailers_router.py tests/unit/api/test_history_router.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.api.routers.retailers'`

- [ ] **Step 3: Write minimal implementation**

Add to `backend/app/domain/entities.py`:

```python
@dataclass
class Retailer:
    id: int | None
    slug: str
    name: str
    is_active: bool = True
```

Add to `backend/app/domain/ports/repositories.py`:

```python
class RetailerRepository(ABC):
    @abstractmethod
    async def list_all(self) -> list[Retailer]: ...
```

And add `async def get_by_id(self, watch_id: int) -> Watch | None: ...` to the existing `WatchRepository` ABC.

Add matching implementations to `backend/app/infrastructure/db/repositories.py` (`SqlAlchemyRetailerRepository.list_all`, `SqlAlchemyWatchRepository.get_by_id`) following the file's established `select` → map → return pattern.

```python
# backend/app/infrastructure/db/seed.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import RetailerModel

SUPPORTED_RETAILERS: list[tuple[str, str]] = [
    ("blinkit", "Blinkit"),
    ("zepto", "Zepto"),
    ("instamart", "Swiggy Instamart"),
    ("bigbasket", "BigBasket"),
]


async def ensure_retailers_seeded(session: AsyncSession) -> None:
    existing = (await session.execute(select(RetailerModel.slug))).scalars().all()
    existing_slugs = set(existing)
    for slug, name in SUPPORTED_RETAILERS:
        if slug not in existing_slugs:
            session.add(RetailerModel(slug=slug, name=name, is_active=True))
    await session.commit()
```

```python
# backend/app/api/schemas/retailers.py
from pydantic import BaseModel


class RetailerSchema(BaseModel):
    slug: str
    name: str
    is_active: bool
```

```python
# backend/app/api/schemas/history.py
from datetime import datetime

from pydantic import BaseModel


class SnapshotSchema(BaseModel):
    availability: str
    price: float | None
    mrp: float | None
    discount_pct: float | None
    eta_minutes: int | None
    store_name: str | None
    image_url: str | None
    quantity_label: str | None
    variants: list[str]
    product_url: str | None


class HistoryEntrySchema(BaseModel):
    event_id: int
    event_type: str
    created_at: datetime
    snapshot: SnapshotSchema
```

```python
# backend/app/api/routers/retailers.py
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user_id, get_session
from app.api.schemas.retailers import RetailerSchema
from app.domain.ports.repositories import RetailerRepository
from app.infrastructure.db.repositories import SqlAlchemyRetailerRepository

router = APIRouter(prefix="/api/v1/retailers", tags=["retailers"])


def get_retailer_repository(session=Depends(get_session)) -> RetailerRepository:
    return SqlAlchemyRetailerRepository(session)


@router.get("", response_model=list[RetailerSchema])
async def list_retailers(
    user_id: int = Depends(get_current_user_id),
    repo: RetailerRepository = Depends(get_retailer_repository),
) -> list[RetailerSchema]:
    retailers = await repo.list_all()
    return [RetailerSchema(slug=r.slug, name=r.name, is_active=r.is_active) for r in retailers]
```

```python
# backend/app/api/routers/history.py
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user_id, get_session
from app.api.schemas.history import HistoryEntrySchema, SnapshotSchema
from app.domain.ports.repositories import DetectionEventRepository, SnapshotRepository, WatchRepository
from app.infrastructure.db.repositories import (
    SqlAlchemyDetectionEventRepository,
    SqlAlchemySnapshotRepository,
    SqlAlchemyWatchRepository,
)

router = APIRouter(prefix="/api/v1/history", tags=["history"])


def get_watch_repository(session=Depends(get_session)) -> WatchRepository:
    return SqlAlchemyWatchRepository(session)


def get_detection_event_repository(session=Depends(get_session)) -> DetectionEventRepository:
    return SqlAlchemyDetectionEventRepository(session)


def get_snapshot_repository(session=Depends(get_session)) -> SnapshotRepository:
    return SqlAlchemySnapshotRepository(session)


@router.get("", response_model=list[HistoryEntrySchema])
async def get_history(
    watch_id: int,
    user_id: int = Depends(get_current_user_id),
    watch_repo: WatchRepository = Depends(get_watch_repository),
    event_repo: DetectionEventRepository = Depends(get_detection_event_repository),
    snapshot_repo: SnapshotRepository = Depends(get_snapshot_repository),
) -> list[HistoryEntrySchema]:
    watch = await watch_repo.get_by_id(watch_id)
    if watch is None or watch.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Watch not found")

    events = await event_repo.list_for_watch_target(watch.watch_target_id)
    entries = []
    for event in events:
        snapshot = await snapshot_repo.get_by_id(event.snapshot_id)
        if snapshot is None:
            continue
        entries.append(
            HistoryEntrySchema(
                event_id=event.id,
                event_type=event.event_type.value,
                created_at=event.created_at,
                snapshot=SnapshotSchema(
                    availability=snapshot.availability.value
                    if hasattr(snapshot.availability, "value")
                    else snapshot.availability,
                    price=snapshot.price,
                    mrp=snapshot.mrp,
                    discount_pct=snapshot.discount_pct,
                    eta_minutes=snapshot.eta_minutes,
                    store_name=snapshot.store_name,
                    image_url=snapshot.image_url,
                    quantity_label=snapshot.quantity_label,
                    variants=snapshot.variants,
                    product_url=snapshot.product_url,
                ),
            )
        )
    return entries
```

Add to `backend/app/api/main.py`, inside `create_app()` (alongside the auth router include) and inside `lifespan` (after `app.state.session_factory = ...`):

```python
    from app.api.routers.history import router as history_router
    from app.api.routers.retailers import router as retailers_router

    application.include_router(retailers_router)
    application.include_router(history_router)
```

```python
    async with app.state.session_factory() as session:
        from app.infrastructure.db.seed import ensure_retailers_seeded

        await ensure_retailers_seeded(session)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/unit/api/test_retailers_router.py tests/unit/api/test_history_router.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain backend/app/infrastructure/db backend/app/api backend/tests/unit/api/test_retailers_router.py backend/tests/unit/api/test_history_router.py
git commit -m "feat: add retailers and history routers with retailer seeding"
```

---

### Task 18: Products and Watches routers

**Files:**
- Modify: `backend/app/domain/entities.py` (add `Product(id, user_id, name, keyword, canonical_image_url)` dataclass)
- Modify: `backend/app/domain/ports/repositories.py` (add `ProductRepository`; add `create`, `list_for_user`, `deactivate` to `WatchRepository`)
- Modify: `backend/app/infrastructure/db/repositories.py` (add `SqlAlchemyProductRepository`; extend `SqlAlchemyWatchRepository`)
- Create: `backend/app/api/schemas/products.py`
- Create: `backend/app/api/schemas/watches.py`
- Create: `backend/app/api/routers/products.py`
- Create: `backend/app/api/routers/watches.py`
- Modify: `backend/app/api/main.py` (register both routers)
- Test: `backend/tests/unit/api/test_products_router.py`
- Test: `backend/tests/unit/api/test_watches_router.py`

**Interfaces:**
- Produces `ProductRepository` (`async def create(self, user_id, name, keyword, canonical_image_url) -> Product`, `async def list_for_user(self, user_id: int) -> list[Product]`, `async def get_by_id(self, product_id: int) -> Product | None`, `async def delete(self, product_id: int) -> None`).
- Extends `WatchRepository` with `async def create(self, user_id, product_id, watch_target_id, interval_seconds) -> Watch`, `async def list_for_user(self, user_id: int) -> list[Watch]`, `async def deactivate(self, watch_id: int) -> None` (soft-delete via `is_active = False`, consistent with `list_by_watch_target`'s active-only filter from Task 11).
- Produces `POST/GET /api/v1/products`, `DELETE /api/v1/products/{product_id}` — all scoped to `get_current_user_id`; 404 (not 403) when a product exists but belongs to someone else.
- Produces `POST/GET /api/v1/watches`, `DELETE /api/v1/watches/{watch_id}` — `POST` body is `{product_id, retailer_slug, city, pincode, interval_seconds}`; validates the product belongs to the caller, then calls `WatchTargetRepository.get_or_create(retailer_slug, city, pincode, product.keyword, interval_seconds)` (Task 4 — this is the cross-user scrape dedup point) before creating the `Watch`.
- Consumes: `get_current_user_id` (Task 15); `WatchTargetRepository.get_or_create` (Task 4).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/api/test_products_router.py
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.api.routers.products import get_product_repository, router
from app.domain.entities import Product


class FakeProductRepo:
    def __init__(self) -> None:
        self._products: dict[int, Product] = {}
        self._next_id = 1

    async def create(self, user_id, name, keyword, canonical_image_url) -> Product:
        product = Product(
            id=self._next_id, user_id=user_id, name=name, keyword=keyword,
            canonical_image_url=canonical_image_url,
        )
        self._products[product.id] = product
        self._next_id += 1
        return product

    async def list_for_user(self, user_id: int):
        return [p for p in self._products.values() if p.user_id == user_id]

    async def get_by_id(self, product_id: int):
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
```

```python
# backend/tests/unit/api/test_watches_router.py
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

    async def get_by_id(self, product_id: int):
        return self._product


class FakeWatchTargetRepo:
    async def get_or_create(self, retailer_slug, city, pincode, keyword, interval_seconds):
        return WatchTarget(
            id=99, retailer_slug=retailer_slug, city=city, pincode=pincode,
            keyword=keyword, interval_seconds=interval_seconds,
        )


class FakeWatchRepo:
    def __init__(self) -> None:
        self.created: list[Watch] = []

    async def create(self, user_id, product_id, watch_target_id, interval_seconds) -> Watch:
        watch = Watch(
            id=1, user_id=user_id, product_id=product_id,
            watch_target_id=watch_target_id, interval_seconds=interval_seconds,
        )
        self.created.append(watch)
        return watch

    async def list_for_user(self, user_id: int):
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
    product = Product(id=1, user_id=10, name="Milk", keyword="amul milk 500ml", canonical_image_url=None)
    client = TestClient(_build_app(product))

    response = client.post(
        "/api/v1/watches",
        json={"product_id": 1, "retailer_slug": "blinkit", "city": "Bengaluru", "pincode": "560001", "interval_seconds": 300},
    )

    assert response.status_code == 201
    assert response.json()["watch_target_id"] == 99


def test_create_watch_for_someone_elses_product_returns_404():
    product = Product(id=1, user_id=999, name="Milk", keyword="milk", canonical_image_url=None)
    client = TestClient(_build_app(product))

    response = client.post(
        "/api/v1/watches",
        json={"product_id": 1, "retailer_slug": "blinkit", "city": "Bengaluru", "pincode": "560001", "interval_seconds": 300},
    )

    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/api/test_products_router.py tests/unit/api/test_watches_router.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.api.routers.products'`

- [ ] **Step 3: Write minimal implementation**

Add to `backend/app/domain/entities.py`:

```python
@dataclass
class Product:
    id: int | None
    user_id: int
    name: str
    keyword: str
    canonical_image_url: str | None = None
```

Add `ProductRepository` ABC to `backend/app/domain/ports/repositories.py` (`create`, `list_for_user`, `get_by_id`, `delete` as described above) and extend `WatchRepository` with `create`, `list_for_user`, `deactivate`. Add matching `SqlAlchemyProductRepository` and the new `SqlAlchemyWatchRepository` methods to `backend/app/infrastructure/db/repositories.py`, following the file's established pattern.

```python
# backend/app/api/schemas/products.py
from pydantic import BaseModel


class ProductCreateSchema(BaseModel):
    name: str
    keyword: str
    canonical_image_url: str | None = None


class ProductSchema(BaseModel):
    id: int
    name: str
    keyword: str
    canonical_image_url: str | None
```

```python
# backend/app/api/schemas/watches.py
from pydantic import BaseModel


class WatchCreateSchema(BaseModel):
    product_id: int
    retailer_slug: str
    city: str
    pincode: str
    interval_seconds: int = 300


class WatchSchema(BaseModel):
    id: int
    product_id: int
    watch_target_id: int
    interval_seconds: int
    is_active: bool = True
```

```python
# backend/app/api/routers/products.py
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user_id, get_session
from app.api.schemas.products import ProductCreateSchema, ProductSchema
from app.domain.ports.repositories import ProductRepository
from app.infrastructure.db.repositories import SqlAlchemyProductRepository

router = APIRouter(prefix="/api/v1/products", tags=["products"])


def get_product_repository(session=Depends(get_session)) -> ProductRepository:
    return SqlAlchemyProductRepository(session)


@router.post("", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreateSchema,
    user_id: int = Depends(get_current_user_id),
    repo: ProductRepository = Depends(get_product_repository),
) -> ProductSchema:
    product = await repo.create(user_id, body.name, body.keyword, body.canonical_image_url)
    return ProductSchema(
        id=product.id, name=product.name, keyword=product.keyword,
        canonical_image_url=product.canonical_image_url,
    )


@router.get("", response_model=list[ProductSchema])
async def list_products(
    user_id: int = Depends(get_current_user_id),
    repo: ProductRepository = Depends(get_product_repository),
) -> list[ProductSchema]:
    products = await repo.list_for_user(user_id)
    return [
        ProductSchema(id=p.id, name=p.name, keyword=p.keyword, canonical_image_url=p.canonical_image_url)
        for p in products
    ]


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    user_id: int = Depends(get_current_user_id),
    repo: ProductRepository = Depends(get_product_repository),
) -> None:
    product = await repo.get_by_id(product_id)
    if product is None or product.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    await repo.delete(product_id)
```

```python
# backend/app/api/routers/watches.py
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user_id, get_session
from app.api.schemas.watches import WatchCreateSchema, WatchSchema
from app.domain.ports.repositories import ProductRepository, WatchRepository, WatchTargetRepository
from app.infrastructure.db.repositories import (
    SqlAlchemyProductRepository,
    SqlAlchemyWatchRepository,
    SqlAlchemyWatchTargetRepository,
)

router = APIRouter(prefix="/api/v1/watches", tags=["watches"])


def get_product_repository(session=Depends(get_session)) -> ProductRepository:
    return SqlAlchemyProductRepository(session)


def get_watch_target_repository(session=Depends(get_session)) -> WatchTargetRepository:
    return SqlAlchemyWatchTargetRepository(session)


def get_watch_repository(session=Depends(get_session)) -> WatchRepository:
    return SqlAlchemyWatchRepository(session)


@router.post("", response_model=WatchSchema, status_code=status.HTTP_201_CREATED)
async def create_watch(
    body: WatchCreateSchema,
    user_id: int = Depends(get_current_user_id),
    product_repo: ProductRepository = Depends(get_product_repository),
    watch_target_repo: WatchTargetRepository = Depends(get_watch_target_repository),
    watch_repo: WatchRepository = Depends(get_watch_repository),
) -> WatchSchema:
    product = await product_repo.get_by_id(body.product_id)
    if product is None or product.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    watch_target = await watch_target_repo.get_or_create(
        body.retailer_slug, body.city, body.pincode, product.keyword, body.interval_seconds
    )
    watch = await watch_repo.create(user_id, product.id, watch_target.id, body.interval_seconds)
    return WatchSchema(
        id=watch.id, product_id=watch.product_id, watch_target_id=watch.watch_target_id,
        interval_seconds=watch.interval_seconds, is_active=watch.is_active,
    )


@router.get("", response_model=list[WatchSchema])
async def list_watches(
    user_id: int = Depends(get_current_user_id),
    watch_repo: WatchRepository = Depends(get_watch_repository),
) -> list[WatchSchema]:
    watches = await watch_repo.list_for_user(user_id)
    return [
        WatchSchema(
            id=w.id, product_id=w.product_id, watch_target_id=w.watch_target_id,
            interval_seconds=w.interval_seconds, is_active=w.is_active,
        )
        for w in watches
    ]


@router.delete("/{watch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watch(
    watch_id: int,
    user_id: int = Depends(get_current_user_id),
    watch_repo: WatchRepository = Depends(get_watch_repository),
) -> None:
    watch = await watch_repo.get_by_id(watch_id)
    if watch is None or watch.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Watch not found")
    await watch_repo.deactivate(watch_id)
```

Add to `backend/app/api/main.py`, alongside the other router includes:

```python
    from app.api.routers.products import router as products_router
    from app.api.routers.watches import router as watches_router

    application.include_router(products_router)
    application.include_router(watches_router)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/unit/api/test_products_router.py tests/unit/api/test_watches_router.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain backend/app/infrastructure/db/repositories.py backend/app/api backend/tests/unit/api/test_products_router.py backend/tests/unit/api/test_watches_router.py
git commit -m "feat: add products and watches routers with cross-user scrape dedup"
```

---

### Task 19: Notifications, Settings, and Logs routers

**Files:**
- Modify: `backend/app/infrastructure/db/models.py` (add `SystemLogModel`)
- Modify: `backend/alembic/versions/0001_initial_schema.py` (add `system_logs` table)
- Modify: `backend/app/domain/entities.py` (add `SystemLog(id, level, message, context, created_at)`)
- Modify: `backend/app/domain/ports/repositories.py` (extend `NotificationChannelRepository`, `NotificationLogRepository`; add `SettingsRepository`, `SystemLogRepository`)
- Modify: `backend/app/infrastructure/db/repositories.py` (implement the additions above)
- Create: `backend/app/api/schemas/notifications.py`
- Create: `backend/app/api/schemas/settings.py`
- Create: `backend/app/api/schemas/logs.py`
- Create: `backend/app/api/routers/notifications.py`
- Create: `backend/app/api/routers/settings.py`
- Create: `backend/app/api/routers/logs.py`
- Create: `backend/app/api/error_logging_middleware.py`
- Modify: `backend/app/api/main.py` (register routers + middleware)
- Test: `backend/tests/unit/api/test_notifications_router.py`
- Test: `backend/tests/unit/api/test_settings_router.py`
- Test: `backend/tests/unit/api/test_logs_router.py`

**Interfaces:**
- Extends `NotificationChannelRepository` with `create(user_id, type, config, is_verified=False) -> NotificationChannel`, `get_by_id(channel_id) -> NotificationChannel | None`, `delete(channel_id) -> None`, `mark_verified(channel_id) -> None`; extends `NotificationLogRepository` with `list_for_user(user_id, limit=50) -> list[NotificationLog]`.
- Produces `SettingsRepository` (`get_for_user(user_id) -> dict[str, Any]`, `set_for_user(user_id, key, value) -> None`).
- Produces `SystemLogRepository` (`create(level, message, context, at) -> SystemLog`, `list_recent(limit=100) -> list[SystemLog]`).
- Produces `POST/GET /api/v1/notifications/channels`, `DELETE /api/v1/notifications/channels/{id}`, `POST /api/v1/notifications/channels/{id}/verify` (self-attestation: user confirms they received a test message — no inbound webhook required for MVP), `GET /api/v1/notifications/log`.
- Produces `GET/PUT /api/v1/settings` (user-scoped key/value).
- Produces `GET /api/v1/logs` (most-recent-first `SystemLog` entries) and `ErrorLoggingMiddleware`, registered in `app.api.main`, which writes a `SystemLogModel` row (level `"error"`) for any unhandled exception before it becomes a 500 — this is what actually populates the Logs page without needing every module to know about `SystemLogRepository`.
- Consumes: `get_current_user_id` (Task 15); `NotificationChannel`, `NotificationLog` (Task 11).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/api/test_notifications_router.py
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.api.routers.notifications import get_notification_channel_repository, get_notification_log_repository, router
from app.domain.entities import NotificationChannel
from app.domain.enums import NotificationChannelType


class FakeChannelRepo:
    def __init__(self) -> None:
        self._channels: dict[int, NotificationChannel] = {}
        self._next_id = 1

    async def create(self, user_id, type, config, is_verified=False):
        channel = NotificationChannel(id=self._next_id, user_id=user_id, type=type, config=config, is_verified=is_verified)
        self._channels[channel.id] = channel
        self._next_id += 1
        return channel

    async def list_for_user(self, user_id: int):
        return [c for c in self._channels.values() if c.user_id == user_id]

    async def get_by_id(self, channel_id: int):
        return self._channels.get(channel_id)

    async def delete(self, channel_id: int) -> None:
        self._channels.pop(channel_id, None)

    async def mark_verified(self, channel_id: int) -> None:
        self._channels[channel_id].is_verified = True


class FakeLogRepo:
    async def list_for_user(self, user_id: int, limit: int = 50):
        return []


def _build_app(user_id: int = 10) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    app.dependency_overrides[get_notification_channel_repository] = lambda: FakeChannelRepo()
    app.dependency_overrides[get_notification_log_repository] = lambda: FakeLogRepo()
    return app


def test_create_channel_then_verify_it():
    app = _build_app()
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/notifications/channels", json={"type": "telegram", "config": {"chat_id": "123"}}
    )
    assert create_response.status_code == 201
    channel_id = create_response.json()["id"]
    assert create_response.json()["is_verified"] is False

    verify_response = client.post(f"/api/v1/notifications/channels/{channel_id}/verify")
    assert verify_response.status_code == 200

    list_response = client.get("/api/v1/notifications/channels")
    assert list_response.json()[0]["is_verified"] is True
```

```python
# backend/tests/unit/api/test_settings_router.py
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.api.routers.settings import get_settings_repository, router


class FakeSettingsRepo:
    def __init__(self) -> None:
        self._store: dict[int, dict] = {}

    async def get_for_user(self, user_id: int):
        return self._store.get(user_id, {})

    async def set_for_user(self, user_id: int, key: str, value) -> None:
        self._store.setdefault(user_id, {})[key] = value


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user_id] = lambda: 10
    app.dependency_overrides[get_settings_repository] = lambda: FakeSettingsRepo()
    return app


def test_set_then_get_setting():
    client = TestClient(_build_app())

    put_response = client.put("/api/v1/settings", json={"key": "timezone", "value": "Asia/Kolkata"})
    assert put_response.status_code == 200

    get_response = client.get("/api/v1/settings")
    assert get_response.json() == {"timezone": "Asia/Kolkata"}
```

```python
# backend/tests/unit/api/test_logs_router.py
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.api.routers.logs import get_system_log_repository, router
from app.domain.entities import SystemLog


class FakeSystemLogRepo:
    async def list_recent(self, limit: int = 100):
        return [
            SystemLog(id=1, level="error", message="provider crashed", context={}, created_at=datetime.now(timezone.utc))
        ]


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user_id] = lambda: 10
    app.dependency_overrides[get_system_log_repository] = lambda: FakeSystemLogRepo()
    return app


def test_list_logs_returns_recent_entries():
    client = TestClient(_build_app())

    response = client.get("/api/v1/logs")

    assert response.status_code == 200
    assert response.json()[0]["message"] == "provider crashed"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/api/test_notifications_router.py tests/unit/api/test_settings_router.py tests/unit/api/test_logs_router.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.api.routers.notifications'`

- [ ] **Step 3: Write minimal implementation**

Add `SystemLogModel` to `backend/app/infrastructure/db/models.py`:

```python
class SystemLogModel(Base):
    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str]
    message: Mapped[str]
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime]
```

Add the matching `op.create_table("system_logs", ...)` block to `0001_initial_schema.py` (columns: `id`, `level` String, `message` String, `context` JSON default `dict`, `created_at` DateTime) and add `"system_logs"` to the `downgrade()` drop list.

Add `SystemLog` dataclass to `backend/app/domain/entities.py`:

```python
@dataclass
class SystemLog:
    id: int | None
    level: str
    message: str
    context: dict
    created_at: datetime
```

Extend the ABCs in `backend/app/domain/ports/repositories.py` (`NotificationChannelRepository.create/get_by_id/delete/mark_verified`, `NotificationLogRepository.list_for_user`) and add `SettingsRepository`, `SystemLogRepository` — implement all of it in `backend/app/infrastructure/db/repositories.py` following the file's established pattern (`SqlAlchemySettingsRepository`, `SqlAlchemySystemLogRepository`).

```python
# backend/app/api/schemas/notifications.py
from pydantic import BaseModel


class ChannelCreateSchema(BaseModel):
    type: str
    config: dict


class ChannelSchema(BaseModel):
    id: int
    type: str
    config: dict
    is_verified: bool


class NotificationLogEntrySchema(BaseModel):
    id: int
    detection_event_id: int
    channel_id: int
    status: str
    sent_at: str
```

```python
# backend/app/api/schemas/settings.py
from typing import Any

from pydantic import BaseModel


class SettingUpdateSchema(BaseModel):
    key: str
    value: Any
```

```python
# backend/app/api/schemas/logs.py
from datetime import datetime

from pydantic import BaseModel


class SystemLogSchema(BaseModel):
    id: int
    level: str
    message: str
    context: dict
    created_at: datetime
```

```python
# backend/app/api/routers/notifications.py
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user_id, get_session
from app.api.schemas.notifications import ChannelCreateSchema, ChannelSchema, NotificationLogEntrySchema
from app.domain.enums import NotificationChannelType
from app.domain.ports.repositories import NotificationChannelRepository, NotificationLogRepository
from app.infrastructure.db.repositories import (
    SqlAlchemyNotificationChannelRepository,
    SqlAlchemyNotificationLogRepository,
)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


def get_notification_channel_repository(session=Depends(get_session)) -> NotificationChannelRepository:
    return SqlAlchemyNotificationChannelRepository(session)


def get_notification_log_repository(session=Depends(get_session)) -> NotificationLogRepository:
    return SqlAlchemyNotificationLogRepository(session)


@router.post("/channels", response_model=ChannelSchema, status_code=status.HTTP_201_CREATED)
async def create_channel(
    body: ChannelCreateSchema,
    user_id: int = Depends(get_current_user_id),
    repo: NotificationChannelRepository = Depends(get_notification_channel_repository),
) -> ChannelSchema:
    channel = await repo.create(user_id, NotificationChannelType(body.type), body.config)
    return ChannelSchema(id=channel.id, type=channel.type.value, config=channel.config, is_verified=channel.is_verified)


@router.get("/channels", response_model=list[ChannelSchema])
async def list_channels(
    user_id: int = Depends(get_current_user_id),
    repo: NotificationChannelRepository = Depends(get_notification_channel_repository),
) -> list[ChannelSchema]:
    channels = await repo.list_for_user(user_id)
    return [ChannelSchema(id=c.id, type=c.type.value, config=c.config, is_verified=c.is_verified) for c in channels]


@router.post("/channels/{channel_id}/verify")
async def verify_channel(
    channel_id: int,
    user_id: int = Depends(get_current_user_id),
    repo: NotificationChannelRepository = Depends(get_notification_channel_repository),
) -> dict:
    channel = await repo.get_by_id(channel_id)
    if channel is None or channel.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel not found")
    await repo.mark_verified(channel_id)
    return {"status": "verified"}


@router.delete("/channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: int,
    user_id: int = Depends(get_current_user_id),
    repo: NotificationChannelRepository = Depends(get_notification_channel_repository),
) -> None:
    channel = await repo.get_by_id(channel_id)
    if channel is None or channel.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel not found")
    await repo.delete(channel_id)


@router.get("/log", response_model=list[NotificationLogEntrySchema])
async def list_notification_log(
    user_id: int = Depends(get_current_user_id),
    repo: NotificationLogRepository = Depends(get_notification_log_repository),
) -> list[NotificationLogEntrySchema]:
    entries = await repo.list_for_user(user_id)
    return [
        NotificationLogEntrySchema(
            id=e.id, detection_event_id=e.detection_event_id, channel_id=e.channel_id,
            status=e.status, sent_at=e.sent_at.isoformat(),
        )
        for e in entries
    ]
```

```python
# backend/app/api/routers/settings.py
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user_id, get_session
from app.api.schemas.settings import SettingUpdateSchema
from app.domain.ports.repositories import SettingsRepository
from app.infrastructure.db.repositories import SqlAlchemySettingsRepository

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


def get_settings_repository(session=Depends(get_session)) -> SettingsRepository:
    return SqlAlchemySettingsRepository(session)


@router.get("")
async def get_settings_for_user(
    user_id: int = Depends(get_current_user_id),
    repo: SettingsRepository = Depends(get_settings_repository),
) -> dict:
    return await repo.get_for_user(user_id)


@router.put("")
async def update_setting(
    body: SettingUpdateSchema,
    user_id: int = Depends(get_current_user_id),
    repo: SettingsRepository = Depends(get_settings_repository),
) -> dict:
    await repo.set_for_user(user_id, body.key, body.value)
    return await repo.get_for_user(user_id)
```

```python
# backend/app/api/routers/logs.py
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user_id, get_session
from app.api.schemas.logs import SystemLogSchema
from app.domain.ports.repositories import SystemLogRepository
from app.infrastructure.db.repositories import SqlAlchemySystemLogRepository

router = APIRouter(prefix="/api/v1/logs", tags=["logs"])


def get_system_log_repository(session=Depends(get_session)) -> SystemLogRepository:
    return SqlAlchemySystemLogRepository(session)


@router.get("", response_model=list[SystemLogSchema])
async def list_logs(
    user_id: int = Depends(get_current_user_id),
    repo: SystemLogRepository = Depends(get_system_log_repository),
) -> list[SystemLogSchema]:
    logs = await repo.list_recent()
    return [
        SystemLogSchema(id=l.id, level=l.level, message=l.message, context=l.context, created_at=l.created_at)
        for l in logs
    ]
```

```python
# backend/app/api/error_logging_middleware.py
from datetime import datetime, timezone

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = structlog.get_logger(__name__)


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            logger.exception("unhandled_request_error", path=request.url.path)
            async with request.app.state.session_factory() as session:
                from app.infrastructure.db.repositories import SqlAlchemySystemLogRepository

                await SqlAlchemySystemLogRepository(session).create(
                    level="error",
                    message=str(exc),
                    context={"path": request.url.path},
                    at=datetime.now(timezone.utc),
                )
                await session.commit()
            raise
```

Add to `backend/app/api/main.py`:

```python
    from app.api.error_logging_middleware import ErrorLoggingMiddleware
    from app.api.routers.logs import router as logs_router
    from app.api.routers.notifications import router as notifications_router
    from app.api.routers.settings import router as settings_router

    application.add_middleware(ErrorLoggingMiddleware)
    application.include_router(notifications_router)
    application.include_router(settings_router)
    application.include_router(logs_router)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/unit/api/test_notifications_router.py tests/unit/api/test_settings_router.py tests/unit/api/test_logs_router.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure/db backend/app/domain backend/app/api backend/tests/unit/api/test_notifications_router.py backend/tests/unit/api/test_settings_router.py backend/tests/unit/api/test_logs_router.py
git commit -m "feat: add notifications, settings, and logs routers"
```

---

### Task 20: Analytics — availability/restock computation and router

**Files:**
- Modify: `backend/app/domain/ports/repositories.py` (add `list_since(self, watch_target_id: int, since: datetime) -> list[Snapshot]` to `SnapshotRepository`)
- Modify: `backend/app/infrastructure/db/repositories.py` (implement `list_since` on `SqlAlchemySnapshotRepository`)
- Create: `backend/app/application/analytics.py`
- Create: `backend/app/api/schemas/analytics.py`
- Create: `backend/app/api/routers/analytics.py`
- Modify: `backend/app/api/main.py` (register router)
- Test: `backend/tests/unit/application/test_analytics.py`
- Test: `backend/tests/unit/api/test_analytics_router.py`

**Interfaces:**
- Produces pure function `compute_availability_summary(events: list[DetectionEvent], period_start: datetime, period_end: datetime) -> AvailabilitySummary` in `app.application.analytics`, where `AvailabilitySummary(availability_pct: float, restock_count: int, total_downtime_minutes: float, average_downtime_minutes: float)`. Walks `OUT_OF_STOCK`→`STOCK_AVAILABLE` event pairs to compute downtime windows (an unclosed trailing `OUT_OF_STOCK` counts as down until `period_end`); no I/O, fully unit-testable — this is what makes "restock frequency," "downtime," and "average availability" from the spec real, computed numbers instead of vague dashboard copy.
- Produces `GET /api/v1/analytics/price-history?watch_id=<int>&days=<int=30>` → `list[{"timestamp": str, "price": float | None}]`, and `GET /api/v1/analytics/availability?watch_id=<int>&days=<int=30>` → `AvailabilitySummarySchema`. Both scoped to the caller's own watch (same 404-on-mismatch pattern as Task 17's history router).
- Consumes: `DetectionEventRepository.list_for_watch_target` (Task 4); `SnapshotRepository.list_since` (added here); `WatchRepository.get_by_id` (Task 17).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/application/test_analytics.py
from datetime import datetime, timedelta, timezone

from app.application.analytics import compute_availability_summary
from app.domain.entities import DetectionEvent
from app.domain.enums import EventType


def _event(event_type: EventType, minutes_from_start: int, start: datetime) -> DetectionEvent:
    return DetectionEvent(
        id=None, watch_target_id=1, snapshot_id=1, previous_snapshot_id=None,
        event_type=event_type, created_at=start + timedelta(minutes=minutes_from_start),
    )


def test_computes_downtime_and_restock_count_for_closed_outage():
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=10)
    events = [
        _event(EventType.OUT_OF_STOCK, 60, start),
        _event(EventType.STOCK_AVAILABLE, 120, start),
    ]

    summary = compute_availability_summary(events, period_start=start, period_end=end)

    assert summary.restock_count == 1
    assert summary.total_downtime_minutes == 60.0
    assert summary.average_downtime_minutes == 60.0
    assert 89.0 < summary.availability_pct < 91.0


def test_trailing_out_of_stock_counts_as_down_until_period_end():
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=2)
    events = [_event(EventType.OUT_OF_STOCK, 60, start)]

    summary = compute_availability_summary(events, period_start=start, period_end=end)

    assert summary.total_downtime_minutes == 60.0
    assert summary.restock_count == 0


def test_no_events_means_full_availability():
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=1)

    summary = compute_availability_summary([], period_start=start, period_end=end)

    assert summary.availability_pct == 100.0
    assert summary.total_downtime_minutes == 0.0
```

```python
# backend/tests/unit/api/test_analytics_router.py
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.api.routers.analytics import get_detection_event_repository, get_snapshot_repository, get_watch_repository, router
from app.domain.entities import DetectionEvent, Snapshot, Watch
from app.domain.enums import Availability, EventType


class FakeWatchRepo:
    def __init__(self, watch: Watch | None) -> None:
        self._watch = watch

    async def get_by_id(self, watch_id: int):
        return self._watch


class FakeSnapshotRepo:
    async def list_since(self, watch_target_id: int, since: datetime):
        return [
            Snapshot(
                id=1, watch_target_id=watch_target_id, timestamp=datetime.now(timezone.utc),
                availability=Availability.AVAILABLE, price=29.0, mrp=32.0, discount_pct=9.4,
                eta_minutes=10, store_name="Blinkit Koramangala", image_url=None,
                quantity_label="500 ml", variants=[], product_url=None,
            )
        ]


class FakeDetectionEventRepo:
    async def list_for_watch_target(self, watch_target_id: int, limit: int = 50):
        return []


def _build_app(watch: Watch | None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user_id] = lambda: 10
    app.dependency_overrides[get_watch_repository] = lambda: FakeWatchRepo(watch)
    app.dependency_overrides[get_snapshot_repository] = lambda: FakeSnapshotRepo()
    app.dependency_overrides[get_detection_event_repository] = lambda: FakeDetectionEventRepo()
    return app


def test_price_history_returns_points_for_owned_watch():
    watch = Watch(id=5, user_id=10, product_id=1, watch_target_id=7, interval_seconds=300)
    client = TestClient(_build_app(watch))

    response = client.get("/api/v1/analytics/price-history", params={"watch_id": 5})

    assert response.status_code == 200
    assert response.json()[0]["price"] == 29.0


def test_availability_summary_returns_404_for_unowned_watch():
    watch = Watch(id=5, user_id=999, product_id=1, watch_target_id=7, interval_seconds=300)
    client = TestClient(_build_app(watch))

    response = client.get("/api/v1/analytics/availability", params={"watch_id": 5})

    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/application/test_analytics.py tests/unit/api/test_analytics_router.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.application.analytics'`

- [ ] **Step 3: Write minimal implementation**

Add `list_since` to `SnapshotRepository` ABC and `SqlAlchemySnapshotRepository` (filter `SnapshotModel.watch_target_id == watch_target_id` and `SnapshotModel.timestamp >= since`, order ascending), following the file's established pattern.

```python
# backend/app/application/analytics.py
from dataclasses import dataclass
from datetime import datetime

from app.domain.entities import DetectionEvent
from app.domain.enums import EventType


@dataclass
class AvailabilitySummary:
    availability_pct: float
    restock_count: int
    total_downtime_minutes: float
    average_downtime_minutes: float


def compute_availability_summary(
    events: list[DetectionEvent], period_start: datetime, period_end: datetime
) -> AvailabilitySummary:
    sorted_events = sorted(events, key=lambda e: e.created_at)

    downtime_periods: list[tuple[datetime, datetime]] = []
    open_outage_start: datetime | None = None
    for event in sorted_events:
        if event.event_type == EventType.OUT_OF_STOCK:
            open_outage_start = event.created_at
        elif event.event_type == EventType.STOCK_AVAILABLE and open_outage_start is not None:
            downtime_periods.append((open_outage_start, event.created_at))
            open_outage_start = None
    if open_outage_start is not None:
        downtime_periods.append((open_outage_start, period_end))

    total_downtime_minutes = sum(
        (end - start).total_seconds() for start, end in downtime_periods
    ) / 60
    total_period_minutes = (period_end - period_start).total_seconds() / 60
    availability_pct = (
        100.0
        if total_period_minutes <= 0
        else max(0.0, 100 * (1 - total_downtime_minutes / total_period_minutes))
    )
    restock_count = sum(1 for e in sorted_events if e.event_type == EventType.STOCK_AVAILABLE)
    average_downtime_minutes = (
        total_downtime_minutes / len(downtime_periods) if downtime_periods else 0.0
    )

    return AvailabilitySummary(
        availability_pct=round(availability_pct, 2),
        restock_count=restock_count,
        total_downtime_minutes=round(total_downtime_minutes, 2),
        average_downtime_minutes=round(average_downtime_minutes, 2),
    )
```

```python
# backend/app/api/schemas/analytics.py
from pydantic import BaseModel


class PricePointSchema(BaseModel):
    timestamp: str
    price: float | None


class AvailabilitySummarySchema(BaseModel):
    availability_pct: float
    restock_count: int
    total_downtime_minutes: float
    average_downtime_minutes: float
```

```python
# backend/app/api/routers/analytics.py
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user_id, get_session
from app.api.schemas.analytics import AvailabilitySummarySchema, PricePointSchema
from app.application.analytics import compute_availability_summary
from app.domain.ports.repositories import DetectionEventRepository, SnapshotRepository, WatchRepository
from app.infrastructure.db.repositories import (
    SqlAlchemyDetectionEventRepository,
    SqlAlchemySnapshotRepository,
    SqlAlchemyWatchRepository,
)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


def get_watch_repository(session=Depends(get_session)) -> WatchRepository:
    return SqlAlchemyWatchRepository(session)


def get_snapshot_repository(session=Depends(get_session)) -> SnapshotRepository:
    return SqlAlchemySnapshotRepository(session)


def get_detection_event_repository(session=Depends(get_session)) -> DetectionEventRepository:
    return SqlAlchemyDetectionEventRepository(session)


async def _owned_watch(watch_id: int, user_id: int, watch_repo: WatchRepository):
    watch = await watch_repo.get_by_id(watch_id)
    if watch is None or watch.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Watch not found")
    return watch


@router.get("/price-history", response_model=list[PricePointSchema])
async def price_history(
    watch_id: int,
    days: int = 30,
    user_id: int = Depends(get_current_user_id),
    watch_repo: WatchRepository = Depends(get_watch_repository),
    snapshot_repo: SnapshotRepository = Depends(get_snapshot_repository),
) -> list[PricePointSchema]:
    watch = await _owned_watch(watch_id, user_id, watch_repo)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    snapshots = await snapshot_repo.list_since(watch.watch_target_id, since)
    return [PricePointSchema(timestamp=s.timestamp.isoformat(), price=s.price) for s in snapshots]


@router.get("/availability", response_model=AvailabilitySummarySchema)
async def availability_summary(
    watch_id: int,
    days: int = 30,
    user_id: int = Depends(get_current_user_id),
    watch_repo: WatchRepository = Depends(get_watch_repository),
    event_repo: DetectionEventRepository = Depends(get_detection_event_repository),
) -> AvailabilitySummarySchema:
    watch = await _owned_watch(watch_id, user_id, watch_repo)
    period_end = datetime.now(timezone.utc)
    period_start = period_end - timedelta(days=days)
    events = await event_repo.list_for_watch_target(watch.watch_target_id, limit=1000)
    summary = compute_availability_summary(events, period_start, period_end)
    return AvailabilitySummarySchema(
        availability_pct=summary.availability_pct,
        restock_count=summary.restock_count,
        total_downtime_minutes=summary.total_downtime_minutes,
        average_downtime_minutes=summary.average_downtime_minutes,
    )
```

Add to `backend/app/api/main.py`:

```python
    from app.api.routers.analytics import router as analytics_router

    application.include_router(analytics_router)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/unit/application/test_analytics.py tests/unit/api/test_analytics_router.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/application/analytics.py backend/app/api backend/app/domain/ports/repositories.py backend/app/infrastructure/db/repositories.py backend/tests/unit/application/test_analytics.py backend/tests/unit/api/test_analytics_router.py
git commit -m "feat: add availability/restock analytics computation and router"
```

---

### Task 21: WebSocket live-update endpoint

**Files:**
- Create: `backend/app/infrastructure/cache/redis_subscriber.py`
- Create: `backend/app/api/websocket.py`
- Modify: `backend/app/api/main.py` (register the websocket router)
- Test: `backend/tests/unit/infrastructure/test_redis_subscriber.py`
- Test: `backend/tests/unit/api/test_websocket.py`

**Interfaces:**
- Produces `RedisSubscriber` in `app.infrastructure.cache.redis_subscriber`, constructed with any object exposing `.pubsub()` (matches `redis.asyncio.Redis`). Exposes `async def listen(self, channels: list[str]) -> AsyncIterator[dict]` — subscribes, then yields each message's JSON-decoded `data` forever (an infinite generator by design; callers stop it by breaking the loop or calling `.aclose()`).
- Produces `GET /ws?token=<jwt>` WebSocket route in `app.api.websocket`: validates the token via `AuthService.verify_access_token` (closes with code 4401 on failure), loads the caller's watches via `WatchRepository.list_for_user`, subscribes to `events:{watch_target_id}` for each one (closes with code 4404 if the user has no active watches), and forwards every message from `RedisSubscriber.listen` to the client as JSON until disconnect.
- Consumes: `RedisEventPublisher`'s channel naming convention `events:{watch_target_id}` (Task 9 — this is the other end of that publish); `get_auth_service` (Task 15); `WatchRepository.list_for_user` (Task 18).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/infrastructure/test_redis_subscriber.py
import json

import pytest

from app.infrastructure.cache.redis_subscriber import RedisSubscriber


class FakePubSub:
    def __init__(self, messages: list[dict]) -> None:
        self._messages = [{"type": "message", "data": json.dumps(m)} for m in messages]
        self.subscribed_channels: list[str] = []
        self.closed = False

    async def subscribe(self, *channels: str) -> None:
        self.subscribed_channels.extend(channels)

    async def unsubscribe(self, *channels: str) -> None:
        pass

    async def get_message(self, ignore_subscribe_messages: bool = True, timeout: float | None = None):
        if self._messages:
            return self._messages.pop(0)
        return None

    async def close(self) -> None:
        self.closed = True


class FakeRedisClient:
    def __init__(self, pubsub: FakePubSub) -> None:
        self._pubsub = pubsub

    def pubsub(self):
        return self._pubsub


@pytest.mark.asyncio
async def test_listen_subscribes_and_yields_decoded_messages():
    fake_pubsub = FakePubSub([{"event_id": 1}, {"event_id": 2}])
    subscriber = RedisSubscriber(FakeRedisClient(fake_pubsub))

    gen = subscriber.listen(["events:7"])
    first = await gen.__anext__()
    second = await gen.__anext__()
    await gen.aclose()

    assert first == {"event_id": 1}
    assert second == {"event_id": 2}
    assert fake_pubsub.subscribed_channels == ["events:7"]
```

```python
# backend/tests/unit/api/test_websocket.py
from fastapi import FastAPI
from fastapi.testclient import TestClient

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
    watch = Watch(id=1, user_id=10, product_id=1, watch_target_id=7, interval_seconds=300)
    app = _build_app([watch], [{"event_type": "stock_available"}])
    client = TestClient(app)

    with client.websocket_connect("/ws?token=valid-token") as websocket:
        data = websocket.receive_json()

    assert data == {"event_type": "stock_available"}


def test_websocket_closes_with_4401_on_invalid_token():
    app = _build_app([], [])
    client = TestClient(app)

    with client.websocket_connect("/ws?token=garbage") as websocket:
        with __import__("pytest").raises(Exception):
            websocket.receive_json()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/infrastructure/test_redis_subscriber.py tests/unit/api/test_websocket.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.infrastructure.cache.redis_subscriber'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/infrastructure/cache/redis_subscriber.py
import json
from typing import AsyncIterator, Protocol


class PubSubLike(Protocol):
    async def subscribe(self, *channels: str) -> None: ...
    async def unsubscribe(self, *channels: str) -> None: ...
    async def get_message(
        self, ignore_subscribe_messages: bool = True, timeout: float | None = None
    ) -> dict | None: ...
    async def close(self) -> None: ...


class RedisClientLike(Protocol):
    def pubsub(self) -> PubSubLike: ...


class RedisSubscriber:
    def __init__(self, redis_client: RedisClientLike) -> None:
        self._redis_client = redis_client

    async def listen(self, channels: list[str]) -> AsyncIterator[dict]:
        pubsub = self._redis_client.pubsub()
        await pubsub.subscribe(*channels)
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message is not None and message.get("type") == "message":
                    yield json.loads(message["data"])
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.close()
```

```python
# backend/app/api/websocket.py
import redis.asyncio as redis
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.api.deps import get_auth_service
from app.application.auth_service import AuthService
from app.application.exceptions import InvalidTokenError
from app.core.config import get_settings
from app.domain.ports.repositories import WatchRepository
from app.infrastructure.cache.redis_subscriber import RedisSubscriber
from app.infrastructure.db.repositories import SqlAlchemyWatchRepository
from app.infrastructure.db.session import get_engine, get_sessionmaker

router = APIRouter()


async def get_watch_repository(websocket: WebSocket) -> WatchRepository:
    settings = get_settings()
    engine = get_engine(settings.database_url)
    session_factory = get_sessionmaker(engine)
    async with session_factory() as session:
        yield SqlAlchemyWatchRepository(session)


def get_redis_subscriber() -> RedisSubscriber:
    settings = get_settings()
    return RedisSubscriber(redis.from_url(settings.redis_url))


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    auth_service: AuthService = Depends(get_auth_service),
    watch_repo: WatchRepository = Depends(get_watch_repository),
    subscriber: RedisSubscriber = Depends(get_redis_subscriber),
) -> None:
    try:
        user_id = auth_service.verify_access_token(token)
    except InvalidTokenError:
        await websocket.close(code=4401)
        return

    watches = await watch_repo.list_for_user(user_id)
    if not watches:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    channels = [f"events:{w.watch_target_id}" for w in watches]
    try:
        async for message in subscriber.listen(channels):
            await websocket.send_json(message)
    except WebSocketDisconnect:
        pass
```

Add to `backend/app/api/main.py`:

```python
    from app.api.websocket import router as websocket_router

    application.include_router(websocket_router)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/unit/infrastructure/test_redis_subscriber.py tests/unit/api/test_websocket.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure/cache/redis_subscriber.py backend/app/api backend/tests/unit/infrastructure/test_redis_subscriber.py backend/tests/unit/api/test_websocket.py
git commit -m "feat: add WebSocket endpoint streaming live detection events per user"
```

---

## Phase 7: Remaining Providers

Tasks 22–24 each follow the exact structure Task 7 established for Blinkit: a `selectors.py` with `data-test-id`-based selectors (verify against the live DOM before relying on them in production — see Task 7's selector maintenance note, which applies identically here), a `provider.py` whose extraction methods take an already-loaded `Page` and do no navigation (unit-testable), and navigation methods (`initialize`, `search_product`, `get_product`, `check_availability`, `health_check`) that own all live I/O and are covered by the opt-in integration tier, not these unit tests. Each task also registers its provider in `backend/app/monitor/main.py`'s `InMemoryProviderRegistry`.

### Task 22: Zepto provider

**Files:**
- Create: `backend/app/infrastructure/providers/zepto/__init__.py`
- Create: `backend/app/infrastructure/providers/zepto/selectors.py`
- Create: `backend/app/infrastructure/providers/zepto/provider.py`
- Create: `backend/tests/fixtures/zepto_product_available.html`
- Create: `backend/tests/fixtures/zepto_product_out_of_stock.html`
- Modify: `backend/app/monitor/main.py` (register `"zepto": ZeptoProvider` in the provider registry)
- Test: `backend/tests/unit/providers/test_zepto_provider.py`

**Interfaces:**
- Produces `ZeptoProvider(BaseRetailProvider)` with `slug = "zepto"`, same method shape as `BlinkitProvider` (Task 7), navigating `https://www.zeptonow.com`.
- Consumes: `BaseRetailProvider`, `LocationContext`, `ProviderProductResult`, `Availability` (Tasks 2, 5).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/providers/test_zepto_provider.py
from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from app.domain.enums import Availability
from app.infrastructure.providers.zepto.provider import ZeptoProvider

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


@pytest.fixture
async def page():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        pg = await browser.new_page()
        yield pg
        await browser.close()


@pytest.mark.asyncio
async def test_extracts_available_product_fields(page):
    html = (FIXTURES / "zepto_product_available.html").read_text()
    await page.set_content(html)
    provider = ZeptoProvider()

    availability = await provider.check_availability_from_page(page)
    price, mrp, discount_pct = await provider.extract_price(page)
    eta_minutes = await provider.extract_eta(page)
    variants = await provider.extract_variants(page)

    assert availability == Availability.AVAILABLE
    assert price == 27.0
    assert mrp == 30.0
    assert discount_pct == 10.0
    assert eta_minutes == 8
    assert variants == ["500 ml"]


@pytest.mark.asyncio
async def test_extracts_out_of_stock_product(page):
    html = (FIXTURES / "zepto_product_out_of_stock.html").read_text()
    await page.set_content(html)
    provider = ZeptoProvider()

    assert await provider.check_availability_from_page(page) == Availability.OUT_OF_STOCK


@pytest.mark.asyncio
async def test_health_check_returns_false_before_initialize():
    provider = ZeptoProvider()
    assert await provider.health_check() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/providers/test_zepto_provider.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.infrastructure.providers.zepto'`

- [ ] **Step 3: Write minimal implementation**

```html
<!-- backend/tests/fixtures/zepto_product_available.html -->
<!DOCTYPE html>
<html>
<body>
  <h1 data-test-id="pdp-product-name">Amul Milk 500ml</h1>
  <div data-test-id="pdp-product-price">₹27</div>
  <div data-test-id="pdp-product-mrp">₹30</div>
  <div data-test-id="pdp-eta">8 mins</div>
  <div data-test-id="pdp-store-name">Zepto Indiranagar</div>
  <div data-test-id="pdp-product-image"><img src="https://cdn.zeptonow.com/milk.jpg"></div>
  <div data-test-id="pdp-product-quantity">500 ml</div>
  <div data-test-id="pdp-variant">500 ml</div>
  <button data-test-id="pdp-add-to-cart">Add</button>
</body>
</html>
```

```html
<!-- backend/tests/fixtures/zepto_product_out_of_stock.html -->
<!DOCTYPE html>
<html>
<body>
  <h1 data-test-id="pdp-product-name">Amul Milk 500ml</h1>
  <div data-test-id="pdp-sold-out">Sold out</div>
</body>
</html>
```

```python
# backend/app/infrastructure/providers/zepto/__init__.py
```

```python
# backend/app/infrastructure/providers/zepto/selectors.py
ZEPTO_SELECTORS = {
    "location_trigger": "[data-test-id='select-location']",
    "location_input": "[data-test-id='location-search-input']",
    "location_confirm": "[data-test-id='location-confirm']",
    "search_result_card": "[data-test-id='plp-product-card'] a",
    "product_name": "[data-test-id='pdp-product-name']",
    "price": "[data-test-id='pdp-product-price']",
    "mrp": "[data-test-id='pdp-product-mrp']",
    "eta": "[data-test-id='pdp-eta']",
    "store": "[data-test-id='pdp-store-name']",
    "image": "[data-test-id='pdp-product-image'] img",
    "quantity": "[data-test-id='pdp-product-quantity']",
    "variants": "[data-test-id='pdp-variant']",
    "out_of_stock_badge": "[data-test-id='pdp-sold-out']",
    "low_stock_badge": "[data-test-id='pdp-low-stock']",
}
```

```python
# backend/app/infrastructure/providers/zepto/provider.py
import re
from datetime import datetime, timezone

from playwright.async_api import Browser, Page, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from tenacity import retry, stop_after_attempt, wait_exponential

from app.domain.entities import LocationContext, ProviderProductResult
from app.domain.enums import Availability
from app.domain.ports.provider import BaseRetailProvider
from app.infrastructure.providers.zepto.selectors import ZEPTO_SELECTORS

BASE_URL = "https://www.zeptonow.com"


class ZeptoProvider(BaseRetailProvider):
    slug = "zepto"

    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None

    async def initialize(self, location: LocationContext) -> None:
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
        page = await self._browser.new_page()
        try:
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
            try:
                await page.click(ZEPTO_SELECTORS["location_trigger"], timeout=5000)
                await page.fill(ZEPTO_SELECTORS["location_input"], location.pincode)
                await page.click(ZEPTO_SELECTORS["location_confirm"], timeout=5000)
            except PlaywrightTimeoutError:
                pass
        finally:
            await page.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def search_product(self, keyword: str) -> list[ProviderProductResult]:
        assert self._browser is not None, "call initialize() first"
        page = await self._browser.new_page()
        try:
            await page.goto(f"{BASE_URL}/search?q={keyword}", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_selector(ZEPTO_SELECTORS["search_result_card"], timeout=10000)
            cards = await page.query_selector_all(ZEPTO_SELECTORS["search_result_card"])
            urls = [await card.get_attribute("href") for card in cards]
            return [await self.get_product(f"{BASE_URL}{url}") for url in urls if url]
        finally:
            await page.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def get_product(self, product_url: str) -> ProviderProductResult:
        assert self._browser is not None, "call initialize() first"
        page = await self._browser.new_page()
        try:
            await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
            name_el = await page.query_selector(ZEPTO_SELECTORS["product_name"])
            product_name = (await name_el.inner_text()).strip() if name_el else ""
            price, mrp, discount_pct = await self.extract_price(page)
            return ProviderProductResult(
                retailer_slug=self.slug,
                keyword=product_name,
                product_name=product_name,
                availability=await self.check_availability_from_page(page),
                price=price,
                mrp=mrp,
                discount_pct=discount_pct,
                eta_minutes=await self.extract_eta(page),
                store_name=await self.extract_store(page),
                image_url=await self.extract_image(page),
                quantity_label=await self.extract_quantity(page),
                variants=await self.extract_variants(page),
                product_url=product_url,
                scraped_at=datetime.now(timezone.utc),
            )
        finally:
            await page.close()

    async def check_availability(self, product_url: str) -> Availability:
        assert self._browser is not None, "call initialize() first"
        page = await self._browser.new_page()
        try:
            await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
            return await self.check_availability_from_page(page)
        finally:
            await page.close()

    async def check_availability_from_page(self, page: Page) -> Availability:
        if await page.query_selector(ZEPTO_SELECTORS["out_of_stock_badge"]):
            return Availability.OUT_OF_STOCK
        if await page.query_selector(ZEPTO_SELECTORS["low_stock_badge"]):
            return Availability.LOW_STOCK
        return Availability.AVAILABLE

    async def extract_price(self, page: Page) -> tuple[float | None, float | None, float | None]:
        price = await self._extract_number(page, ZEPTO_SELECTORS["price"])
        mrp = await self._extract_number(page, ZEPTO_SELECTORS["mrp"])
        discount_pct = round((1 - price / mrp) * 100, 1) if price is not None and mrp else None
        return price, mrp, discount_pct

    async def extract_eta(self, page: Page) -> int | None:
        el = await page.query_selector(ZEPTO_SELECTORS["eta"])
        if not el:
            return None
        match = re.search(r"(\d+)", await el.inner_text())
        return int(match.group(1)) if match else None

    async def extract_store(self, page: Page) -> str | None:
        el = await page.query_selector(ZEPTO_SELECTORS["store"])
        return (await el.inner_text()).strip() if el else None

    async def extract_image(self, page: Page) -> str | None:
        el = await page.query_selector(ZEPTO_SELECTORS["image"])
        return await el.get_attribute("src") if el else None

    async def extract_quantity(self, page: Page) -> str | None:
        el = await page.query_selector(ZEPTO_SELECTORS["quantity"])
        return (await el.inner_text()).strip() if el else None

    async def extract_variants(self, page: Page) -> list[str]:
        elements = await page.query_selector_all(ZEPTO_SELECTORS["variants"])
        return [(await el.inner_text()).strip() for el in elements]

    async def _extract_number(self, page: Page, selector: str) -> float | None:
        el = await page.query_selector(selector)
        if not el:
            return None
        match = re.search(r"[\d,]+\.?\d*", (await el.inner_text()).replace(",", ""))
        return float(match.group(0)) if match else None

    async def health_check(self) -> bool:
        if self._browser is None:
            return False
        try:
            page = await self._browser.new_page()
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=10000)
            await page.close()
            return True
        except PlaywrightTimeoutError:
            return False

    async def close(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
```

Update `backend/app/monitor/main.py`'s registry construction:

```python
    from app.infrastructure.providers.zepto.provider import ZeptoProvider

    provider_registry = InMemoryProviderRegistry({
        "blinkit": BlinkitProvider,
        "zepto": ZeptoProvider,
    })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/unit/providers/test_zepto_provider.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure/providers/zepto backend/tests/fixtures/zepto_product_available.html backend/tests/fixtures/zepto_product_out_of_stock.html backend/app/monitor/main.py backend/tests/unit/providers/test_zepto_provider.py
git commit -m "feat: add Zepto provider"
```

---

### Task 23: Swiggy Instamart provider

**Files:**
- Create: `backend/app/infrastructure/providers/instamart/__init__.py`
- Create: `backend/app/infrastructure/providers/instamart/selectors.py`
- Create: `backend/app/infrastructure/providers/instamart/provider.py`
- Create: `backend/tests/fixtures/instamart_product_available.html`
- Create: `backend/tests/fixtures/instamart_product_out_of_stock.html`
- Modify: `backend/app/monitor/main.py` (register `"instamart": InstamartProvider`)
- Test: `backend/tests/unit/providers/test_instamart_provider.py`

**Interfaces:**
- Produces `InstamartProvider(BaseRetailProvider)` with `slug = "instamart"`, same method shape as `BlinkitProvider` (Task 7), navigating `https://www.swiggy.com/instamart`.
- Consumes: `BaseRetailProvider`, `LocationContext`, `ProviderProductResult`, `Availability` (Tasks 2, 5).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/providers/test_instamart_provider.py
from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from app.domain.enums import Availability
from app.infrastructure.providers.instamart.provider import InstamartProvider

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


@pytest.fixture
async def page():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        pg = await browser.new_page()
        yield pg
        await browser.close()


@pytest.mark.asyncio
async def test_extracts_available_product_fields(page):
    html = (FIXTURES / "instamart_product_available.html").read_text()
    await page.set_content(html)
    provider = InstamartProvider()

    availability = await provider.check_availability_from_page(page)
    price, mrp, discount_pct = await provider.extract_price(page)
    eta_minutes = await provider.extract_eta(page)

    assert availability == Availability.AVAILABLE
    assert price == 28.0
    assert mrp == 31.0
    assert discount_pct == 9.7
    assert eta_minutes == 15


@pytest.mark.asyncio
async def test_extracts_out_of_stock_product(page):
    html = (FIXTURES / "instamart_product_out_of_stock.html").read_text()
    await page.set_content(html)
    provider = InstamartProvider()

    assert await provider.check_availability_from_page(page) == Availability.OUT_OF_STOCK


@pytest.mark.asyncio
async def test_health_check_returns_false_before_initialize():
    provider = InstamartProvider()
    assert await provider.health_check() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/providers/test_instamart_provider.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.infrastructure.providers.instamart'`

- [ ] **Step 3: Write minimal implementation**

```html
<!-- backend/tests/fixtures/instamart_product_available.html -->
<!DOCTYPE html>
<html>
<body>
  <h1 data-testid="item-name">Amul Milk 500ml</h1>
  <div data-testid="item-price">₹28</div>
  <div data-testid="item-mrp">₹31</div>
  <div data-testid="item-eta">15 MINS</div>
  <div data-testid="item-store">Instamart Whitefield</div>
  <div data-testid="item-image"><img src="https://cdn.swiggy.com/milk.jpg"></div>
  <div data-testid="item-quantity">500 ml</div>
  <div data-testid="item-variant">500 ml</div>
  <button data-testid="item-add-to-cart">ADD</button>
</body>
</html>
```

```html
<!-- backend/tests/fixtures/instamart_product_out_of_stock.html -->
<!DOCTYPE html>
<html>
<body>
  <h1 data-testid="item-name">Amul Milk 500ml</h1>
  <div data-testid="item-out-of-stock">Out of stock</div>
</body>
</html>
```

```python
# backend/app/infrastructure/providers/instamart/__init__.py
```

```python
# backend/app/infrastructure/providers/instamart/selectors.py
INSTAMART_SELECTORS = {
    "location_trigger": "[data-testid='select-location']",
    "location_input": "[data-testid='location-search-input']",
    "location_confirm": "[data-testid='location-confirm']",
    "search_result_card": "[data-testid='item-card'] a",
    "product_name": "[data-testid='item-name']",
    "price": "[data-testid='item-price']",
    "mrp": "[data-testid='item-mrp']",
    "eta": "[data-testid='item-eta']",
    "store": "[data-testid='item-store']",
    "image": "[data-testid='item-image'] img",
    "quantity": "[data-testid='item-quantity']",
    "variants": "[data-testid='item-variant']",
    "out_of_stock_badge": "[data-testid='item-out-of-stock']",
    "low_stock_badge": "[data-testid='item-low-stock']",
}
```

```python
# backend/app/infrastructure/providers/instamart/provider.py
import re
from datetime import datetime, timezone

from playwright.async_api import Browser, Page, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from tenacity import retry, stop_after_attempt, wait_exponential

from app.domain.entities import LocationContext, ProviderProductResult
from app.domain.enums import Availability
from app.domain.ports.provider import BaseRetailProvider
from app.infrastructure.providers.instamart.selectors import INSTAMART_SELECTORS

BASE_URL = "https://www.swiggy.com/instamart"


class InstamartProvider(BaseRetailProvider):
    slug = "instamart"

    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None

    async def initialize(self, location: LocationContext) -> None:
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
        page = await self._browser.new_page()
        try:
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
            try:
                await page.click(INSTAMART_SELECTORS["location_trigger"], timeout=5000)
                await page.fill(INSTAMART_SELECTORS["location_input"], location.pincode)
                await page.click(INSTAMART_SELECTORS["location_confirm"], timeout=5000)
            except PlaywrightTimeoutError:
                pass
        finally:
            await page.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def search_product(self, keyword: str) -> list[ProviderProductResult]:
        assert self._browser is not None, "call initialize() first"
        page = await self._browser.new_page()
        try:
            await page.goto(
                f"{BASE_URL}/search?query={keyword}", wait_until="domcontentloaded", timeout=30000
            )
            await page.wait_for_selector(INSTAMART_SELECTORS["search_result_card"], timeout=10000)
            cards = await page.query_selector_all(INSTAMART_SELECTORS["search_result_card"])
            urls = [await card.get_attribute("href") for card in cards]
            return [await self.get_product(f"{BASE_URL}{url}") for url in urls if url]
        finally:
            await page.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def get_product(self, product_url: str) -> ProviderProductResult:
        assert self._browser is not None, "call initialize() first"
        page = await self._browser.new_page()
        try:
            await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
            name_el = await page.query_selector(INSTAMART_SELECTORS["product_name"])
            product_name = (await name_el.inner_text()).strip() if name_el else ""
            price, mrp, discount_pct = await self.extract_price(page)
            return ProviderProductResult(
                retailer_slug=self.slug,
                keyword=product_name,
                product_name=product_name,
                availability=await self.check_availability_from_page(page),
                price=price,
                mrp=mrp,
                discount_pct=discount_pct,
                eta_minutes=await self.extract_eta(page),
                store_name=await self.extract_store(page),
                image_url=await self.extract_image(page),
                quantity_label=await self.extract_quantity(page),
                variants=await self.extract_variants(page),
                product_url=product_url,
                scraped_at=datetime.now(timezone.utc),
            )
        finally:
            await page.close()

    async def check_availability(self, product_url: str) -> Availability:
        assert self._browser is not None, "call initialize() first"
        page = await self._browser.new_page()
        try:
            await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
            return await self.check_availability_from_page(page)
        finally:
            await page.close()

    async def check_availability_from_page(self, page: Page) -> Availability:
        if await page.query_selector(INSTAMART_SELECTORS["out_of_stock_badge"]):
            return Availability.OUT_OF_STOCK
        if await page.query_selector(INSTAMART_SELECTORS["low_stock_badge"]):
            return Availability.LOW_STOCK
        return Availability.AVAILABLE

    async def extract_price(self, page: Page) -> tuple[float | None, float | None, float | None]:
        price = await self._extract_number(page, INSTAMART_SELECTORS["price"])
        mrp = await self._extract_number(page, INSTAMART_SELECTORS["mrp"])
        discount_pct = round((1 - price / mrp) * 100, 1) if price is not None and mrp else None
        return price, mrp, discount_pct

    async def extract_eta(self, page: Page) -> int | None:
        el = await page.query_selector(INSTAMART_SELECTORS["eta"])
        if not el:
            return None
        match = re.search(r"(\d+)", await el.inner_text())
        return int(match.group(1)) if match else None

    async def extract_store(self, page: Page) -> str | None:
        el = await page.query_selector(INSTAMART_SELECTORS["store"])
        return (await el.inner_text()).strip() if el else None

    async def extract_image(self, page: Page) -> str | None:
        el = await page.query_selector(INSTAMART_SELECTORS["image"])
        return await el.get_attribute("src") if el else None

    async def extract_quantity(self, page: Page) -> str | None:
        el = await page.query_selector(INSTAMART_SELECTORS["quantity"])
        return (await el.inner_text()).strip() if el else None

    async def extract_variants(self, page: Page) -> list[str]:
        elements = await page.query_selector_all(INSTAMART_SELECTORS["variants"])
        return [(await el.inner_text()).strip() for el in elements]

    async def _extract_number(self, page: Page, selector: str) -> float | None:
        el = await page.query_selector(selector)
        if not el:
            return None
        match = re.search(r"[\d,]+\.?\d*", (await el.inner_text()).replace(",", ""))
        return float(match.group(0)) if match else None

    async def health_check(self) -> bool:
        if self._browser is None:
            return False
        try:
            page = await self._browser.new_page()
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=10000)
            await page.close()
            return True
        except PlaywrightTimeoutError:
            return False

    async def close(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
```

Update `backend/app/monitor/main.py`'s registry construction:

```python
    from app.infrastructure.providers.instamart.provider import InstamartProvider

    provider_registry = InMemoryProviderRegistry({
        "blinkit": BlinkitProvider,
        "zepto": ZeptoProvider,
        "instamart": InstamartProvider,
    })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/unit/providers/test_instamart_provider.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure/providers/instamart backend/tests/fixtures/instamart_product_available.html backend/tests/fixtures/instamart_product_out_of_stock.html backend/app/monitor/main.py backend/tests/unit/providers/test_instamart_provider.py
git commit -m "feat: add Swiggy Instamart provider"
```

---

### Task 24: BigBasket provider

**Files:**
- Create: `backend/app/infrastructure/providers/bigbasket/__init__.py`
- Create: `backend/app/infrastructure/providers/bigbasket/selectors.py`
- Create: `backend/app/infrastructure/providers/bigbasket/provider.py`
- Create: `backend/tests/fixtures/bigbasket_product_available.html`
- Create: `backend/tests/fixtures/bigbasket_product_out_of_stock.html`
- Modify: `backend/app/monitor/main.py` (register `"bigbasket": BigBasketProvider`)
- Test: `backend/tests/unit/providers/test_bigbasket_provider.py`

**Interfaces:**
- Produces `BigBasketProvider(BaseRetailProvider)` with `slug = "bigbasket"`, same method shape as `BlinkitProvider` (Task 7), navigating `https://www.bigbasket.com`.
- Consumes: `BaseRetailProvider`, `LocationContext`, `ProviderProductResult`, `Availability` (Tasks 2, 5).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/providers/test_bigbasket_provider.py
from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from app.domain.enums import Availability
from app.infrastructure.providers.bigbasket.provider import BigBasketProvider

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


@pytest.fixture
async def page():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        pg = await browser.new_page()
        yield pg
        await browser.close()


@pytest.mark.asyncio
async def test_extracts_available_product_fields(page):
    html = (FIXTURES / "bigbasket_product_available.html").read_text()
    await page.set_content(html)
    provider = BigBasketProvider()

    availability = await provider.check_availability_from_page(page)
    price, mrp, discount_pct = await provider.extract_price(page)
    quantity_label = await provider.extract_quantity(page)

    assert availability == Availability.AVAILABLE
    assert price == 30.0
    assert mrp == 33.0
    assert discount_pct == 9.1
    assert quantity_label == "500 ml"


@pytest.mark.asyncio
async def test_extracts_out_of_stock_product(page):
    html = (FIXTURES / "bigbasket_product_out_of_stock.html").read_text()
    await page.set_content(html)
    provider = BigBasketProvider()

    assert await provider.check_availability_from_page(page) == Availability.OUT_OF_STOCK


@pytest.mark.asyncio
async def test_health_check_returns_false_before_initialize():
    provider = BigBasketProvider()
    assert await provider.health_check() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/providers/test_bigbasket_provider.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.infrastructure.providers.bigbasket'`

- [ ] **Step 3: Write minimal implementation**

```html
<!-- backend/tests/fixtures/bigbasket_product_available.html -->
<!DOCTYPE html>
<html>
<body>
  <h1 class="prod-name" data-qa="product-name">Amul Milk 500ml</h1>
  <div class="discnt-price" data-qa="product-price">₹30</div>
  <div class="mrp-price" data-qa="product-mrp">₹33</div>
  <div data-qa="product-eta">30-45 mins</div>
  <div data-qa="product-store">BigBasket BB Now Koramangala</div>
  <div data-qa="product-image"><img src="https://cdn.bigbasket.com/milk.jpg"></div>
  <div data-qa="product-quantity">500 ml</div>
  <div data-qa="product-variant">500 ml</div>
  <button data-qa="add-to-cart">ADD</button>
</body>
</html>
```

```html
<!-- backend/tests/fixtures/bigbasket_product_out_of_stock.html -->
<!DOCTYPE html>
<html>
<body>
  <h1 class="prod-name" data-qa="product-name">Amul Milk 500ml</h1>
  <div data-qa="product-out-of-stock">Out of Stock</div>
</body>
</html>
```

```python
# backend/app/infrastructure/providers/bigbasket/__init__.py
```

```python
# backend/app/infrastructure/providers/bigbasket/selectors.py
BIGBASKET_SELECTORS = {
    "location_trigger": "[data-qa='select-location']",
    "location_input": "[data-qa='location-search-input']",
    "location_confirm": "[data-qa='location-confirm']",
    "search_result_card": "[data-qa='product-card'] a",
    "product_name": "[data-qa='product-name']",
    "price": "[data-qa='product-price']",
    "mrp": "[data-qa='product-mrp']",
    "eta": "[data-qa='product-eta']",
    "store": "[data-qa='product-store']",
    "image": "[data-qa='product-image'] img",
    "quantity": "[data-qa='product-quantity']",
    "variants": "[data-qa='product-variant']",
    "out_of_stock_badge": "[data-qa='product-out-of-stock']",
    "low_stock_badge": "[data-qa='product-low-stock']",
}
```

```python
# backend/app/infrastructure/providers/bigbasket/provider.py
import re
from datetime import datetime, timezone

from playwright.async_api import Browser, Page, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from tenacity import retry, stop_after_attempt, wait_exponential

from app.domain.entities import LocationContext, ProviderProductResult
from app.domain.enums import Availability
from app.domain.ports.provider import BaseRetailProvider
from app.infrastructure.providers.bigbasket.selectors import BIGBASKET_SELECTORS

BASE_URL = "https://www.bigbasket.com"


class BigBasketProvider(BaseRetailProvider):
    slug = "bigbasket"

    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None

    async def initialize(self, location: LocationContext) -> None:
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
        page = await self._browser.new_page()
        try:
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
            try:
                await page.click(BIGBASKET_SELECTORS["location_trigger"], timeout=5000)
                await page.fill(BIGBASKET_SELECTORS["location_input"], location.pincode)
                await page.click(BIGBASKET_SELECTORS["location_confirm"], timeout=5000)
            except PlaywrightTimeoutError:
                pass
        finally:
            await page.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def search_product(self, keyword: str) -> list[ProviderProductResult]:
        assert self._browser is not None, "call initialize() first"
        page = await self._browser.new_page()
        try:
            await page.goto(
                f"{BASE_URL}/ps/?q={keyword}", wait_until="domcontentloaded", timeout=30000
            )
            await page.wait_for_selector(BIGBASKET_SELECTORS["search_result_card"], timeout=10000)
            cards = await page.query_selector_all(BIGBASKET_SELECTORS["search_result_card"])
            urls = [await card.get_attribute("href") for card in cards]
            return [await self.get_product(f"{BASE_URL}{url}") for url in urls if url]
        finally:
            await page.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def get_product(self, product_url: str) -> ProviderProductResult:
        assert self._browser is not None, "call initialize() first"
        page = await self._browser.new_page()
        try:
            await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
            name_el = await page.query_selector(BIGBASKET_SELECTORS["product_name"])
            product_name = (await name_el.inner_text()).strip() if name_el else ""
            price, mrp, discount_pct = await self.extract_price(page)
            return ProviderProductResult(
                retailer_slug=self.slug,
                keyword=product_name,
                product_name=product_name,
                availability=await self.check_availability_from_page(page),
                price=price,
                mrp=mrp,
                discount_pct=discount_pct,
                eta_minutes=await self.extract_eta(page),
                store_name=await self.extract_store(page),
                image_url=await self.extract_image(page),
                quantity_label=await self.extract_quantity(page),
                variants=await self.extract_variants(page),
                product_url=product_url,
                scraped_at=datetime.now(timezone.utc),
            )
        finally:
            await page.close()

    async def check_availability(self, product_url: str) -> Availability:
        assert self._browser is not None, "call initialize() first"
        page = await self._browser.new_page()
        try:
            await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
            return await self.check_availability_from_page(page)
        finally:
            await page.close()

    async def check_availability_from_page(self, page: Page) -> Availability:
        if await page.query_selector(BIGBASKET_SELECTORS["out_of_stock_badge"]):
            return Availability.OUT_OF_STOCK
        if await page.query_selector(BIGBASKET_SELECTORS["low_stock_badge"]):
            return Availability.LOW_STOCK
        return Availability.AVAILABLE

    async def extract_price(self, page: Page) -> tuple[float | None, float | None, float | None]:
        price = await self._extract_number(page, BIGBASKET_SELECTORS["price"])
        mrp = await self._extract_number(page, BIGBASKET_SELECTORS["mrp"])
        discount_pct = round((1 - price / mrp) * 100, 1) if price is not None and mrp else None
        return price, mrp, discount_pct

    async def extract_eta(self, page: Page) -> int | None:
        el = await page.query_selector(BIGBASKET_SELECTORS["eta"])
        if not el:
            return None
        match = re.search(r"(\d+)", await el.inner_text())
        return int(match.group(1)) if match else None

    async def extract_store(self, page: Page) -> str | None:
        el = await page.query_selector(BIGBASKET_SELECTORS["store"])
        return (await el.inner_text()).strip() if el else None

    async def extract_image(self, page: Page) -> str | None:
        el = await page.query_selector(BIGBASKET_SELECTORS["image"])
        return await el.get_attribute("src") if el else None

    async def extract_quantity(self, page: Page) -> str | None:
        el = await page.query_selector(BIGBASKET_SELECTORS["quantity"])
        return (await el.inner_text()).strip() if el else None

    async def extract_variants(self, page: Page) -> list[str]:
        elements = await page.query_selector_all(BIGBASKET_SELECTORS["variants"])
        return [(await el.inner_text()).strip() for el in elements]

    async def _extract_number(self, page: Page, selector: str) -> float | None:
        el = await page.query_selector(selector)
        if not el:
            return None
        match = re.search(r"[\d,]+\.?\d*", (await el.inner_text()).replace(",", ""))
        return float(match.group(0)) if match else None

    async def health_check(self) -> bool:
        if self._browser is None:
            return False
        try:
            page = await self._browser.new_page()
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=10000)
            await page.close()
            return True
        except PlaywrightTimeoutError:
            return False

    async def close(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
```

Update `backend/app/monitor/main.py`'s registry construction to its final form covering all four retailers:

```python
    from app.infrastructure.providers.bigbasket.provider import BigBasketProvider
    from app.infrastructure.providers.instamart.provider import InstamartProvider
    from app.infrastructure.providers.zepto.provider import ZeptoProvider

    provider_registry = InMemoryProviderRegistry({
        "blinkit": BlinkitProvider,
        "zepto": ZeptoProvider,
        "instamart": InstamartProvider,
        "bigbasket": BigBasketProvider,
    })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/unit/providers/test_bigbasket_provider.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure/providers/bigbasket backend/tests/fixtures/bigbasket_product_available.html backend/tests/fixtures/bigbasket_product_out_of_stock.html backend/app/monitor/main.py backend/tests/unit/providers/test_bigbasket_provider.py
git commit -m "feat: add BigBasket provider, completing all four retailer adapters"
```

---

## Phase 8: Frontend

Frontend tests use Vitest + React Testing Library (`npm run test`), covering pure logic (stores, API client, hooks) and one smoke render test per page — not exhaustive UI coverage (the Global Constraint's 90% target is scoped to the backend `domain`/`application`/`api` layers).

### Task 25: Vite/React/TS/Tailwind/shadcn scaffold, API client, OTP login

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/index.css`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/store/authStore.ts`
- Create: `frontend/src/pages/Login.tsx`
- Test: `frontend/src/store/authStore.test.ts`
- Test: `frontend/src/api/client.test.ts`

**Interfaces:**
- Produces `useAuthStore` (Zustand) in `src/store/authStore.ts`: state `{ accessToken: string | null; refreshToken: string | null; phoneNumber: string | null }`, actions `login(tokens: { accessToken: string; refreshToken: string }, phoneNumber: string): void`, `logout(): void`, persisted to `localStorage` under key `"auth"`.
- Produces `apiClient` (configured `axios` instance) in `src/api/client.ts`, `baseURL` from `import.meta.env.VITE_API_URL`, a request interceptor attaching `Authorization: Bearer <accessToken>` from `useAuthStore.getState()`, and a response interceptor that on a 401 calls `POST /api/v1/auth/refresh` once and retries the original request, logging out (via `useAuthStore.getState().logout()`) if the refresh itself fails.
- Produces `Login` page component at route `/login`: phone-number step → OTP-code step → on success calls `useAuthStore.login()` and navigates to `/`.
- Produces `App.tsx` with `react-router-dom` routes for every page from Tasks 26–31 (`/`, `/products`, `/retailers`, `/history`, `/notifications`, `/logs`, `/settings`) wrapped in a `RequireAuth` guard that redirects to `/login` when `accessToken` is null; routes are added incrementally as each task builds its page (this task wires `/login` and a placeholder `/` that later tasks replace).
- Consumes: backend `/api/v1/auth/otp/request`, `/api/v1/auth/otp/verify`, `/api/v1/auth/refresh` (Task 16).

- [ ] **Step 1: Write the failing tests**

```typescript
// frontend/src/store/authStore.test.ts
import { describe, expect, it, beforeEach } from "vitest";
import { useAuthStore } from "./authStore";

describe("useAuthStore", () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: null, refreshToken: null, phoneNumber: null });
  });

  it("stores tokens and phone number on login", () => {
    useAuthStore.getState().login(
      { accessToken: "access-123", refreshToken: "refresh-456" },
      "+919999999999"
    );

    const state = useAuthStore.getState();
    expect(state.accessToken).toBe("access-123");
    expect(state.refreshToken).toBe("refresh-456");
    expect(state.phoneNumber).toBe("+919999999999");
  });

  it("clears state on logout", () => {
    useAuthStore.getState().login({ accessToken: "a", refreshToken: "b" }, "+919999999999");
    useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.accessToken).toBeNull();
    expect(state.refreshToken).toBeNull();
  });
});
```

```typescript
// frontend/src/api/client.test.ts
import { describe, expect, it, beforeEach } from "vitest";
import { useAuthStore } from "../store/authStore";
import { apiClient } from "./client";

describe("apiClient request interceptor", () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: null, refreshToken: null, phoneNumber: null });
  });

  it("attaches the bearer token from the auth store when present", async () => {
    useAuthStore.getState().login({ accessToken: "access-123", refreshToken: "r" }, "+91999");

    const config = await apiClient.interceptors.request.handlers[0].fulfilled({ headers: {} });

    expect(config.headers.Authorization).toBe("Bearer access-123");
  });

  it("omits the header when no token is present", async () => {
    const config = await apiClient.interceptors.request.handlers[0].fulfilled({ headers: {} });

    expect(config.headers.Authorization).toBeUndefined();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm install && npm run test -- --run`
Expected: FAIL — `src/store/authStore.ts` and `src/api/client.ts` do not exist yet

- [ ] **Step 3: Write minimal implementation**

```json
// frontend/package.json
{
  "name": "inventory-monitor-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "test": "vitest"
  },
  "dependencies": {
    "axios": "^1.7.0",
    "chart.js": "^4.4.0",
    "clsx": "^2.1.0",
    "framer-motion": "^11.11.0",
    "react": "^18.3.0",
    "react-chartjs-2": "^5.2.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.27.0",
    "tailwind-merge": "^2.5.0",
    "zustand": "^5.0.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.6.0",
    "@testing-library/react": "^16.0.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.0",
    "jsdom": "^25.0.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.6.0",
    "vite": "^5.4.0",
    "vitest": "^2.1.0"
  }
}
```

```typescript
// frontend/vite.config.ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
});
```

```typescript
// frontend/vitest.config.ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
  },
});
```

```json
// frontend/tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "resolveJsonModule": true
  },
  "include": ["src"]
}
```

```typescript
// frontend/tailwind.config.ts
import type { Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
} satisfies Config;
```

```javascript
// frontend/postcss.config.js
export default {
  plugins: { tailwindcss: {}, autoprefixer: {} },
};
```

```html
<!-- frontend/index.html -->
<!DOCTYPE html>
<html lang="en" class="dark">
  <head>
    <meta charset="UTF-8" />
    <title>Inventory Monitor</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

```css
/* frontend/src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;
```

```typescript
// frontend/src/main.tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

```typescript
// frontend/src/store/authStore.ts
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface Tokens {
  accessToken: string;
  refreshToken: string;
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  phoneNumber: string | null;
  login: (tokens: Tokens, phoneNumber: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      phoneNumber: null,
      login: (tokens, phoneNumber) =>
        set({ accessToken: tokens.accessToken, refreshToken: tokens.refreshToken, phoneNumber }),
      logout: () => set({ accessToken: null, refreshToken: null, phoneNumber: null }),
    }),
    { name: "auth" }
  )
);
```

```typescript
// frontend/src/api/client.ts
import axios from "axios";
import { useAuthStore } from "../store/authStore";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refreshToken = useAuthStore.getState().refreshToken;
      if (refreshToken) {
        try {
          const { data } = await axios.post(
            `${apiClient.defaults.baseURL}/api/v1/auth/refresh`,
            { refresh_token: refreshToken }
          );
          useAuthStore.getState().login(
            { accessToken: data.access_token, refreshToken: data.refresh_token },
            useAuthStore.getState().phoneNumber ?? ""
          );
          return apiClient(original);
        } catch {
          useAuthStore.getState().logout();
        }
      } else {
        useAuthStore.getState().logout();
      }
    }
    return Promise.reject(error);
  }
);
```

```typescript
// frontend/src/pages/Login.tsx
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../api/client";
import { useAuthStore } from "../store/authStore";

export default function Login() {
  const [phoneNumber, setPhoneNumber] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"phone" | "otp">("phone");
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  async function requestOtp(event: FormEvent) {
    event.preventDefault();
    await apiClient.post("/api/v1/auth/otp/request", { phone_number: phoneNumber });
    setStep("otp");
  }

  async function verifyOtp(event: FormEvent) {
    event.preventDefault();
    const { data } = await apiClient.post("/api/v1/auth/otp/verify", {
      phone_number: phoneNumber,
      code,
    });
    login({ accessToken: data.access_token, refreshToken: data.refresh_token }, phoneNumber);
    navigate("/");
  }

  if (step === "phone") {
    return (
      <form onSubmit={requestOtp} className="flex flex-col gap-4 p-8 max-w-sm mx-auto">
        <input
          value={phoneNumber}
          onChange={(e) => setPhoneNumber(e.target.value)}
          placeholder="+91XXXXXXXXXX"
          className="rounded border px-3 py-2"
        />
        <button type="submit" className="rounded bg-blue-600 px-3 py-2 text-white">
          Send code
        </button>
      </form>
    );
  }

  return (
    <form onSubmit={verifyOtp} className="flex flex-col gap-4 p-8 max-w-sm mx-auto">
      <input
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="6-digit code"
        className="rounded border px-3 py-2"
      />
      <button type="submit" className="rounded bg-blue-600 px-3 py-2 text-white">
        Verify
      </button>
    </form>
  );
}
```

```typescript
// frontend/src/App.tsx
import { Navigate, Route, BrowserRouter, Routes } from "react-router-dom";
import Login from "./pages/Login";
import { useAuthStore } from "./store/authStore";

function RequireAuth({ children }: { children: JSX.Element }) {
  const accessToken = useAuthStore((s) => s.accessToken);
  return accessToken ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <div className="p-8">Dashboard coming in Task 26</div>
            </RequireAuth>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm run test -- --run`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat: add frontend scaffold, auth store, API client, and OTP login page"
```

---

### Task 26: Live-events store, WebSocket hook, Dashboard page

**Files:**
- Modify: `frontend/package.json` (add `@tanstack/react-query`)
- Create: `frontend/src/store/liveEventsStore.ts`
- Create: `frontend/src/hooks/useLiveEvents.ts`
- Create: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/App.tsx` (wrap routes in `QueryClientProvider`; replace the `/` placeholder with `Dashboard`)
- Test: `frontend/src/store/liveEventsStore.test.ts`
- Test: `frontend/src/hooks/useLiveEvents.test.ts`

**Interfaces:**
- Produces `LiveEvent` type (`{ event_id: number; watch_target_id: number; event_type: string; snapshot_id: number; created_at: string }`) and `useLiveEventsStore` (Zustand) in `src/store/liveEventsStore.ts`: state `{ events: LiveEvent[] }`, action `addEvent(event: LiveEvent): void` — prepends and caps the list at 100 entries (oldest dropped), so the feed can't grow unbounded during a long session.
- Produces `useLiveEvents(): void` hook in `src/hooks/useLiveEvents.ts` — opens `WebSocket("${VITE_WS_URL}/ws?token=<accessToken>")` on mount (no-op if not authenticated), parses each message as `LiveEvent` and calls `addEvent`, fires a browser `Notification` (if permission granted) per message, and reconnects with a fixed 3s backoff on close; cleans up the socket on unmount.
- Produces `Dashboard` page consuming `useLiveEvents()` and rendering `useLiveEventsStore`'s feed plus a watch count fetched via `@tanstack/react-query`'s `useQuery` against `GET /api/v1/watches`.
- Consumes: `useAuthStore` (Task 25); backend `GET /ws` (Task 21), `GET /api/v1/watches` (Task 18).

- [ ] **Step 1: Write the failing tests**

```typescript
// frontend/src/store/liveEventsStore.test.ts
import { describe, expect, it, beforeEach } from "vitest";
import { useLiveEventsStore } from "./liveEventsStore";

describe("useLiveEventsStore", () => {
  beforeEach(() => {
    useLiveEventsStore.setState({ events: [] });
  });

  it("prepends new events", () => {
    const store = useLiveEventsStore.getState();
    store.addEvent({ event_id: 1, watch_target_id: 1, event_type: "stock_available", snapshot_id: 1, created_at: "t1" });
    store.addEvent({ event_id: 2, watch_target_id: 1, event_type: "price_changed", snapshot_id: 2, created_at: "t2" });

    expect(useLiveEventsStore.getState().events.map((e) => e.event_id)).toEqual([2, 1]);
  });

  it("caps the feed at 100 events", () => {
    const store = useLiveEventsStore.getState();
    for (let i = 0; i < 105; i++) {
      store.addEvent({ event_id: i, watch_target_id: 1, event_type: "stock_available", snapshot_id: i, created_at: "t" });
    }

    expect(useLiveEventsStore.getState().events).toHaveLength(100);
    expect(useLiveEventsStore.getState().events[0].event_id).toBe(104);
  });
});
```

```typescript
// frontend/src/hooks/useLiveEvents.test.ts
import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "../store/authStore";
import { useLiveEventsStore } from "../store/liveEventsStore";
import { useLiveEvents } from "./useLiveEvents";

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  url: string;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  close() {}
}

describe("useLiveEvents", () => {
  beforeEach(() => {
    FakeWebSocket.instances = [];
    // @ts-expect-error test double
    global.WebSocket = FakeWebSocket;
    useAuthStore.setState({ accessToken: "access-123", refreshToken: "r", phoneNumber: "+91" });
    useLiveEventsStore.setState({ events: [] });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("connects with the access token in the query string", () => {
    renderHook(() => useLiveEvents());

    expect(FakeWebSocket.instances).toHaveLength(1);
    expect(FakeWebSocket.instances[0].url).toContain("token=access-123");
  });

  it("adds an incoming message to the live events store", () => {
    renderHook(() => useLiveEvents());
    const socket = FakeWebSocket.instances[0];

    socket.onmessage?.({
      data: JSON.stringify({ event_id: 1, watch_target_id: 1, event_type: "stock_available", snapshot_id: 1, created_at: "t1" }),
    });

    expect(useLiveEventsStore.getState().events).toHaveLength(1);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm run test -- --run`
Expected: FAIL — `src/store/liveEventsStore.ts` and `src/hooks/useLiveEvents.ts` do not exist yet

- [ ] **Step 3: Write minimal implementation**

Add `"@tanstack/react-query": "^5.59.0"` to `dependencies` in `frontend/package.json`.

```typescript
// frontend/src/store/liveEventsStore.ts
import { create } from "zustand";

export interface LiveEvent {
  event_id: number;
  watch_target_id: number;
  event_type: string;
  snapshot_id: number;
  created_at: string;
}

interface LiveEventsState {
  events: LiveEvent[];
  addEvent: (event: LiveEvent) => void;
}

const MAX_EVENTS = 100;

export const useLiveEventsStore = create<LiveEventsState>((set) => ({
  events: [],
  addEvent: (event) =>
    set((state) => ({ events: [event, ...state.events].slice(0, MAX_EVENTS) })),
}));
```

```typescript
// frontend/src/hooks/useLiveEvents.ts
import { useEffect } from "react";
import { useAuthStore } from "../store/authStore";
import { LiveEvent, useLiveEventsStore } from "../store/liveEventsStore";

const RECONNECT_DELAY_MS = 3000;

export function useLiveEvents(): void {
  const accessToken = useAuthStore((s) => s.accessToken);
  const addEvent = useLiveEventsStore((s) => s.addEvent);

  useEffect(() => {
    if (!accessToken) return;

    let socket: WebSocket;
    let reconnectTimer: ReturnType<typeof setTimeout>;
    let cancelled = false;

    function connect() {
      const wsUrl = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";
      socket = new WebSocket(`${wsUrl}/ws?token=${accessToken}`);

      socket.onmessage = (event) => {
        const payload: LiveEvent = JSON.parse(event.data);
        addEvent(payload);
        if (typeof Notification !== "undefined" && Notification.permission === "granted") {
          new Notification(`Update: ${payload.event_type}`);
        }
      };

      socket.onclose = () => {
        if (!cancelled) {
          reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };
    }

    connect();

    return () => {
      cancelled = true;
      clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [accessToken, addEvent]);
}
```

```typescript
// frontend/src/pages/Dashboard.tsx
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import { useLiveEvents } from "../hooks/useLiveEvents";
import { useLiveEventsStore } from "../store/liveEventsStore";

export default function Dashboard() {
  useLiveEvents();
  const events = useLiveEventsStore((s) => s.events);
  const { data: watches } = useQuery({
    queryKey: ["watches"],
    queryFn: async () => (await apiClient.get("/api/v1/watches")).data,
  });

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      <div className="rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur">
        Active watches: {watches?.length ?? "…"}
      </div>
      <div className="space-y-2">
        <h2 className="text-lg font-medium">Live feed</h2>
        {events.map((event) => (
          <div key={event.event_id} className="rounded border border-white/10 p-2 text-sm">
            {event.event_type} — watch target {event.watch_target_id}
          </div>
        ))}
      </div>
    </div>
  );
}
```

Replace `frontend/src/App.tsx` with:

```typescript
// frontend/src/App.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Navigate, Route, BrowserRouter, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import { useAuthStore } from "./store/authStore";

const queryClient = new QueryClient();

function RequireAuth({ children }: { children: JSX.Element }) {
  const accessToken = useAuthStore((s) => s.accessToken);
  return accessToken ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <RequireAuth>
                <Dashboard />
              </RequireAuth>
            }
          />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm install && npm run test -- --run`
Expected: PASS (6 new tests)

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat: add live events store, WebSocket hook, and dashboard page"
```

---

### Task 27: Products page (products + per-product watch management)

**Files:**
- Create: `frontend/src/pages/Products.tsx`
- Modify: `frontend/src/App.tsx` (add `/products` route)
- Test: `frontend/src/pages/Products.test.tsx`

**Interfaces:**
- Produces `Products` page: lists the caller's products (`GET /api/v1/products`) each with its watches (`GET /api/v1/watches`, filtered client-side by `product_id` — the API returns all of the caller's watches, not product-scoped, per Task 18); a form to create a product (`POST /api/v1/products`); a per-product form to add a watch (retailer select from the four supported slugs, city, pincode, interval — `POST /api/v1/watches`); delete buttons for both (`DELETE /api/v1/products/{id}`, `DELETE /api/v1/watches/{id}`), invalidating the relevant `react-query` cache key on success.
- Consumes: `apiClient` (Task 25); `GET/POST/DELETE /api/v1/products`, `GET/POST/DELETE /api/v1/watches` (Task 18).

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/pages/Products.test.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import Products from "./Products";

vi.mock("../api/client", () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}));

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("Products page", () => {
  afterEach(() => vi.resetAllMocks());

  it("renders products returned by the API", async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === "/api/v1/products") {
        return Promise.resolve({ data: [{ id: 1, name: "Milk", keyword: "amul milk 500ml", canonical_image_url: null }] });
      }
      return Promise.resolve({ data: [] });
    });

    renderWithClient(<Products />);

    await waitFor(() => expect(screen.getByText("Milk")).toBeInTheDocument());
  });

  it("submits a new product via the create form", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: 1, name: "Bread", keyword: "brown bread", canonical_image_url: null } });

    renderWithClient(<Products />);

    fireEvent.change(await screen.findByPlaceholderText("Name"), { target: { value: "Bread" } });
    fireEvent.change(screen.getByPlaceholderText("Search keyword"), { target: { value: "brown bread" } });
    fireEvent.click(screen.getByText("Add product"));

    await waitFor(() =>
      expect(apiClient.post).toHaveBeenCalledWith("/api/v1/products", {
        name: "Bread",
        keyword: "brown bread",
        canonical_image_url: null,
      })
    );
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- --run`
Expected: FAIL — `src/pages/Products.tsx` does not exist yet

- [ ] **Step 3: Write minimal implementation**

```typescript
// frontend/src/pages/Products.tsx
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { apiClient } from "../api/client";

const RETAILERS = ["blinkit", "zepto", "instamart", "bigbasket"];

interface Product {
  id: number;
  name: string;
  keyword: string;
  canonical_image_url: string | null;
}

interface Watch {
  id: number;
  product_id: number;
  watch_target_id: number;
  interval_seconds: number;
  is_active: boolean;
}

export default function Products() {
  const queryClient = useQueryClient();
  const { data: products = [] } = useQuery<Product[]>({
    queryKey: ["products"],
    queryFn: async () => (await apiClient.get("/api/v1/products")).data,
  });
  const { data: watches = [] } = useQuery<Watch[]>({
    queryKey: ["watches"],
    queryFn: async () => (await apiClient.get("/api/v1/watches")).data,
  });

  const [name, setName] = useState("");
  const [keyword, setKeyword] = useState("");

  async function createProduct(event: FormEvent) {
    event.preventDefault();
    await apiClient.post("/api/v1/products", { name, keyword, canonical_image_url: null });
    setName("");
    setKeyword("");
    queryClient.invalidateQueries({ queryKey: ["products"] });
  }

  async function deleteProduct(id: number) {
    await apiClient.delete(`/api/v1/products/${id}`);
    queryClient.invalidateQueries({ queryKey: ["products"] });
  }

  async function createWatch(productId: number, form: HTMLFormElement) {
    const data = new FormData(form);
    await apiClient.post("/api/v1/watches", {
      product_id: productId,
      retailer_slug: data.get("retailer_slug"),
      city: data.get("city"),
      pincode: data.get("pincode"),
      interval_seconds: Number(data.get("interval_seconds") ?? 300),
    });
    queryClient.invalidateQueries({ queryKey: ["watches"] });
  }

  async function deleteWatch(id: number) {
    await apiClient.delete(`/api/v1/watches/${id}`);
    queryClient.invalidateQueries({ queryKey: ["watches"] });
  }

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-semibold">Products</h1>

      <form onSubmit={createProduct} className="flex gap-2">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" className="rounded border px-2 py-1" />
        <input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="Search keyword" className="rounded border px-2 py-1" />
        <button type="submit" className="rounded bg-blue-600 px-3 py-1 text-white">Add product</button>
      </form>

      {products.map((product) => (
        <div key={product.id} className="rounded-lg border border-white/10 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">{product.name}</div>
              <div className="text-sm text-white/60">{product.keyword}</div>
            </div>
            <button onClick={() => deleteProduct(product.id)} className="text-red-400">Delete</button>
          </div>

          <ul className="text-sm space-y-1">
            {watches.filter((w) => w.product_id === product.id).map((watch) => (
              <li key={watch.id} className="flex items-center justify-between">
                <span>watch #{watch.id} → target {watch.watch_target_id}</span>
                <button onClick={() => deleteWatch(watch.id)} className="text-red-400">Remove</button>
              </li>
            ))}
          </ul>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              createWatch(product.id, e.currentTarget);
              e.currentTarget.reset();
            }}
            className="flex flex-wrap gap-2"
          >
            <select name="retailer_slug" className="rounded border px-2 py-1">
              {RETAILERS.map((slug) => (
                <option key={slug} value={slug}>{slug}</option>
              ))}
            </select>
            <input name="city" placeholder="City" className="rounded border px-2 py-1" />
            <input name="pincode" placeholder="Pincode" className="rounded border px-2 py-1" />
            <input name="interval_seconds" placeholder="Interval (s)" defaultValue={300} className="rounded border px-2 py-1 w-28" />
            <button type="submit" className="rounded bg-emerald-600 px-3 py-1 text-white">Add watch</button>
          </form>
        </div>
      ))}
    </div>
  );
}
```

Add to `frontend/src/App.tsx` (import `Products` and add a route):

```typescript
          <Route
            path="/products"
            element={
              <RequireAuth>
                <Products />
              </RequireAuth>
            }
          />
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- --run`
Expected: PASS (2 new tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Products.tsx frontend/src/pages/Products.test.tsx frontend/src/App.tsx
git commit -m "feat: add products page with per-product watch management"
```

---

### Task 28: Retailers page

**Files:**
- Create: `frontend/src/pages/Retailers.tsx`
- Modify: `frontend/src/App.tsx` (add `/retailers` route)
- Test: `frontend/src/pages/Retailers.test.tsx`

**Interfaces:**
- Produces `Retailers` page: fetches `GET /api/v1/retailers` and renders one card per retailer with `name` and an `is_active` badge ("active"/"inactive").
- Consumes: `apiClient` (Task 25); `GET /api/v1/retailers` (Task 17).

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/pages/Retailers.test.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import Retailers from "./Retailers";

vi.mock("../api/client", () => ({ apiClient: { get: vi.fn() } }));

describe("Retailers page", () => {
  it("renders each retailer with its active status", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: [
        { slug: "blinkit", name: "Blinkit", is_active: true },
        { slug: "zepto", name: "Zepto", is_active: false },
      ],
    });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <Retailers />
      </QueryClientProvider>
    );

    await waitFor(() => expect(screen.getByText("Blinkit")).toBeInTheDocument());
    expect(screen.getByText("Zepto")).toBeInTheDocument();
    expect(screen.getAllByText(/active/i)).toHaveLength(2);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- --run`
Expected: FAIL — `src/pages/Retailers.tsx` does not exist yet

- [ ] **Step 3: Write minimal implementation**

```typescript
// frontend/src/pages/Retailers.tsx
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";

interface Retailer {
  slug: string;
  name: string;
  is_active: boolean;
}

export default function Retailers() {
  const { data: retailers = [] } = useQuery<Retailer[]>({
    queryKey: ["retailers"],
    queryFn: async () => (await apiClient.get("/api/v1/retailers")).data,
  });

  return (
    <div className="p-8 space-y-4">
      <h1 className="text-2xl font-semibold">Retailers</h1>
      <div className="grid grid-cols-2 gap-4">
        {retailers.map((retailer) => (
          <div key={retailer.slug} className="rounded-lg border border-white/10 p-4 flex items-center justify-between">
            <span>{retailer.name}</span>
            <span className={retailer.is_active ? "text-emerald-400" : "text-red-400"}>
              {retailer.is_active ? "active" : "inactive"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

Add to `frontend/src/App.tsx`:

```typescript
          <Route
            path="/retailers"
            element={
              <RequireAuth>
                <Retailers />
              </RequireAuth>
            }
          />
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- --run`
Expected: PASS (1 new test)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Retailers.tsx frontend/src/pages/Retailers.test.tsx frontend/src/App.tsx
git commit -m "feat: add retailers page"
```

---

### Task 29: History page with price chart

**Files:**
- Modify: `frontend/package.json` (add `chart.js`, `react-chartjs-2` — already listed in Task 25's `dependencies`, so this task just consumes them)
- Create: `frontend/src/pages/History.tsx`
- Modify: `frontend/src/App.tsx` (add `/history` route)
- Test: `frontend/src/pages/History.test.tsx`

**Interfaces:**
- Produces `History` page: a `<select>` of the caller's watches (`GET /api/v1/watches`), and on selection fetches `GET /api/v1/analytics/price-history?watch_id=<id>` (rendered as a Chart.js `Line` chart via `react-chartjs-2`) and `GET /api/v1/history?watch_id=<id>` (rendered as an event table).
- Consumes: `apiClient` (Task 25); `GET /api/v1/watches` (Task 18); `GET /api/v1/analytics/price-history`, `GET /api/v1/history` (Tasks 20, 17).

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/pages/History.test.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import History from "./History";

vi.mock("../api/client", () => ({ apiClient: { get: vi.fn() } }));
vi.mock("react-chartjs-2", () => ({ Line: () => <div data-testid="price-chart" /> }));

describe("History page", () => {
  it("fetches history and price data once a watch is selected", async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === "/api/v1/watches") {
        return Promise.resolve({ data: [{ id: 5, product_id: 1, watch_target_id: 7, interval_seconds: 300, is_active: true }] });
      }
      if (url.startsWith("/api/v1/analytics/price-history")) {
        return Promise.resolve({ data: [{ timestamp: "t1", price: 29 }] });
      }
      if (url.startsWith("/api/v1/history")) {
        return Promise.resolve({ data: [{ event_id: 1, event_type: "stock_available", created_at: "t1", snapshot: { availability: "available", price: 29, mrp: 32, discount_pct: 9.4, eta_minutes: 10, store_name: null, image_url: null, quantity_label: null, variants: [], product_url: null } }] });
      }
      return Promise.resolve({ data: [] });
    });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <History />
      </QueryClientProvider>
    );

    fireEvent.change(await screen.findByRole("combobox"), { target: { value: "5" } });

    await waitFor(() => expect(screen.getByTestId("price-chart")).toBeInTheDocument());
    expect(screen.getByText("stock_available")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- --run`
Expected: FAIL — `src/pages/History.tsx` does not exist yet

- [ ] **Step 3: Write minimal implementation**

```typescript
// frontend/src/pages/History.tsx
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Line } from "react-chartjs-2";
import {
  CategoryScale,
  Chart as ChartJS,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";
import { apiClient } from "../api/client";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip);

interface Watch {
  id: number;
  product_id: number;
  watch_target_id: number;
  interval_seconds: number;
  is_active: boolean;
}

interface PricePoint {
  timestamp: string;
  price: number | null;
}

interface HistoryEntry {
  event_id: number;
  event_type: string;
  created_at: string;
}

export default function History() {
  const [watchId, setWatchId] = useState<number | null>(null);
  const { data: watches = [] } = useQuery<Watch[]>({
    queryKey: ["watches"],
    queryFn: async () => (await apiClient.get("/api/v1/watches")).data,
  });
  const { data: pricePoints = [] } = useQuery<PricePoint[]>({
    queryKey: ["price-history", watchId],
    queryFn: async () => (await apiClient.get(`/api/v1/analytics/price-history?watch_id=${watchId}`)).data,
    enabled: watchId !== null,
  });
  const { data: entries = [] } = useQuery<HistoryEntry[]>({
    queryKey: ["history", watchId],
    queryFn: async () => (await apiClient.get(`/api/v1/history?watch_id=${watchId}`)).data,
    enabled: watchId !== null,
  });

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-semibold">History</h1>
      <select onChange={(e) => setWatchId(Number(e.target.value))} className="rounded border px-2 py-1" defaultValue="">
        <option value="" disabled>Select a watch</option>
        {watches.map((watch) => (
          <option key={watch.id} value={watch.id}>watch #{watch.id}</option>
        ))}
      </select>

      {watchId !== null && (
        <>
          <Line
            data={{
              labels: pricePoints.map((p) => p.timestamp),
              datasets: [{ label: "Price", data: pricePoints.map((p) => p.price ?? 0) }],
            }}
          />
          <table className="w-full text-sm">
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.event_id}>
                  <td>{entry.created_at}</td>
                  <td>{entry.event_type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
```

Add to `frontend/src/App.tsx`:

```typescript
          <Route
            path="/history"
            element={
              <RequireAuth>
                <History />
              </RequireAuth>
            }
          />
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- --run`
Expected: PASS (1 new test)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/History.tsx frontend/src/pages/History.test.tsx frontend/src/App.tsx
git commit -m "feat: add history page with price chart"
```

---

### Task 30: Notifications page

**Files:**
- Create: `frontend/src/pages/Notifications.tsx`
- Modify: `frontend/src/App.tsx` (add `/notifications` route)
- Test: `frontend/src/pages/Notifications.test.tsx`

**Interfaces:**
- Produces `Notifications` page: lists channels (`GET /api/v1/notifications/channels`) with a "Verify" button per unverified channel (`POST /api/v1/notifications/channels/{id}/verify`) and a delete button (`DELETE /api/v1/notifications/channels/{id}`); a form to add a channel (type select: telegram/discord/email, a single free-text config field parsed as JSON); and the notification log (`GET /api/v1/notifications/log`).
- Consumes: `apiClient` (Task 25); notifications endpoints (Task 19).

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/pages/Notifications.test.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import Notifications from "./Notifications";

vi.mock("../api/client", () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}));

describe("Notifications page", () => {
  it("verifies an unverified channel", async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === "/api/v1/notifications/channels") {
        return Promise.resolve({ data: [{ id: 1, type: "telegram", config: { chat_id: "123" }, is_verified: false }] });
      }
      return Promise.resolve({ data: [] });
    });
    vi.mocked(apiClient.post).mockResolvedValue({ data: { status: "verified" } });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <Notifications />
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByText("Verify"));

    await waitFor(() =>
      expect(apiClient.post).toHaveBeenCalledWith("/api/v1/notifications/channels/1/verify")
    );
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- --run`
Expected: FAIL — `src/pages/Notifications.tsx` does not exist yet

- [ ] **Step 3: Write minimal implementation**

```typescript
// frontend/src/pages/Notifications.tsx
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { apiClient } from "../api/client";

interface Channel {
  id: number;
  type: string;
  config: Record<string, unknown>;
  is_verified: boolean;
}

interface LogEntry {
  id: number;
  detection_event_id: number;
  channel_id: number;
  status: string;
  sent_at: string;
}

export default function Notifications() {
  const queryClient = useQueryClient();
  const { data: channels = [] } = useQuery<Channel[]>({
    queryKey: ["channels"],
    queryFn: async () => (await apiClient.get("/api/v1/notifications/channels")).data,
  });
  const { data: log = [] } = useQuery<LogEntry[]>({
    queryKey: ["notification-log"],
    queryFn: async () => (await apiClient.get("/api/v1/notifications/log")).data,
  });
  const [type, setType] = useState("telegram");
  const [config, setConfig] = useState("{}");

  async function addChannel(event: FormEvent) {
    event.preventDefault();
    await apiClient.post("/api/v1/notifications/channels", { type, config: JSON.parse(config) });
    queryClient.invalidateQueries({ queryKey: ["channels"] });
  }

  async function verify(id: number) {
    await apiClient.post(`/api/v1/notifications/channels/${id}/verify`);
    queryClient.invalidateQueries({ queryKey: ["channels"] });
  }

  async function remove(id: number) {
    await apiClient.delete(`/api/v1/notifications/channels/${id}`);
    queryClient.invalidateQueries({ queryKey: ["channels"] });
  }

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-semibold">Notifications</h1>

      <form onSubmit={addChannel} className="flex gap-2">
        <select value={type} onChange={(e) => setType(e.target.value)} className="rounded border px-2 py-1">
          <option value="telegram">telegram</option>
          <option value="discord">discord</option>
          <option value="email">email</option>
        </select>
        <input value={config} onChange={(e) => setConfig(e.target.value)} className="rounded border px-2 py-1 flex-1" />
        <button type="submit" className="rounded bg-blue-600 px-3 py-1 text-white">Add channel</button>
      </form>

      <ul className="space-y-2">
        {channels.map((channel) => (
          <li key={channel.id} className="flex items-center justify-between rounded border border-white/10 p-2">
            <span>{channel.type} — {channel.is_verified ? "verified" : "unverified"}</span>
            <div className="flex gap-2">
              {!channel.is_verified && (
                <button onClick={() => verify(channel.id)} className="text-emerald-400">Verify</button>
              )}
              <button onClick={() => remove(channel.id)} className="text-red-400">Delete</button>
            </div>
          </li>
        ))}
      </ul>

      <h2 className="text-lg font-medium">Recent notifications</h2>
      <ul className="text-sm space-y-1">
        {log.map((entry) => (
          <li key={entry.id}>{entry.sent_at} — channel {entry.channel_id} — {entry.status}</li>
        ))}
      </ul>
    </div>
  );
}
```

Add to `frontend/src/App.tsx`:

```typescript
          <Route
            path="/notifications"
            element={
              <RequireAuth>
                <Notifications />
              </RequireAuth>
            }
          />
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- --run`
Expected: PASS (1 new test)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Notifications.tsx frontend/src/pages/Notifications.test.tsx frontend/src/App.tsx
git commit -m "feat: add notifications page with channel management and log"
```

---

### Task 31: Logs and Settings pages

**Files:**
- Create: `frontend/src/pages/Logs.tsx`
- Create: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/App.tsx` (add `/logs` and `/settings` routes, and a top-level nav linking every page — this is the last frontend task, so it also finalizes navigation)
- Test: `frontend/src/pages/Logs.test.tsx`
- Test: `frontend/src/pages/Settings.test.tsx`

**Interfaces:**
- Produces `Logs` page: fetches `GET /api/v1/logs` and renders each entry's level, message, and timestamp.
- Produces `Settings` page: fetches `GET /api/v1/settings` and renders a key/value editor form that calls `PUT /api/v1/settings` with `{key, value}` on submit.
- Produces a `Nav` component rendered once in `App.tsx` (outside the route switch) linking to all seven pages, visible only when authenticated.
- Consumes: `apiClient` (Task 25); `GET /api/v1/logs` (Task 19); `GET/PUT /api/v1/settings` (Task 19).

- [ ] **Step 1: Write the failing tests**

```typescript
// frontend/src/pages/Logs.test.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import Logs from "./Logs";

vi.mock("../api/client", () => ({ apiClient: { get: vi.fn() } }));

describe("Logs page", () => {
  it("renders recent log entries", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: [{ id: 1, level: "error", message: "provider crashed", context: {}, created_at: "t1" }],
    });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <Logs />
      </QueryClientProvider>
    );

    await waitFor(() => expect(screen.getByText("provider crashed")).toBeInTheDocument());
  });
});
```

```typescript
// frontend/src/pages/Settings.test.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import Settings from "./Settings";

vi.mock("../api/client", () => ({ apiClient: { get: vi.fn(), put: vi.fn() } }));

describe("Settings page", () => {
  it("submits an updated setting", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { timezone: "Asia/Kolkata" } });
    vi.mocked(apiClient.put).mockResolvedValue({ data: { timezone: "UTC" } });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <Settings />
      </QueryClientProvider>
    );

    fireEvent.change(await screen.findByPlaceholderText("Key"), { target: { value: "timezone" } });
    fireEvent.change(screen.getByPlaceholderText("Value"), { target: { value: "UTC" } });
    fireEvent.click(screen.getByText("Save"));

    await waitFor(() =>
      expect(apiClient.put).toHaveBeenCalledWith("/api/v1/settings", { key: "timezone", value: "UTC" })
    );
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm run test -- --run`
Expected: FAIL — `src/pages/Logs.tsx` and `src/pages/Settings.tsx` do not exist yet

- [ ] **Step 3: Write minimal implementation**

```typescript
// frontend/src/pages/Logs.tsx
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";

interface SystemLog {
  id: number;
  level: string;
  message: string;
  created_at: string;
}

export default function Logs() {
  const { data: logs = [] } = useQuery<SystemLog[]>({
    queryKey: ["logs"],
    queryFn: async () => (await apiClient.get("/api/v1/logs")).data,
  });

  return (
    <div className="p-8 space-y-2">
      <h1 className="text-2xl font-semibold">Logs</h1>
      {logs.map((log) => (
        <div key={log.id} className="rounded border border-white/10 p-2 text-sm">
          <span className="uppercase text-white/50">{log.level}</span> — {log.message} — {log.created_at}
        </div>
      ))}
    </div>
  );
}
```

```typescript
// frontend/src/pages/Settings.tsx
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { apiClient } from "../api/client";

export default function Settings() {
  const queryClient = useQueryClient();
  const { data: settings = {} } = useQuery<Record<string, unknown>>({
    queryKey: ["settings"],
    queryFn: async () => (await apiClient.get("/api/v1/settings")).data,
  });
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");

  async function save(event: FormEvent) {
    event.preventDefault();
    await apiClient.put("/api/v1/settings", { key, value });
    queryClient.invalidateQueries({ queryKey: ["settings"] });
  }

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-semibold">Settings</h1>
      <ul className="text-sm space-y-1">
        {Object.entries(settings).map(([k, v]) => (
          <li key={k}>{k}: {String(v)}</li>
        ))}
      </ul>
      <form onSubmit={save} className="flex gap-2">
        <input value={key} onChange={(e) => setKey(e.target.value)} placeholder="Key" className="rounded border px-2 py-1" />
        <input value={value} onChange={(e) => setValue(e.target.value)} placeholder="Value" className="rounded border px-2 py-1" />
        <button type="submit" className="rounded bg-blue-600 px-3 py-1 text-white">Save</button>
      </form>
    </div>
  );
}
```

Replace `frontend/src/App.tsx` with its final form (adds `Nav`, `/logs`, `/settings`):

```typescript
// frontend/src/App.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Link, Navigate, Route, BrowserRouter, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import History from "./pages/History";
import Login from "./pages/Login";
import Logs from "./pages/Logs";
import Notifications from "./pages/Notifications";
import Products from "./pages/Products";
import Retailers from "./pages/Retailers";
import Settings from "./pages/Settings";
import { useAuthStore } from "./store/authStore";

const queryClient = new QueryClient();

function RequireAuth({ children }: { children: JSX.Element }) {
  const accessToken = useAuthStore((s) => s.accessToken);
  return accessToken ? children : <Navigate to="/login" replace />;
}

function Nav() {
  const accessToken = useAuthStore((s) => s.accessToken);
  if (!accessToken) return null;
  const links: [string, string][] = [
    ["/", "Dashboard"],
    ["/products", "Products"],
    ["/retailers", "Retailers"],
    ["/history", "History"],
    ["/notifications", "Notifications"],
    ["/logs", "Logs"],
    ["/settings", "Settings"],
  ];
  return (
    <nav className="flex gap-4 border-b border-white/10 p-4 text-sm">
      {links.map(([to, label]) => (
        <Link key={to} to={to}>{label}</Link>
      ))}
    </nav>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Nav />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<RequireAuth><Dashboard /></RequireAuth>} />
          <Route path="/products" element={<RequireAuth><Products /></RequireAuth>} />
          <Route path="/retailers" element={<RequireAuth><Retailers /></RequireAuth>} />
          <Route path="/history" element={<RequireAuth><History /></RequireAuth>} />
          <Route path="/notifications" element={<RequireAuth><Notifications /></RequireAuth>} />
          <Route path="/logs" element={<RequireAuth><Logs /></RequireAuth>} />
          <Route path="/settings" element={<RequireAuth><Settings /></RequireAuth>} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm run test -- --run`
Expected: PASS (2 new tests; full suite green)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Logs.tsx frontend/src/pages/Settings.tsx frontend/src/pages/Logs.test.tsx frontend/src/pages/Settings.test.tsx frontend/src/App.tsx
git commit -m "feat: add logs and settings pages, finalize app navigation"
```

---

## Phase 9: Deployment

Deployment tasks aren't Python/TS unit tests — "verify" here means the artifact builds/validates cleanly, checked by the Docker/Compose CLI itself.

### Task 32: Backend and frontend Dockerfiles

**Files:**
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`

**Interfaces:**
- Produces a single backend image (multi-stage, `python:3.13-slim`) reused by all four backend services (`api`, `monitor`, `worker`, `beat` — Task 33 picks the process via each service's `command:`); installs Playwright's Chromium + OS deps via `playwright install --with-deps chromium`; a container-level `HEALTHCHECK` hits `GET /health`.
- Produces a multi-stage frontend image: Node build stage → static files served by `nginx`, with an SPA fallback (`try_files ... /index.html`) so client-side routes (`/products`, `/history`, ...) don't 404 on refresh.

- [ ] **Step 1: Write the Dockerfiles**

```dockerfile
# backend/Dockerfile
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir .
RUN playwright install --with-deps chromium

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# frontend/Dockerfile
FROM node:20-slim AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

```nginx
# frontend/nginx.conf
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 2: Verify both images build**

Run: `docker build -t inventory-monitor-backend backend`
Expected: build completes with exit code 0

Run: `docker build -t inventory-monitor-frontend frontend`
Expected: build completes with exit code 0

- [ ] **Step 3: Commit**

```bash
git add backend/Dockerfile frontend/Dockerfile frontend/nginx.conf
git commit -m "feat: add backend and frontend Dockerfiles"
```

---

### Task 33: docker-compose.yml and .env.example

**Files:**
- Create: `docker/docker-compose.yml`
- Create: `docker/.env.example`

**Interfaces:**
- Produces the full local/self-host stack: `postgres`, `redis` (both with healthchecks), `api`, `monitor`, `worker`, `beat` (all built from `backend/Dockerfile`, differing only by `command:`), and an optional `frontend` service behind a `self-host` Compose profile (skipped when the frontend is deployed to Vercel instead — Task 34 covers that path). `api`/`monitor`/`worker`/`beat` all wait on `postgres`/`redis` via `condition: service_healthy`. `monitor` gets a named volume for the Playwright browser cache so it isn't re-downloaded on every restart.
- Produces `docker/.env.example` documenting every `Settings` field from `app.core.config` (Tasks 1, 13) plus `POSTGRES_PASSWORD`, ready to `cp` to `docker/.env`.

- [ ] **Step 1: Write the compose file and env template**

```yaml
# docker/docker-compose.yml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: inventory_monitor
      POSTGRES_USER: inventory_monitor
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-changeme}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U inventory_monitor"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build:
      context: ../backend
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  monitor:
    build:
      context: ../backend
    env_file: .env
    command: ["python", "-m", "app.monitor.main"]
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - playwright_cache:/root/.cache/ms-playwright

  worker:
    build:
      context: ../backend
    env_file: .env
    command: ["celery", "-A", "app.tasks.celery_app", "worker", "--loglevel=info"]
    depends_on:
      redis:
        condition: service_healthy

  beat:
    build:
      context: ../backend
    env_file: .env
    command: ["celery", "-A", "app.tasks.celery_app", "beat", "--loglevel=info"]
    depends_on:
      redis:
        condition: service_healthy

  frontend:
    build:
      context: ../frontend
    ports:
      - "5173:80"
    profiles: ["self-host"]

volumes:
  postgres_data:
  playwright_cache:
```

```bash
# docker/.env.example
DATABASE_URL=postgresql+asyncpg://inventory_monitor:changeme@postgres:5432/inventory_monitor
REDIS_URL=redis://redis:6379/0
JWT_SECRET=change-this-to-a-long-random-string
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
OTP_PROVIDER=console
TIMEZONE=Asia/Kolkata
ENVIRONMENT=production
LOG_LEVEL=INFO
TELEGRAM_BOT_TOKEN=
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_ADDRESS=
POSTGRES_PASSWORD=changeme
```

- [ ] **Step 2: Verify the compose file is valid**

Run: `cp docker/.env.example docker/.env && docker compose -f docker/docker-compose.yml config`
Expected: exit code 0, prints the fully resolved compose configuration with no errors

- [ ] **Step 3: Commit**

```bash
git add docker/docker-compose.yml docker/.env.example
git commit -m "feat: add docker-compose stack and environment template"
```

---

### Task 34: Vercel config and deployment README

**Files:**
- Create: `frontend/vercel.json`
- Create: `README.md`

**Interfaces:**
- Produces `frontend/vercel.json`: static Vite build (`npm run build` → `dist`) with an SPA rewrite (`/(.*)` → `/index.html`) so client-side routes resolve on a hard refresh; `VITE_API_URL`/`VITE_WS_URL` are set as Vercel project environment variables pointing at wherever the backend Compose stack is hosted (a VPS, Railway, Fly.io, Render, or a home server — the compose file from Task 33 doesn't assume any specific one).
- Produces the root `README.md`: architecture summary (links to the design spec), installation (local Docker Compose flow, including the one-time `alembic upgrade head` migration step this plan deliberately doesn't run automatically on container boot — avoids a migration race across multiple starting replicas), configuration (every `.env` var from Task 33 explained), deployment (frontend → Vercel, backend → any Docker host), developer guide (running backend/frontend tests, adding a fifth retailer by implementing `BaseRetailProvider`), and a pointer to the auto-generated API docs at `/docs` (FastAPI's built-in Swagger UI, needs no separate authoring).

- [ ] **Step 1: Write the config and docs**

```json
// frontend/vercel.json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

```markdown
# README.md

# Multi-Retailer Inventory Monitor

Monitors product availability and price across Blinkit, Zepto, Swiggy Instamart,
and BigBasket, and notifies you (and anyone you invite) on changes. It never adds
anything to a cart, checks out, or holds a payment method — see
`docs/superpowers/specs/2026-07-15-multi-retailer-inventory-monitor-design.md`
for the full design and the hard constraints behind that.

## Architecture

Clean Architecture Python backend (`domain` → `application` → `infrastructure`/`api`)
split across an `api` (FastAPI) process and a `monitor` (asyncio + Playwright)
process, with Celery/Redis handling notification and analytics side-effects, and a
React/TypeScript dashboard. Full rationale in the design spec linked above.

## Local development

1. `cp docker/.env.example docker/.env` and fill in a real `JWT_SECRET`.
2. `docker compose -f docker/docker-compose.yml build`
3. One-time schema setup: `docker compose -f docker/docker-compose.yml run --rm api alembic upgrade head`
4. `docker compose -f docker/docker-compose.yml up postgres redis api monitor worker beat`
5. API docs: `http://localhost:8000/docs`. OTP codes print to the `api`/`monitor`
   container logs by default (`OTP_PROVIDER=console`) — no SMS account needed to
   develop locally.
6. Frontend: `cd frontend && npm install && npm run dev` (reads `VITE_API_URL`/
   `VITE_WS_URL` from `frontend/.env.local`, defaulting to `localhost:8000`).

## Configuration

All backend configuration is environment variables (`docker/.env`), validated by
`app.core.config.Settings`: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`,
`JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`,
`OTP_PROVIDER` (`console` locally; implement a new `OtpProvider` adapter — e.g.
Twilio, MSG91 — against `app.domain.ports.otp.OtpProvider` for production SMS),
`TIMEZONE`, `ENVIRONMENT`, `LOG_LEVEL`, `TELEGRAM_BOT_TOKEN`, `SMTP_*`.

## Deployment

- **Backend** (`api`, `monitor`, `worker`, `beat`, `redis`, `postgres`): deploy
  `docker/docker-compose.yml` to any persistent Docker host — a VPS, Railway,
  Fly.io, Render, or a home server. It needs to run 24/7 (the `monitor` process
  is a long-lived Playwright scheduler), which is why it can't go on Vercel.
- **Frontend**: deploy to Vercel using `frontend/vercel.json`; set `VITE_API_URL`
  and `VITE_WS_URL` (`wss://...`) as Vercel project env vars pointing at the
  backend host above.

## Developer guide

- Backend tests: `cd backend && python -m pytest`
- Frontend tests: `cd frontend && npm run test -- --run`
- Add a fifth retailer: implement `BaseRetailProvider` (`app/domain/ports/provider.py`)
  the way `app/infrastructure/providers/blinkit/provider.py` does, register it in
  `app/monitor/main.py`'s `InMemoryProviderRegistry`, and seed it into
  `SUPPORTED_RETAILERS` (`app/infrastructure/db/seed.py`) — no other module needs
  to change.
- API reference: FastAPI's auto-generated Swagger UI at `/docs` (and ReDoc at
  `/redoc`) on the running `api` service — always in sync with the routers, never
  hand-maintained.
```

- [ ] **Step 2: Verify**

Run: `cd frontend && cat vercel.json | python -m json.tool`
Expected: exit code 0 (valid JSON)

- [ ] **Step 3: Commit**

```bash
git add frontend/vercel.json README.md
git commit -m "docs: add Vercel config and deployment README"
```

---

## Self-Review Notes

- **Spec coverage:** every design-spec section (§1 constraints, §3 auth, §4 architecture, §5 data model, §6 providers, §7 monitoring engine, §8 notifications, §9 API/frontend, §10 deployment, §11 testing) maps to at least one task above; §12/§13 (project structure, code quality) are enforced throughout via the Global Constraints block and the file layout every task follows.
- **Placeholder scan:** no `TODO`/`TBD` in any step; the two spots that look like open questions — retailer CSS selectors (Task 7) and the OTP SMS provider (Task 15) — are both documented as intentional, swappable extension points behind an interface (`BLINKIT_SELECTORS`, `OtpProvider`), not unfinished work, and both have concrete default implementations (console OTP; best-effort selectors validated against local fixtures) that make every task's tests pass today.
- **Type consistency:** verified `ProviderProductResult`, `Snapshot`, `DetectionEvent`, `Watch`, `WatchTarget`, `NotificationChannel`, `NotificationContext`, and the repository method signatures stay identical everywhere they're consumed across Tasks 2–24; `EventType`/`Availability`/`NotificationChannelType` enum members are used consistently from Task 2 onward with no renames.

