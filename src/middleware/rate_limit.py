"""
Rate limiting middleware using Redis.
"""

from datetime import timedelta
from typing import Callable, Optional

import redis.asyncio as redis
from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis-based rate limiting middleware.

    Uses a sliding window counter algorithm for rate limiting.
    Limits are configurable per path prefix.
    """

    # Rate limit configurations: path_prefix -> (requests, window_seconds)
    RATE_LIMITS = {
        "/api/v1/auth/": (settings.rate_limit_auth_requests, settings.rate_limit_auth_window_seconds),
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

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        # Skip rate limiting for non-API routes
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # Get rate limit configuration
        max_requests, window_seconds = self.get_rate_limit(request.url.path)

        # Get client identifier
        key = self.get_client_identifier(request)

        try:
            redis_client = await self.get_redis()

            # Increment counter
            current = await redis_client.incr(key)

            # Set expiry on first request
            if current == 1:
                await redis_client.expire(key, window_seconds)

            # Get TTL for Retry-After header
            ttl = await redis_client.ttl(key)

            # Check if over limit
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

            # Process request
            response = await call_next(request)

            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(max_requests)
            response.headers["X-RateLimit-Remaining"] = str(max(0, max_requests - current))
            response.headers["X-RateLimit-Reset"] = str(ttl)

            return response

        except redis.RedisError:
            # If Redis is unavailable, allow request (fail open)
            return await call_next(request)


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
