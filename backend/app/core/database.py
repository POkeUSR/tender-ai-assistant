"""
Async database configuration for PostgreSQL.
Provides async engine, session maker, and dependency for FastAPI.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# Base class for models (defined here to avoid circular imports)
class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Create async engine - remove sslmode from URL and use connect_args instead
db_url = settings.database_url.replace("?sslmode=require", "").strip()
print(f"[DB] Attempting to connect to: {db_url}")

engine: AsyncEngine = create_async_engine(
    db_url,
    echo=True,
    connect_args={
        "ssl": True,
    },
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session.
    Yields the session and ensures it's closed after use.
    
    Usage in FastAPI:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()


async def init_db() -> None:
    """
    Create all tables in the database.
    Import models inside function to avoid circular imports.
    """
    # Local imports to avoid circular dependency
    from app.models.models import Tender, Analysis, Score, Proposal
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    """Drop all tables in the database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
