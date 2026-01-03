import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import setup_logger

logger = setup_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        duration = (time.time() - start_time) * 1000

        logger.info(
            "%s %s -> %s (%.2f ms)",
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )

        return response
