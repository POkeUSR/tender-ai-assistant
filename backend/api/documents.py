"""
Documents API endpoints.
Provides CRUD operations for user documents.
"""

import os
import shutil
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.database import get_db, get_user_documents, get_document_by_id, delete_document as db_delete_document
from backend.auth import get_current_user
from backend import state  # noqa: ERA001 - legacy import pattern

router = APIRouter()


# Response models

class DocumentResponse(BaseModel):
    """Schema for document response."""
    id: int
    filename: str
    original_filename: str
    chunks_count: int
    file_size: int | None
    created_at: datetime
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Schema for document list response."""
    documents: List[DocumentResponse]
    total: int


class DeleteResponse(BaseModel):
    """Schema for delete response."""
    status: str = "ok"
    message: str = "Документ успешно удалён"


class ErrorResponse(BaseModel):
    """Schema for error response."""
    detail: str


# Helper function for cleanup
def cleanup_files(file_path: str | None, vectorstore_path: str | None) -> None:
    """Clean up document files."""
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass
    
    if vectorstore_path and os.path.exists(vectorstore_path):
        try:
            shutil.rmtree(vectorstore_path)
        except OSError:
            pass


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DocumentListResponse:
    """
    Get list of documents for the current user.
    
    Returns:
        List of user's documents
    """
    documents = get_user_documents(db, current_user.id)
    
    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                original_filename=doc.original_filename,
                chunks_count=doc.chunks_count,
                file_size=doc.file_size,
                created_at=doc.created_at,
            )
            for doc in documents
        ],
        total=len(documents)
    )


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DocumentResponse:
    """
    Get a specific document by ID.
    
    Args:
        doc_id: Document ID
        
    Returns:
        Document details
        
    Raises:
        HTTPException: 404 if document not found
    """
    document = get_document_by_id(db, doc_id, current_user.id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден"
        )
    
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        original_filename=document.original_filename,
        chunks_count=document.chunks_count,
        file_size=document.file_size,
        created_at=document.created_at,
    )


@router.delete("/documents/{doc_id}", response_model=DeleteResponse)
async def delete_document(
    doc_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DeleteResponse:
    """
    Delete a document.
    
    Args:
        doc_id: Document ID
        
    Returns:
        Success message
        
    Raises:
        HTTPException: 404 if document not found
    """
    document = get_document_by_id(db, doc_id, current_user.id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден"
        )
    
    # Clean up files
    cleanup_files(document.file_path, document.vectorstore_path)
    
    # Clear from memory
    state.delete_user_vectorstore(str(current_user.id), str(doc_id))
    
    # Delete from database
    db_delete_document(db, doc_id, current_user.id)
    
    return DeleteResponse(
        status="ok",
        message="Документ успешно удалён"
    )


@router.post("/documents/{doc_id}/clear-cache")
async def clear_document_cache(
    doc_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Clear vectorstore cache for a document (frees memory).
    
    Args:
        doc_id: Document ID
        
    Returns:
        Success message
        
    Raises:
        HTTPException: 404 if document not found
    """
    document = get_document_by_id(db, doc_id, current_user.id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден"
        )
    
    # Clear from memory only
    deleted = state.delete_user_vectorstore(str(current_user.id), str(doc_id))
    
    return {
        "status": "ok",
        "message": "Кэш документа очищен" if deleted else "Кэш не был загружен"
    }
