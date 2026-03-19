"""
API Router - Combines all API route modules.
"""

from fastapi import APIRouter

from app.api.endpoints import tenders

# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(tenders.router, tags=["tenders"])

# Note: Auth and Documents endpoints are kept in the old structure
# They can be migrated later if needed
