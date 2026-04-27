import time
import logging
from fastapi import Request

logger = logging.getLogger("insighta")


async def request_logging_middleware(request: Request, call_next):
    """Log request method, path, status, duration, and client IP."""

    start = time.time()
    client_ip = request.client.host if request.client else "unknown"

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        duration = time.time() - start

        logger.error(
            "%s %s → ERROR (%s) [%.3fs] IP=%s",
            request.method,
            request.url.path,
            str(e),
            duration,
            client_ip,
        )
        raise

    duration = time.time() - start

    logger.info(
        "%s %s → %s [%.3fs] IP=%s",
        request.method,
        request.url.path,
        status_code,
        duration,
        client_ip,
    )

    return response

