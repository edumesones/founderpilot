"""Database configuration and session management."""

from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker, Session

from src.core.config import settings

# Single declarative Base for the whole project. Re-exported here so the
# historical `from src.core.database import Base` imports keep working;
# there must only ever be ONE Base/MetaData or foreign keys between
# models declared in different modules cannot be resolved.
from src.models.base import Base  # noqa: E402,F401


# Create async engine for async operations
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create sync engine for sync operations
# Note: Need to convert async URL to sync for sync engine
sync_url = settings.database_url.replace("+asyncpg", "")
engine = create_engine(
    sync_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Sync session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Alias for backwards compatibility
get_db = get_async_db


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Async session as a context manager, for code outside FastAPI.

    `get_async_db` is an async generator meant for `Depends()`; background
    workers and webhook handlers need `async with ... as db` instead. The block
    commits on success and rolls back on any exception, so callers only have to
    describe the work.
    """
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def get_sync_db() -> Generator[Session, None, None]:
    """Dependency that provides a sync database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def init_db() -> None:
    """Initialize database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await async_engine.dispose()
