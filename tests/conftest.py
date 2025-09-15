import asyncio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.db import Base
from app.core import db as app_db
from app.core import redis as app_redis
from main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

class FakeRedis:
    def __init__(self):
        self.store = {}
    async def setex(self, key, ttl, value):
        self.store[key] = value
    async def exists(self, key):
        return 1 if key in self.store else 0

async def override_get_db():
    async with AsyncSessionLocal() as session:
        yield session

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    async def init_models():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.get_event_loop().run_until_complete(init_models())
    app.dependency_overrides[app_db.get_db] = override_get_db
    app_redis.redis_client = FakeRedis()
    yield

@pytest.fixture(scope="session")
def client():
    return TestClient(app)

