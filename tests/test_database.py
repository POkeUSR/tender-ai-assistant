"""
Tests for database models and functions.
"""

import os
import tempfile
import pytest
from sqlalchemy import inspect

# Set test database before importing
os.environ["DATABASE_URL"] = "sqlite:///./test_tender.db"

from backend.database import (
    Base,
    User,
    Document,
    engine,
    SessionLocal,
    init_db,
    get_db,
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_documents,
    create_document,
    get_document_by_id,
    delete_document,
)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    session = SessionLocal()
    
    yield session
    
    # Cleanup
    session.close()
    Base.metadata.drop_all(bind=engine)
    
    # Remove test database file
    if os.path.exists("test_tender.db"):
        try:
            os.remove("test_tender.db")
        except:
            pass


class TestDatabaseInitialization:
    """Test database initialization."""

    def test_init_db_creates_tables(self):
        """Test that init_db creates all required tables."""
        # Drop all first
        Base.metadata.drop_all(bind=engine)
        
        # Initialize
        init_db()
        
        # Check tables exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        assert "users" in tables
        assert "documents" in tables


class TestUserModel:
    """Test User model."""

    def test_create_user(self, db_session):
        """Test creating a new user."""
        user = create_user(
            db_session,
            email="test@example.com",
            hashed_password="hashed_password_here"
        )
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.hashed_password == "hashed_password_here"
        assert user.created_at is not None

    def test_get_user_by_email(self, db_session):
        """Test getting user by email."""
        # Create user first
        create_user(db_session, email="findme@example.com", hashed_password="hash")
        
        # Find user
        user = get_user_by_email(db_session, "findme@example.com")
        
        assert user is not None
        assert user.email == "findme@example.com"

    def test_get_user_by_email_not_found(self, db_session):
        """Test getting non-existent user returns None."""
        user = get_user_by_email(db_session, "nonexistent@example.com")
        assert user is None

    def test_get_user_by_id(self, db_session):
        """Test getting user by ID."""
        # Create user
        created_user = create_user(db_session, email="byid@example.com", hashed_password="hash")
        
        # Find by ID
        user = get_user_by_id(db_session, created_user.id)
        
        assert user is not None
        assert user.id == created_user.id
        assert user.email == "byid@example.com"

    def test_user_repr(self, db_session):
        """Test User __repr__ method."""
        user = create_user(db_session, email="repr@example.com", hashed_password="hash")
        
        assert "User" in repr(user)
        assert "repr@example.com" in repr(user)


class TestDocumentModel:
    """Test Document model."""

    def test_create_document(self, db_session):
        """Test creating a new document."""
        # Create user first
        user = create_user(db_session, email="docuser@example.com", hashed_password="hash")
        
        # Create document
        doc = create_document(
            db_session,
            user_id=user.id,
            filename="uploaded_file.pdf",
            original_filename="original.pdf",
            file_path="/uploads/file.pdf",
            vectorstore_path="/faiss/user_1/doc_1",
            chunks_count=100,
            file_size=1024000
        )
        
        assert doc.id is not None
        assert doc.user_id == user.id
        assert doc.filename == "uploaded_file.pdf"
        assert doc.original_filename == "original.pdf"
        assert doc.chunks_count == 100
        assert doc.file_size == 1024000

    def test_get_user_documents(self, db_session):
        """Test getting all documents for a user."""
        # Create user
        user = create_user(db_session, email="multidoc@example.com", hashed_password="hash")
        
        # Create multiple documents
        create_document(db_session, user_id=user.id, filename="doc1.pdf", original_filename="doc1.pdf", file_path="/path1")
        create_document(db_session, user_id=user.id, filename="doc2.pdf", original_filename="doc2.pdf", file_path="/path2")
        
        # Get all documents
        docs = get_user_documents(db_session, user.id)
        
        assert len(docs) == 2

    def test_get_user_documents_empty(self, db_session):
        """Test getting documents for user with no documents."""
        user = create_user(db_session, email="nodocs@example.com", hashed_password="hash")
        
        docs = get_user_documents(db_session, user.id)
        
        assert len(docs) == 0

    def test_get_document_by_id(self, db_session):
        """Test getting a specific document."""
        # Create user and document
        user = create_user(db_session, email="specific@example.com", hashed_password="hash")
        doc = create_document(db_session, user_id=user.id, filename="specific.pdf", original_filename="specific.pdf", file_path="/specific")
        
        # Get by ID
        found_doc = get_document_by_id(db_session, doc.id, user.id)
        
        assert found_doc is not None
        assert found_doc.id == doc.id

    def test_get_document_by_id_wrong_user(self, db_session):
        """Test that getting document with wrong user_id returns None."""
        # Create two users
        user1 = create_user(db_session, email="user1@example.com", hashed_password="hash")
        user2 = create_user(db_session, email="user2@example.com", hashed_password="hash")
        
        # Create document for user1
        doc = create_document(db_session, user_id=user1.id, filename="user1_doc.pdf", original_filename="user1_doc.pdf", file_path="/path")
        
        # Try to get with user2's ID
        found_doc = get_document_by_id(db_session, doc.id, user2.id)
        
        assert found_doc is None

    def test_delete_document(self, db_session):
        """Test deleting a document."""
        # Create user and document
        user = create_user(db_session, email="delete@example.com", hashed_password="hash")
        doc = create_document(db_session, user_id=user.id, filename="delete.pdf", original_filename="delete.pdf", file_path="/delete")
        doc_id = doc.id
        
        # Delete
        result = delete_document(db_session, doc_id, user.id)
        
        assert result is True
        
        # Verify deleted
        assert get_document_by_id(db_session, doc_id, user.id) is None

    def test_delete_document_not_found(self, db_session):
        """Test deleting non-existent document returns False."""
        user = create_user(db_session, email="deletenotfound@example.com", hashed_password="hash")
        
        result = delete_document(db_session, 99999, user.id)
        
        assert result is False


class TestDocumentRelationships:
    """Test relationships between User and Document."""

    def test_user_documents_relationship(self, db_session):
        """Test that user.documents relationship works."""
        # Create user with documents
        user = create_user(db_session, email="rel@example.com", hashed_password="hash")
        create_document(db_session, user_id=user.id, filename="doc1.pdf", original_filename="doc1.pdf", file_path="/path1")
        create_document(db_session, user_id=user.id, filename="doc2.pdf", original_filename="doc2.pdf", file_path="/path2")
        
        # Refresh to get relationship data
        db_session.refresh(user)
        
        assert len(user.documents) == 2

    def test_document_user_relationship(self, db_session):
        """Test that document.user relationship works."""
        # Create user and document
        user = create_user(db_session, email="docrel@example.com", hashed_password="hash")
        doc = create_document(db_session, user_id=user.id, filename="doc.pdf", original_filename="doc.pdf", file_path="/path")
        
        # Refresh to get relationship
        db_session.refresh(doc)
        
        assert doc.user is not None
        assert doc.user.id == user.id
        assert doc.user.email == "docrel@example.com"
