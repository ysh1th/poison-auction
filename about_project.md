### Tech stack used

- **PostgreSQL** (real SQL, not SQLite)
- **Real authentication** (JWT + refresh tokens + hashed passwords)
- **Custom middleware** (rate-limit, request-ID logging, role check)
- **Redis** (for token-blacklist & rate-limit counters)
- **Unit tests** (pytest, coverage ≥ 80 %)

---

Project name

**“Silent Auction Poison Pill”**

A **time-boxed** silent-auction site where every bidder can **only place ONE single bid per item**; once submitted the bid is **encrypted** and **immutable** until the auction ends.

The twist: **you can poison your own bid**—i.e. mark it as “auto-raise” which means the system will automatically outbid any higher offer by the smallest possible increment **until your budget is exhausted**.

This forces you to learn **row-level locking, transactional race-condition handling, JWT refresh flows, and Redis-backed rate limiting** in a fun, adversarial setting.

---

Core rules (dictate the tech you must use)

1. One-account-per-email, password hashed with `argon2id`.
2. Access token 15 min, refresh token 7 days, **refresh-rotation** (old refresh token becomes invalid after use).
3. Black-listed tokens stored in **Redis** with TTL = remaining lifetime.
4. Global rate-limit: 10 requests / IP / 10 s; **auction-write** endpoints: 3 requests / authenticated user / 60 s.
5. Poison-bid logic runs inside a **PostgreSQL transaction** with `SELECT ... FOR UPDATE` to prevent lost-update.
6. Middleware must inject a **request-ID** header into every response and log it with structlog → makes debugging concurrent poison-bids possible.
7. 80 % test coverage enforced with `pytest-cov` pre-push hook.

---

Entity diagram (PostgreSQL)

```
users          (id, email, pw_hash, role, created_at)
items          (id, title, desc, close_at, base_price, status)
bids           (id, item_id, user_id, amount, poison_budget, poison_step, created_at)
               UNIQUE (item_id, user_id)  -- enforces single bid
blacklist      (jti, exp)                 -- Redis SET, TTL driven

```

---

FastAPI layer (what you will write)

```
app/
├── auth/
│   ├── dependencies.py   # reusable JWT + role checker
│   ├── utils.py          # argon2, create / rotate tokens
│   └── test_auth.py      # unit tests w/ faker + pytest-asyncio
├── auctions/
│   ├── endpoints.py      # POST /items/{id}/bid  (poison logic)
│   ├── tx_bid.py         # async txn wrapper, SELECT FOR UPDATE
│   └── test_tx.py        # concurrent bid bombs to verify race-free
├── middleware/
│   ├── request_id.py     # starlette.basehttpmiddleware
│   ├── rate_limit.py     # Redis sliding-window
│   └── test_middleware.py
├── core/
│   ├── db.py             # SQLAlchemy async engine
│   ├── redis.py          # aioredis pool
│   └── config.py         # pydantic settings, env driven
main.py
Dockerfile
docker-compose.yml  (postgres:15, redis:7, backend, vite dev server)

```

---

React + Vite frontend (only the interesting bits)

- Login page uses `react-hook-form` + `zod`; stores **refresh** in http-only secure cookie, **access** in memory.
- Silent refresh via `useRefreshToken()` hook (axios interceptor).
- Auction room: Server-Sent-Events stream (`/events/{item_id}`) pushes new high-bid in real time; UI shows your poison budget bar shrinking live.
- Vite proxy config routes `/api` and `/events` to FastAPI – zero CORS pain during development.

---

Weekend-by-weekend burn-down
**W1  Backend skeleton**

- Docker-compose, migrations (alembic), user register + login, JWT refresh rotation, blacklist in Redis.
- Middleware: request-ID + rate-limit; write pytest for every function.

**W2  Poison-bid core**

- Auction endpoints, transactional bid placement, unique constraint test, concurrent pytest-xdist stress test (simulate 50 users hammering the same millisecond).

**W3  Frontend + polish**

- React-Vite login, auction list, SSE bid stream, poison slider.
- Add pytest coverage badge to README; push to GitHub Actions.

---

Starter command sequence

```bash
# 1. bootstrap
git clone <https://github.com/yourname/silent-auction-poison.git>
cd silent-auction-poison
cp .env.example .env          # tweak postgres & redis URLs

# 2. backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
pytest -q --cov=app --cov-report=term-missing

# 3. frontend
cd frontend
pnpm install
pnpm dev          # runs on :5173, proxy to :8000 already set

```