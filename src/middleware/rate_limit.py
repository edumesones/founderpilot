"""
Rate limiting middleware using Redis.
"""

import logging
from datetime import timedelta
from typing import Callable, Optional

import redis.asyncio as redis
from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.core.config import settings

logger = logging.getLogger(__name__)

# A cached async Redis client belongs to the event loop that created it.
# When that loop is gone the failure surfaces as RuntimeError or
# AttributeError rather than a RedisError, so both have to count as
# "Redis is unavailable".
REDIS_FAILURES = (redis.RedisError, OSError, RuntimeError, AttributeError)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis-based rate limiting middleware.

    Uses a sliding window counter algorithm for rate limiting.
    Limits are configurable per path prefix.
    """

    # Rate limit configurations: path_prefix -> (requests, window_seconds)
    RATE_LIMITS = {
        "/api/v1/auth/": (settings.rate_limit_auth_requests, settings.rate_limit_auth_window_seconds),
        "/api/v1/invoices/": (200, 60),  # 200 requests per minute for invoice endpoints
    }

    DEFAULT_LIMIT = (100, 60)  # 100 requests per minute default

    def __init__(self, app, redis_url: str = settings.redis_url):
        super().__init__(app)
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None

    async def get_redis(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                decode_responses=True,
            )
        return self._redis

    def get_rate_limit(self, path: str) -> tuple[int, int]:
        """Get rate limit for a path."""
        for prefix, limit in self.RATE_LIMITS.items():
            if path.startswith(prefix):
                return limit
        return self.DEFAULT_LIMIT

    def get_client_identifier(self, request: Request) -> str:
        """Get unique identifier for the client."""
        # Try X-Forwarded-For first (for reverse proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        elif request.client:
            ip = request.client.host
        else:
            ip = "unknown"

        return f"rate_limit:{ip}:{request.url.path}"

    async def _discard_redis(self) -> None:
        """Drop the cached client so the next request builds a fresh one."""
        client, self._redis = self._redis, None
        if client is not None:
            try:
                await client.aclose()
            except Exception:  # noqa: BLE001 - the client is already broken
                pass

    async def _count_request(
        self, key: str, window_seconds: int
    ) -> Optional[tuple[int, int]]:
        """Count this request against `key`.

        Returns (count_so_far, ttl_seconds), or None when Redis is unavailable --
        rate limiting is never a reason to fail a request.
        """
        try:
            redis_client = await self.get_redis()
            current = await redis_client.incr(key)
            if current == 1:
                await redis_client.expire(key, window_seconds)
            ttl = await redis_client.ttl(key)
            return current, ttl
        except REDIS_FAILURES as exc:
            logger.warning("Rate limiting disabled for this request: %s", exc)
            await self._discard_redis()
            return None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        # Skip rate limiting for non-API routes
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        max_requests, window_seconds = self.get_rate_limit(request.url.path)
        key = self.get_client_identifier(request)

        counted = await self._count_request(key, window_seconds)
        if counted is None:
            # Fail open: Redis is unavailable.
            return await call_next(request)

        current, ttl = counted
        if current > max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
                headers={
                    "Retry-After": str(ttl),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(ttl),
                },
            )

        # Outside the try on purpose: a failure in the route is the route's, not
        # Redis's, and must not cause the request to be replayed.
        response = await call_next(request)

        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, max_requests - current))
        response.headers["X-RateLimit-Reset"] = str(ttl)
        return response


class SimpleRateLimiter:
    """
    Simple rate limiter for use as a dependency.

    Usage:
        rate_limiter = SimpleRateLimiter(requests=10, window=60)

        @router.post("/endpoint")
        async def endpoint(
            request: Request,
            _: None = Depends(rate_limiter),
        ):
            ...
    """

    def __init__(
        self,
        requests: int = 10,
        window: int = 60,
        redis_url: str = settings.redis_url,
    ):
        self.requests = requests
        self.window = window
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None

    async def get_redis(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                decode_responses=True,
            )
        return self._redis

    async def __call__(self, request: Request) -> None:
        """Check rate limit for request."""
        # Get client IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        elif request.client:
            ip = request.client.host
        else:
            ip = "unknown"

        key = f"rate_limit:{ip}:{request.url.path}"

        try:
            redis_client = await self.get_redis()

            current = await redis_client.incr(key)
            if current == 1:
                await redis_client.expire(key, self.window)

            if current > self.requests:
                ttl = await redis_client.ttl(key)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests",
                    headers={"Retry-After": str(ttl)},
                )

        except redis.RedisError:
            # Fail open if Redis is unavailable
            pass
