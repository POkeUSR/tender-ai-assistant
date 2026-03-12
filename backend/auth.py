"""
Authentication module for Tender AI Assistant.
Provides JWT token-based authentication with password hashing.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.database import get_db, User, get_user_by_id

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: The plain text password to verify
        hashed_password: The hashed password to compare against
    
    Returns:
        True if the password matches, False otherwise
    """
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: The plain text password to hash
    
    Returns:
        The hashed password
    """
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: The data to encode in the token (typically {"sub": user_id})
        expires_delta: Optional custom expiration time
    
    Returns:
        The encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token with longer expiration.
    
    Args:
        data: The data to encode in the token (typically {"sub": user_id})
    
    Returns:
        The encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT token to decode
    
    Returns:
        The decoded payload if valid, None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token.
    This is a FastAPI dependency that can be used to protect routes.
    
    Args:
        token: JWT token from Authorization header
        db: Database session
    
    Returns:
        The authenticated User
    
    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Неверный токен аутентификации",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token)
    
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    token_type: str = payload.get("type")
    
    if user_id is None:
        raise credentials_exception
    
    # Only accept access tokens
    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверльный тип токена",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = get_user_by_id(db, int(user_id))
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get the current user if authenticated, None otherwise.
    Useful for optional authentication.
    
    Args:
        token: Optional JWT token from Authorization header
        db: Database session
    
    Returns:
        The User if authenticated, None otherwise
    """
    if token is None:
        return None
    
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate a user with email and password.
    
    Args:
        db: Database session
        email: User's email
        password: User's plain text password
    
    Returns:
        The User if authentication successful, None otherwise
    """
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user
