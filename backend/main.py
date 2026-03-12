import sys
import os

# Add project root (c:/tender) to path so `rag` package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load .env from project root (c:/tender/.env)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.upload import router as upload_router
from api.chat import router as chat_router
from api.analyze import router as analyze_router
from api.risks import router as risks_router
from api.status import router as status_router
from api.auth import router as auth_router
from backend.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: Initialize database
    init_db()
    yield
    # Shutdown: Cleanup if needed


app = FastAPI(title="Tender AI Assistant", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://46.173.29.224:5173",
        "http://46.173.29.224:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(analyze_router, prefix="/api")
app.include_router(risks_router, prefix="/api")
app.include_router(status_router, prefix="/api")
app.include_router(auth_router, prefix="/api/auth")


@app.get("/")
def root():
    return {"message": "Tender AI Assistant API v2.0"}
