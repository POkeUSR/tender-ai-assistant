"""
Database models and connection for Tender AI Assistant.
Uses SQLAlchemy with SQLite for simplicity.
"""

import os
from datetime import datetime
from typing import Generator, Optional

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

# Database URL - can be overridden with environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tender.db")

# Create engine with connection arguments for SQLite
connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    documents = relationship("Document", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class Document(Base):
    """Document model for storing uploaded files and their metadata."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    vectorstore_path = Column(String, nullable=True)
    chunks_count = Column(Integer, default=0)
    file_size = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="documents")

    def __repr__(self):
        return f"<Document(id={self.id}, filename={self.filename}, user_id={self.user_id})>"


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database session.
    Yields the session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database - creates all tables.
    Should be called on application startup.
    """
    Base.metadata.create_all(bind=engine)


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email address."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, email: str, hashed_password: str) -> User:
    """Create a new user."""
    user = User(email=email, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_documents(db: Session, user_id: int) -> list[Document]:
    """Get all documents for a user."""
    return db.query(Document).filter(Document.user_id == user_id).all()


def get_document_by_id(db: Session, doc_id: int, user_id: int) -> Optional[Document]:
    """Get a specific document by ID, scoped to a user."""
    return (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == user_id)
        .first()
    )


def create_document(
    db: Session,
    user_id: int,
    filename: str,
    original_filename: str,
    file_path: str,
    vectorstore_path: Optional[str] = None,
    chunks_count: int = 0,
    file_size: Optional[int] = None,
) -> Document:
    """Create a new document record."""
    document = Document(
        user_id=user_id,
        filename=filename,
        original_filename=original_filename,
        file_path=file_path,
        vectorstore_path=vectorstore_path,
        chunks_count=chunks_count,
        file_size=file_size,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def delete_document(db: Session, doc_id: int, user_id: int) -> bool:
    """
    Delete a document. Returns True if deleted, False if not found.
    Only deletes if the document belongs to the user.
    """
    document = get_document_by_id(db, doc_id, user_id)
    if document:
        db.delete(document)
        db.commit()
        return True
    return False
