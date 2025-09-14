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

async def create_refresh_token(data: dict):
    to_encode = data.copy()
    jti = str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"jti": jti, "exp": expire, "type": "refresh"})
    token = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return token, jti

async def blacklist_token(jti: str, ttl_seconds: int):
    await redis_client.setex(f'blacklist: {jti}', ttl_seconds, '1')

async def is_token_blacklisted(jti: str) -> bool:
    return await redis_client.exists(f'blacklist: {jti}')

async def verify_token(token: str, token_type: str):
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload["type"] != token_type:
            raise HTTPException(status_code=401, detail="Invalid token type")
        if await is_token_blacklisted(payload["jti"]):
            raise HTTPException(status_code=401, detail="Token blacklisted")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="invalid token")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)