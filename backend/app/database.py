from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

# Create async engine — used by FastAPI (single event loop)
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    pool_recycle=300,
    echo=False,
)

# Async session maker — used by FastAPI handlers
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def _make_celery_session_maker() -> async_sessionmaker[AsyncSession]:
    """Create a disposable engine+session for Celery tasks.

    Each Celery task runs in a fresh event loop (via async_task decorator).
    Module-level engine has asyncpg connections bound to a different loop →
    'attached to a different loop' errors. NullPool creates a fresh connection
    per checkout and disposes it on return, so nothing survives across loops.
    """
    celery_engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
        echo=False,
    )
    return async_sessionmaker(
        celery_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@asynccontextmanager
async def get_celery_db() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for Celery tasks — fresh engine per call."""
    session_maker = _make_celery_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    # Dispose engine immediately so connections don't leak
    await session_maker.kw["bind"].dispose()


# Database dependency generator — used by FastAPI Depends()
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
