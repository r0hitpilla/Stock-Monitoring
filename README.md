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

   Alternatively, `docker compose -f docker/docker-compose.yml --profile self-host up frontend`
   builds and serves the frontend from the same Compose stack.

## Configuration

All backend configuration is environment variables (`docker/.env`), validated by
`app.core.config.Settings`: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`,
`JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`,
`OTP_PROVIDER` (`console` locally; implement a new `OtpProvider` adapter — e.g.
Twilio, MSG91 — against `app.domain.ports.otp.OtpProvider` for production SMS),
`TIMEZONE`, `ENVIRONMENT`, `LOG_LEVEL`, `TELEGRAM_BOT_TOKEN`, `SMTP_HOST`,
`SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_ADDRESS`. `docker/.env`
also sets `POSTGRES_PASSWORD`, consumed directly by the `postgres` container
rather than by `Settings`.

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
  the provider dict passed to `InMemoryProviderRegistry` in `app/monitor/main.py`,
  and seed it into `SUPPORTED_RETAILERS` (`app/infrastructure/db/seed.py`) — no
  other module needs to change.
- API reference: FastAPI's auto-generated Swagger UI at `/docs` (and ReDoc at
  `/redoc`) on the running `api` service — always in sync with the routers, never
  hand-maintained.
