# Multi-Retailer Inventory Monitoring Platform — Design

Date: 2026-07-15
Status: Approved

## 1. Purpose & Hard Constraints

A multi-user platform that monitors product availability and price across Indian
quick-commerce retailers and notifies users of changes. It is explicitly **not**
a purchasing tool.

**Hard constraints (apply to every user, every retailer, no exceptions):**

- MUST NOT automatically add products to a cart.
- MUST NOT automatically complete checkout.
- MUST NOT automatically purchase a product.
- MUST NOT store payment methods or hold/manage any monetary balance ("wallet") for
  any user.
- The only actions the system takes on a detected change are: record it and notify
  the user. The user always completes any purchase themselves, outside this system.

## 2. Supported Retailers

Blinkit, Zepto, Swiggy Instamart, BigBasket — added behind a common provider
interface (`BaseRetailProvider`) so future retailers require a new adapter only,
no changes to monitoring/notification/API code.

## 3. Users & Access

- Multi-user. Each friend creates their own account and configures their own
  products/cities/pincodes/notification channels, isolated from other users'
  account data.
- Auth: phone number + OTP. JWT access/refresh tokens after verification.
- OTP delivery goes through a pluggable `OtpProvider` interface: a console/log
  provider for local development (no SMS account required to build/test), and a
  real adapter (Twilio, MSG91, or similar — chosen at deploy time) for production.
  OTP requests are rate-limited per phone number (cooldown + hourly cap) to bound
  SMS cost and abuse.
- No payment methods, no wallet, ever (see §1).

## 4. High-Level Architecture

Clean Architecture, one Python codebase, two runtime entrypoints:

```
domain/         entities + ports (interfaces only, no framework deps)
application/    use cases / services, depend only on domain ports
infrastructure/ concrete adapters: DB repos, Playwright providers,
                notification senders, Redis client, SMS adapter
api/            FastAPI app: routers, Pydantic DTOs, WebSocket, DI wiring
monitor/        asyncio scheduler entrypoint (separate process)
tasks/          Celery app + tasks (separate process)
```

Runtime processes (Docker Compose services):

| Service    | Role |
|------------|------|
| `api`      | FastAPI/Uvicorn — REST + WebSocket |
| `monitor`  | asyncio scheduler + Playwright, drives all scraping |
| `worker`   | Celery worker — notifications, analytics rollups |
| `beat`     | Celery beat — periodic maintenance (log cleanup, daily aggregates) |
| `redis`    | Celery broker, pub/sub fanout to WebSocket, cache |
| `postgres` | Primary DB in production (SQLite file for pure local dev) |
| `frontend` | Vite build; deployed to Vercel in prod, or served in-stack for self-host |

**Why asyncio scheduler + Celery, not Celery for scraping too:** Playwright's
async API is the natural fit for concurrent browser automation; Celery's
traditional worker model is sync-oriented and awkward for that. The `monitor`
process owns all scraping and diffing directly via asyncio. Celery is used for
what it's good at: decoupled, retryable, at-least-once side effects (sending a
notification, rolling up analytics) that shouldn't block the scrape loop.

**Why Vercel + generic Docker backend, not Vercel-only:** Vercel serverless
functions cannot run a persistent Playwright browser, an asyncio scheduler, Celery
workers, Redis, or long-lived WebSocket connections — all of which this system
needs 24/7. The React dashboard deploys to Vercel; the backend deploys as a
Docker Compose stack to any persistent host (VPS, Railway, Fly.io, Render, home
server) — the compose file is written generically, not tied to one provider.

## 5. Data Model

- **User**(id, phone_number, email?, created_at)
- **OtpChallenge**(id, phone_number, code_hash, expires_at, consumed, attempt_count)
- **Retailer**(id, slug, name, is_active) — seeded: blinkit, zepto, instamart, bigbasket
- **Product**(id, user_id, name, keyword, canonical_image_url?) — a user's named
  thing to track
- **WatchTarget**(id, retailer_id, city, pincode, keyword) — unique on
  (retailer_id, city, pincode, keyword); the **shared, dedup'd scrape unit**. If
  two users watch the same product/retailer/city/pincode, they share one
  `WatchTarget` and one scrape stream instead of doubling scrape load.
- **Watch**(id, user_id, product_id, watch_target_id, interval_seconds, is_active) —
  a user's subscription to a WatchTarget
- **Snapshot**(id, watch_target_id, timestamp, availability_status, price, mrp,
  discount_pct, eta_minutes, store_name, image_url, quantity_label,
  variant_label, product_url) — append-only; this is the "History" table
- **DetectionEvent**(id, watch_target_id, snapshot_id, previous_snapshot_id,
  event_type, created_at) — event_type ∈ {stock_available, out_of_stock,
  low_stock, price_changed, new_variant, eta_changed, store_changed}
- **NotificationChannel**(id, user_id, type, config_json, is_verified) — type ∈
  {telegram, discord, email, push}
- **NotificationLog**(id, user_id, detection_event_id, channel_id, status,
  sent_at, dedup_key)
- **Settings**(user-scoped polling preferences + global system settings, timezone)
- **SystemLog** — structured JSON logs, written to stdout/file; recent entries
  also queryable via API for the Logs page

## 6. Provider Layer

`BaseRetailProvider` ABC, implemented once per retailer:

```
initialize(location: LocationContext)   # sets city/pincode delivery context
search_product(keyword: str)
get_product(product_ref)
check_availability(product_ref)
extract_price(...)
extract_eta(...)
extract_store(...)
extract_image(...)
extract_quantity(...)
extract_variants(...)
health_check()
```

