from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings
from app.auth.dependencies import get_current_user

limiter = Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            user = await get_current_user(request.headers.get('Authorization', '').replace('Bearer', ''), request.app.state.db)
            request.state.user = user
        except:
            user = None
        if request.url.path.startswith('/api/items'):
            if user:
                await limiter.limit('3/minute', key=f'user:{user.id}')(request)
            await limiter.limit('10/10seconds')(request)
        return await call_next(request)