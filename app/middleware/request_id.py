from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
import uuid

logger = structlog.get_logger()

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        logger.info("Request started", method=request.method, url=str(request.url), request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info("Request completed", status_code=response.status_code, request_id=request_id)
        return response