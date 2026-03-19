"""
Tender API Endpoints.
Thin wrappers around TenderService - only handle request/response, not business logic.
Uses async database sessions.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.tender import (
    ChatRequest,
    UploadResponse,
    StatusResponse,
)
from app.services.tender_service import TenderService


# Create router
router = APIRouter()


# ============== Upload Endpoints ==============

@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
) -> UploadResponse:
    """
    Upload tender document files.
    
    Args:
        files: List of uploaded files
        db: AsyncSession for database operations
        
    Returns:
        Upload response with status and file info
        
    Raises:
        HTTPException: 400 if file format not supported, 500 if processing fails
    """
    try:
        service = TenderService(db)
        tender = await service.upload_files(files)
        return UploadResponse(
            status="ok",
            filenames=[tender.filename],
            chunks_count=len(tender.raw_text.split()) if tender.raw_text else 0
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Ошибка обработки файлов: {str(e)}"
        )


# ============== Status Endpoints ==============

@router.get("/status", response_model=StatusResponse)
async def get_status(db: AsyncSession = Depends(get_db)) -> StatusResponse:
    """
    Get current status of the tender document processing.
    
    Args:
        db: AsyncSession for database operations
        
    Returns:
        Status response with ready state and document info
    """
    service = TenderService(db)
    result = service.get_status()
    return StatusResponse(**result)


# ============== Chat Endpoints ==============

@router.post("/chat")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Chat with the tender document.
    
    Args:
        request: Chat request with question
        db: AsyncSession for database operations
        
    Returns:
        Streaming response with LLM-generated answer
    """
    try:
        service = TenderService(db)
        
        async def generate():
            async for chunk in service.chat(request.question):
                yield chunk
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============== Analysis Endpoints ==============

@router.post("/analyze")
async def analyze(db: AsyncSession = Depends(get_db)):
    """
    Analyze the tender document.
    
    Args:
        db: AsyncSession for database operations
        
    Returns:
        Streaming response with full analysis
    """
    try:
        service = TenderService(db)
        
        async def generate():
            async for chunk in service.analyze():
                yield chunk
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============== Risks Endpoints ==============

@router.post("/risks")
async def analyze_risks(db: AsyncSession = Depends(get_db)):
    """
    Analyze risks in the tender document.
    
    Args:
        db: AsyncSession for database operations
        
    Returns:
        Streaming response with risk analysis
    """
    try:
        service = TenderService(db)
        
        async def generate():
            async for chunk in service.analyze_risks():
                yield chunk
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
