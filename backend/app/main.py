"""
Main application entry point.
Simplified version - only uses new app structure.
"""

import sys
import os

# Add project root to path so `rag` package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Load .env from project root (go up from backend/app/ to tender-ai-assistant/)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print(f"[APP] Loading .env from: {_PROJECT_ROOT}")
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))
print("[OK] .env loaded")

# Import configuration
from app.core.config import settings, CORS_ORIGINS

# Import database initialization
from app.core.database import engine, init_db

# Import API router
from app.api.endpoints.tenders import router as tenders_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: Create database tables
    await init_db()
    yield
    # Shutdown: Cleanup if needed


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(tenders_router, prefix="/api")


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": f"{settings.app_name} API v{settings.app_version}"}


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
