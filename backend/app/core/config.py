"""
Application configuration using Pydantic BaseSettings.
Loads environment variables from .env file.
"""

import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI API Configuration
    openai_api_key: str = ""
    
    # Database Configuration (PostgreSQL)
    database_url: str = ""
    
    # Force IPv4 for database connections (Windows fix)
    database_force_ipv4: bool = True
    
    # CORS Configuration
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://46.173.29.224:5173",
        "http://46.173.29.224:3000",
    ]
    
    # Application Settings
    app_name: str = "Tender AI Assistant"
    app_version: str = "2.0.0"
    
    # FAISS Index Path
    faiss_index_path: str = "faiss_index"
    
    # Data Directory
    data_dir: str = "backend/data"
    
    # JWT Settings
    access_token_expire_minutes: int = 30
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    
    # LLM Settings
    llm_model: str = "gpt-4o-mini"
    embeddings_model: str = "text-embedding-3-large"
    
    # Chunking Settings
    chunk_size: int = 1200
    chunk_overlap: int = 200
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use os.environ as fallback
        if not self.database_url:
            self.database_url = os.environ.get("DATABASE_URL", "")
        if not self.openai_api_key:
            self.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        print(f"[CONFIG] Settings loaded - DATABASE_URL: {self.database_url[:50] if self.database_url else 'EMPTY'}")
        if not self.database_url:
            print("[CONFIG] DATABASE_URL IS EMPTY!")


# Don't create settings at import time - create lazily
# settings = Settings()
_settings = None

def get_settings() -> Settings:
    """Get the application settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

# Lazy proxy for backwards compatibility
class _SettingsProxy:
    def __getattr__(self, name):
        return getattr(get_settings(), name)

settings = _SettingsProxy()


# CORS origins as list (for FastAPI)
CORS_ORIGINS = settings.cors_origins

# JWT Configuration
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
