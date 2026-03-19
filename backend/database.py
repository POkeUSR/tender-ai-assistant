import os
from datetime import datetime
from typing import AsyncGenerator, Optional
import uuid

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship

import bcrypt

# 1. Настройка подключения - используем asyncpg для асинхронных операций
DATABASE_URL = os.getenv("DATABASE_URL")

# Handle missing DATABASE_URL for development
if not DATABASE_URL:
    DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/tender"

# Ensure we're using asyncpg driver
if "postgresql+" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Sync engine for legacy endpoints (psycopg2)
try:
    SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "").replace("postgresql+", "postgresql://")
    from sqlalchemy import create_engine
    sync_engine = create_engine(SYNC_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://"))
    from sqlalchemy.orm import sessionmaker
    SyncSessionLocal = sessionmaker(bind=sync_engine)
except Exception as e:
    print(f"[DB] Warning: Could not create sync engine: {e}")
    sync_engine = None
    SyncSessionLocal = None


def get_db_sync():
    """Sync database session for legacy endpoints."""
    if SyncSessionLocal is None:
        raise RuntimeError("Sync engine not available")
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()

class Base(DeclarativeBase):
    pass

# 2. Модели по плану
class Tender(Base):
    __tablename__ = "tenders"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    raw_text = Column(Text, nullable=True)
    status = Column(String, default="uploaded") # uploaded, processing, analyzed, failed
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    analysis = relationship("Analysis", back_populates="tender", uselist=False)
    score = relationship("Score", back_populates="tender", uselist=False)
    proposal = relationship("Proposal", back_populates="tender", uselist=False)

class Analysis(Base):
    __tablename__ = "analysis"
    id = Column(Integer, primary_key=True)
    tender_id = Column(String, ForeignKey("tenders.id"))
    summary = Column(Text)
    risks = Column(JSON) # Храним риски как список в JSON
    
    tender = relationship("Tender", back_populates="analysis")

class Score(Base):
    __tablename__ = "scores"
    id = Column(Integer, primary_key=True)
    tender_id = Column(String, ForeignKey("tenders.id"))
    value = Column(Float)
    reason = Column(Text)
    
    tender = relationship("Tender", back_populates="score")

class Proposal(Base):
    __tablename__ = "proposals"
    id = Column(Integer, primary_key=True)
    tender_id = Column(String, ForeignKey("tenders.id"))
    text = Column(Text)
    
    tender = relationship("Tender", back_populates="proposal")


# User model for authentication
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# 3. Функции инициализации
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


# User functions for auth - sync version (for legacy endpoints)
def get_user_by_email(db_session, email: str) -> Optional[User]:
    """Get user by email (sync version)."""
    return db_session.query(User).filter(User.email == email).first()

def get_user_by_id(db_session, user_id: int) -> Optional[User]:
    """Get user by ID (sync version)."""
    return db_session.query(User).filter(User.id == user_id).first()

def create_user(db_session, email: str, hashed_password: str) -> User:
    """Create a new user (sync version)."""
    user = User(email=email, hashed_password=hashed_password)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# User functions for auth - using async SQLAlchemy
async def get_user_by_email_async(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email (async version)."""
    from sqlalchemy import select
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalar_one_or_none()

async def get_user_by_id_async(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID (async version)."""
    from sqlalchemy import select
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalar_one_or_none()

async def create_user_async(db: AsyncSession, email: str, hashed_password: str) -> User:
    """Create a new user (async version)."""
    user = User(email=email, hashed_password=hashed_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
    """Get user by ID (async version)."""
    from sqlalchemy import select
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalar_one_or_none()

async def create_user_async(db: AsyncSession, email: str, hashed_password: str) -> User:
    """Create a new user (async version)."""
    user = User(email=email, hashed_password=hashed_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
