from fastapi import HTTPException, status
from jose import jwt, JWTError
from passlib.context import Argon2Context
from datetime import datetime, timedelta, timezone
import redis.asyncio as redis
import uuid
from app.core.config import settings
from app.core.redis import redis_client

pwd_context = Argon2Context(schemes=["argon2id"])

async def create_access_token(data: dict):
    to_encode = data.copy()
    jti = str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"jti": jti, "exp": expire, "type": "access"})
    token = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return token, jti
