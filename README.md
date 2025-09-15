# Silent Auction Poison Pill

Silent Auction Poison Pill is a time-boxed silent-auction platform where each user can place only one bid per item. The twist lies in the poison-bid mechanic: bidders can mark their bid as “auto-raise,” allowing the system to automatically outbid higher offers incrementally until their budget is exhausted. This creates a dynamic and adversarial bidding environment, emphasizing real-time updates, strategic planning, and concurrency challenges

## Prerequisites
- Python 3.10+
- Node.js 18+ and pnpm (for frontend if/when added)
- Docker (optional, for running Postgres and Redis via compose)

## Backend setup (local)
```bash
python -m venv .venv
source .venv/bin/activate           # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                # create and adjust env if present
```

Set the following env vars in `.env`
- SECRET_KEY
- DATABASE_URL (e.g. postgresql+asyncpg://postgres:password@localhost:5432/auction)
- REDIS_URL (e.g. redis://localhost:6379)

Run database
- Local Postgres recommended via Docker Compose

```bash
docker compose up -d postgres redis
alembic upgrade head
```

Run API
```bash
uvicorn main:app --reload
```

## Rate limiting and request IDs
- Request IDs added to every response header `X-Request-ID`
- Global rate-limit: 10 requests per IP per 10s
- Write endpoints under `/items` limited to 3 per user per 60s

## Auth
- JWT access 15 min, refresh 7 days with rotation
- Argon2 password hashing via passlib CryptContext
- Blacklisted tokens stored in Redis with TTL equal to remaining token life

## Testing
```bash
pytest -q --cov=app --cov-report=term-missing
```
Tests use in-memory SQLite and a fake Redis; no external services required.

## Project layout
```
app/
  auth/
  auctions/
  core/
  middleware/
  models.py
main.py
alembic/
```

## Docker
```bash
docker compose up --build
```

## Notes
- Migrations are the single source of truth; the app does not auto-create tables
- To use real Redis/Postgres locally, set `REDIS_URL` and `DATABASE_URL` accordingly