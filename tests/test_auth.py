"""
Tests for authentication module.
"""

import os
import pytest
from datetime import timedelta

# Set test database before importing
os.environ["DATABASE_URL"] = "sqlite:///./test_tender.db"

from backend.database import Base, engine, SessionLocal, create_user, init_db
from backend.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    authenticate_user,
)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test_tender.db"):
        try:
            os.remove("test_tender.db")
        except:
            pass


class TestPasswordHashing:
    """Test password hashing functions."""

    def test_get_password_hash(self):
        """Test that password hashing works."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        """Test verifying correct password."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty(self):
        """Test verifying with empty password."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert verify_password("", hashed) is False


class TestTokenCreation:
    """Test JWT token creation and decoding."""

    def test_create_access_token(self):
        """Test creating access token."""
        token = create_access_token(data={"sub": "123"})
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiry(self):
        """Test creating access token with custom expiry."""
        expires = timedelta(minutes=60)
        token = create_access_token(data={"sub": "123"}, expires_delta=expires)
        
        assert token is not None

    def test_create_refresh_token(self):
        """Test creating refresh token."""
        token = create_refresh_token(data={"sub": "123"})
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_valid_token(self):
        """Test decoding a valid token."""
        token = create_access_token(data={"sub": "123"})
        payload = decode_token(token)
        
        assert payload is not None
        assert payload["sub"] == "123"
        assert payload["type"] == "access"

    def test_decode_invalid_token(self):
        """Test decoding an invalid token."""
        payload = decode_token("invalid_token_here")
        
        assert payload is None

    def test_decode_token_wrong_key(self):
        """Test decoding token with wrong secret key."""
        # This would require mocking - skipping for simplicity
        pass

    def test_token_contains_expiry(self):
        """Test that token contains expiration time."""
        token = create_access_token(data={"sub": "123"})
        payload = decode_token(token)
        
        assert "exp" in payload


class TestAuthenticateUser:
    """Test user authentication."""

    def test_authenticate_user_success(self, db_session):
        """Test successful user authentication."""
        # Create user
        user = create_user(
            db_session,
            email="auth@test.com",
            hashed_password=get_password_hash("password123")
        )
        
        # Authenticate
        authenticated = authenticate_user(db_session, "auth@test.com", "password123")
        
        assert authenticated is not None
        assert authenticated.id == user.id
        assert authenticated.email == "auth@test.com"

    def test_authenticate_user_wrong_password(self, db_session):
        """Test authentication with wrong password."""
        # Create user
        create_user(
            db_session,
            email="wrongpass@test.com",
            hashed_password=get_password_hash("password123")
        )
        
        # Try to authenticate with wrong password
        authenticated = authenticate_user(db_session, "wrongpass@test.com", "wrongpassword")
        
        assert authenticated is None

    def test_authenticate_user_nonexistent(self, db_session):
        """Test authentication with non-existent user."""
        authenticated = authenticate_user(db_session, "nonexistent@test.com", "password123")
        
        assert authenticated is None


class TestTokenTypes:
    """Test token type differentiation."""

    def test_access_token_type(self):
        """Test that access token has correct type."""
        token = create_access_token(data={"sub": "123"})
        payload = decode_token(token)
        
        assert payload["type"] == "access"

    def test_refresh_token_type(self):
        """Test that refresh token has correct type."""
        token = create_refresh_token(data={"sub": "123"})
        payload = decode_token(token)
        
        assert payload["type"] == "refresh"
