"""
Authentication API endpoints.
Provides registration and login functionality.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field

from backend.database import get_db_sync, create_user, get_user_by_email
from backend.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    authenticate_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from sqlalchemy.orm import Session

router = APIRouter()


# Request/Response models

class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    password_confirm: str = Field(..., description="Password confirmation")


class UserResponse(BaseModel):
    """Schema for user response."""
    id: int
    email: str
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str


class MessageResponse(BaseModel):
    """Schema for simple message response."""
    message: str


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db_sync)):
    """
    Register a new user.
    
    Args:
        user_data: Registration data (email, password, password_confirm)
        db: Database session
    
    Returns:
        Created user information
    
    Raises:
        HTTPException: 400 if passwords don't match or email already exists
    """
    # Check password match
    if user_data.password != user_data.password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароли не совпадают"
        )
    
    # Check password strength
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароль должен содержать минимум 8 символов"
        )
    
    # Check if email already exists
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email уже зарегистрирован"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    user = create_user(
        db,
        email=user_data.email,
        hashed_password=hashed_password
    )
    
    return user


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db_sync)):
    """
    Login with email and password.
    Returns access and refresh tokens.
    
    Args:
        form_data: OAuth2 form with username (email) and password
        db: Database session
    
    Returns:
        Access and refresh tokens
    
    Raises:
        HTTPException: 401 if credentials are invalid
    """
    # Authenticate user
    user = authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_data: TokenRefreshRequest, db: Session = Depends(get_db_sync)):
    """
    Refresh access token using refresh token.
    
    Args:
        refresh_data: Refresh token
        db: Database session
    
    Returns:
        New access and refresh tokens
    
    Raises:
        HTTPException: 401 if refresh token is invalid
    """
    from backend.auth import decode_token
    
    payload = decode_token(refresh_data.refresh_token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или истёкший токен обновления"
        )
    
    token_type = payload.get("type")
    if token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный тип токена"
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен"
        )
    
    # Create new tokens
    access_token = create_access_token(
        data={"sub": user_id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_refresh_token(data={"sub": user_id})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout():
    """
    Logout endpoint.
    In a stateless JWT system, logout is handled client-side by removing the token.
    This endpoint can be used for logging purposes or token blacklisting (if implemented).
    
    Returns:
        Success message
    """
    return {"message": "Успешный выход из системы"}
