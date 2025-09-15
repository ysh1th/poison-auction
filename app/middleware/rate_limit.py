from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import app.core.redis as redis_module

async def sliding_window_allow(key: str, limit: int, window_seconds: int) -> bool:
    now = int(__import__('time').time())
    window_start = now - window_seconds
    try:
        client = redis_module.redis_client
        pipe = client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window_seconds)
        _, _, count, _ = await pipe.execute()
        return count <= limit
    except Exception:
        return True

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else 'unknown'
        global_key = f"rl:ip:{ip}:10in10"
        if not await sliding_window_allow(global_key, 10, 10):
            from fastapi import HTTPException
            raise HTTPException(status_code=429, detail="Too many requests")

        is_write = request.method in {"POST", "PUT", "PATCH", "DELETE"}
        if is_write and request.url.path.startswith('/items'):
            user_id = getattr(getattr(request.state, 'user', None), 'id', None)
            if user_id is not None:
                user_key = f"rl:user:{user_id}:3in60"
                if not await sliding_window_allow(user_key, 3, 60):
                    from fastapi import HTTPException
                    raise HTTPException(status_code=429, detail="Write rate limit exceeded")

        return await call_next(request)