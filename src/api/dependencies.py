"""
FastAPI dependencies for dependency injection.
"""

from typing import Annotated, AsyncGenerator

import redis.asyncio as redis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import AsyncSessionLocal
from src.core.exceptions import AuthenticationError, TokenExpiredError
from src.models.user import User
from src.services.audit import AuditService
from src.services.auth import AuthService
from src.services.google_oauth import GoogleOAuthService
from src.services.jwt import JWTService


# HTTP Bearer token scheme
http_bearer = HTTPBearer(auto_error=False)


# Redis connection pool
_redis_pool: redis.ConnectionPool | None = None


async def get_redis_pool() -> redis.ConnectionPool:
    """Get or create Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _redis_pool


async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """
    Dependency that yields a Redis client.

    Usage:
        @router.get("/route")
        async def route(redis: Redis = Depends(get_redis)):
            ...
    """
    pool = await get_redis_pool()
    client = redis.Redis(connection_pool=pool)
    try:
        yield client
    finally:
        await client.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that yields a database session.

    Usage:
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_jwt_service() -> JWTService:
    """Get JWT service instance."""
    return JWTService()


def get_google_oauth_service() -> GoogleOAuthService:
    """Get Google OAuth service instance."""
    return GoogleOAuthService()


async def get_audit_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuditService:
    """Get audit service instance."""
    return AuditService(db)


async def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> AuthService:
    """Get auth service instance."""
    return AuthService(
        db=db,
        redis_client=redis_client,
    )


def get_token_from_cookie_or_header(request: Request) -> str | None:
    """
    Extract JWT token from cookie or Authorization header.

    Priority:
    1. access_token cookie
    2. Authorization: Bearer <token> header
    """
    # Try cookie first
    token = request.cookies.get("access_token")
    if token:
        return token

    # Try Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]

    return None


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> User:
    """
    Dependency that returns the current authenticated user.

    Extracts JWT from cookie or header, verifies it, and returns the user.

    Usage:
        @router.get("/me")
        async def get_me(user: User = Depends(get_current_user)):
            return user

    Raises:
        HTTPException 401: If not authenticated or token is invalid
    """
    token = get_token_from_cookie_or_header(request)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = AuthService(db=db, redis_client=redis_client)

    try:
        user_id = await auth_service.verify_access_token(token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await auth_service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_optional(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> User | None:
    """
    Dependency that returns the current user if authenticated, or None.

    Useful for endpoints that work differently for authenticated vs anonymous users.
    """
    try:
        return await get_current_user(request, db, redis_client)
    except HTTPException:
        return None


def get_client_ip(request: Request) -> str | None:
    """Extract client IP from request."""
    # Try X-Forwarded-For first (for reverse proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Fall back to direct client
    if request.client:
        return request.client.host

    return None


def get_user_agent(request: Request) -> str | None:
    """Extract user agent from request."""
    return request.headers.get("User-Agent")


# Type aliases for cleaner annotations
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[redis.Redis, Depends(get_redis)]
ClientIP = Annotated[str | None, Depends(get_client_ip)]
UserAgent = Annotated[str | None, Depends(get_user_agent)]