All extraction methods return a standardized `ProviderProductResult` Pydantic
model (product, retailer, city, store, availability, price, mrp, discount,
delivery_eta, image_url, timestamp, product_url, quantity, variants).

Concurrency & resilience per provider:

- One Chromium browser instance per provider inside the `monitor` process;
  multiple browser contexts bounded by an `asyncio.Semaphore` (default 3–5
  concurrent) per retailer.
- Retries with exponential backoff (`tenacity`), per-action timeouts.
- Automatic context/browser restart on crash.
- Circuit breaker: after N consecutive failures, mark the retailer unhealthy and
  back off its polling interval instead of hammering it.
- Graceful shutdown: closes all contexts/browsers cleanly on SIGTERM.
- Selectors: prefer accessible/robust selectors (role, text, test-id-like
  attributes) over brittle XPath, per retailer.

## 7. Monitoring Engine

Asyncio loop inside `monitor`:

1. Every tick (~1s), find `WatchTarget`s due for a check (interval elapsed).
2. Dispatch due targets as bounded-concurrency tasks, grouped by retailer.
3. Normalize the provider result, diff against the latest `Snapshot` for that
   `WatchTarget`.
4. On any change: insert a new `Snapshot` + one or more `DetectionEvent` rows.
5. Publish the event to Redis (`events:{watch_target_id}`) for live WebSocket
   fanout.
6. Enqueue a Celery `process_detection_event(event_id)` job.

Celery `process_detection_event`: resolves every `Watch` subscribed to the
`WatchTarget`, resolves each user's `NotificationChannel`s, applies dedup rules
(only notify on state *transitions*, plus a short cooldown to prevent
flapping-stock alert storms), enqueues per-channel send tasks, writes
`NotificationLog`.

## 8. Notifications

`NotificationSender` interface, one adapter per channel:

- **Telegram** — bot API, user links their chat via a bot deep link
- **Discord** — user-supplied webhook URL
- **Email** — SMTP (optional/off by default)
- **Desktop / Browser** — collapsed into one frontend-driven channel: OS
  `Notification` API fires client-side from the live WebSocket stream while a
  tab is open; Web Push (VAPID) is the enhancement for delivery while no tab is
  open. No separate backend "desktop" channel is needed.

## 9. API & Frontend

FastAPI REST under `/api/v1`:

- `/auth/otp/request`, `/auth/otp/verify`, `/auth/refresh`
- `/products` (CRUD, user-scoped)
- `/watches` (CRUD, user-scoped)
- `/retailers` (list + health status)
- `/history` (query snapshots/detection events, filterable)
- `/notifications` (channels CRUD/verify, notification log)
- `/analytics` (price history, availability %, restock frequency, downtime,
  retailer/product comparison)
- `/settings`
- `/logs`
- `/monitoring/status`, `/health`

One JWT-authenticated `/ws` endpoint, backed by Redis pub/sub so it works across
multiple `api` replicas; clients subscribe to their own watch targets' event
streams.

Frontend: React 18 + TypeScript + Vite + Tailwind + shadcn/ui + Framer Motion +
Chart.js. Dark-mode-first, glassmorphism, animated state transitions. Pages:
Dashboard, Products, Retailers, History, Notifications, Logs, Settings. React
Query for server state; a WebSocket hook feeds live updates into toasts and OS
notifications.

## 10. Deployment

- Multi-stage Dockerfiles: backend (python slim + `playwright install
  --with-deps chromium`), frontend (node build).
- `docker-compose.yml` runs the full stack (api, monitor, worker, beat, redis,
  postgres) on any generic Docker host, with healthchecks and named volumes
  (postgres data, Playwright browser cache, logs).
- Frontend additionally ships a `vercel.json` for the Vercel deploy path,
  pointed at the backend's public URL via env var.
- `.env.example` documents every configuration value (DB, Redis, JWT secret,
  SMS provider credentials, notification channel defaults, polling intervals,
  timezone). YAML config supported for products/retailers/cities/pincodes
  seed data.

## 11. Testing

- Pytest, ≥90% coverage target on domain/application/api layers.
- Unit/API tests run against mock providers (fixture-driven canned
  `ProviderProductResult`s) — no live network calls in the default test run.
- A small opt-in `@pytest.mark.integration` suite exercises real Playwright
  extraction logic against saved HTML fixtures per retailer (not live sites),
  keeping CI fast and non-flaky while still covering selector logic.

## 12. Project Structure

```
backend/
  app/
    domain/
    application/
    infrastructure/
      db/               SQLAlchemy models, repositories, Alembic migrations
      providers/        base.py + blinkit/, zepto/, instamart/, bigbasket/
      notifications/    telegram.py, discord.py, email.py
      cache/            redis client, pub/sub
      sms/              otp provider adapters (console, twilio, msg91)
    api/                FastAPI app, routers, schemas, deps, websocket
    monitor/            asyncio scheduler entrypoint
    tasks/              celery app + tasks
    core/               config (pydantic-settings), logging, security
  tests/
    unit/ integration/ fixtures/
  alembic/
  pyproject.toml
  Dockerfile
frontend/
  src/ (pages, components, hooks, api client, store)
  Dockerfile
  vercel.json
docker/
  docker-compose.yml
  docker-compose.prod.yml
  .env.example
docs/
  architecture.md
```

## 13. Code Quality

Type hints everywhere, docstrings on public interfaces, PEP8, Black formatting,
Ruff linting, MyPy strict on `domain`/`application`.
