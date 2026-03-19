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
    TenderScoring,
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


# ============== Scoring Endpoints ==============

@router.post("/analyze-with-scoring")
async def analyze_with_scoring(db: AsyncSession = Depends(get_db)):
    """
    Analyze the tender document with full scoring and decision.
    
    This endpoint performs:
    1. Risk analysis
    2. Scoring components calculation (budget, complexity, competition)
    3. Final decision based on rules:
       - REJECT: score < 50
       - REVIEW: score >= 50 AND has high risks
       - GO: score >= 50 AND no high risks
    
    Args:
        db: AsyncSession for database operations
        
    Returns:
        Complete analysis with scoring and decision
    """
    from app.services.ai_service import get_ai_service
    from app.models.models import Tender
    from sqlalchemy import select
    
    try:
        # Get text from database
        result = await db.execute(select(Tender).order_by(Tender.id.desc()).limit(1))
        tender = result.scalar_one_or_none()
        
        if not tender or not tender.raw_text:
            raise HTTPException(status_code=400, detail="Текст документа не найден")
        
        text = tender.raw_text
        
        # Initialize AI service
        ai_service = get_ai_service()
        
        # 1. Analyze risks
        risks = await ai_service.analyze_risks(text[:4000])
        
        # 2. Calculate scoring components
        score_components = await ai_service.score_components(text[:4000])
        
        # 3. Calculate final decision
        scoring = await ai_service.calculate_decision(score_components, risks)
        
        # Return result
        return {
            "budget_score": scoring.budget_score,
            "complexity_score": scoring.complexity_score,
            "competition_score": scoring.competition_score,
            "total_score": scoring.total_score,
            "decision": scoring.decision.value if hasattr(scoring.decision, 'value') else str(scoring.decision),
            "reasoning": scoring.reasoning,
            "has_high_risks": scoring.has_high_risks
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")
