"""
Tender Service - Business Logic Layer.
Handles PDF processing, OpenAI/LangChain calls, and FAISS vector store operations.
"""

import json
import os
import shutil
import sys
from pathlib import Path
from typing import AsyncGenerator, List, Optional

# Add project root to path for imports (go up 4 levels: services -> app -> backend -> project_root)
_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from fastapi import UploadFile
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.ext.asyncio import AsyncSession

# Import from app core
from app.core.file_handler import load_files, SUPPORTED_EXTENSIONS
from app.core.config import settings
from app.core.prompt import tender_prompt, ANALYZE_QUESTION, RISKS_QUESTION

# Import state
from backend import state

# Import models
from app.models.models import Tender


class TenderService:
    """
    Service class for handling tender document processing and analysis.
    Contains all business logic for PDF processing, LLM calls, and vector store operations.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize TenderService with database session.
        
        Args:
            db: AsyncSession for database operations
        """
        self.db = db
        self._upload_dir = settings.data_dir
        os.makedirs(self._upload_dir, exist_ok=True)
    
    # ============== Document Upload Methods ==============
    
    async def upload_files(self, files: List[UploadFile]) -> Tender:
        """
        Upload and process tender document files.
        Saves file to disk, extracts text, creates vector store,
        and stores tender record in database.
        
        Args:
            files: List of uploaded files
            
        Returns:
            Created Tender object with ID
            
        Raises:
            ValueError: If file format not supported
        """
        saved_paths = []
        filenames = []

        for file in files:
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                raise ValueError(
                    f"Файл '{file.filename}': неподдерживаемый формат '{ext}'. "
                    f"Поддерживаются: {', '.join(SUPPORTED_EXTENSIONS)}"
                )
            file_path = os.path.join(self._upload_dir, file.filename)
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            saved_paths.append(file_path)
            filenames.append(file.filename)

        # Process files
        text = load_files(saved_paths)
        chunks = self._split_text(text)
        vs = self._create_vectorstore(chunks)
        
        combined_name = ", ".join(filenames)
        state.set_vectorstore(vs, combined_name, len(chunks))

        # Save tender to database
        tender = Tender(
            filename=combined_name,
            raw_text=text,
            status="uploaded"
        )
        self.db.add(tender)
        await self.db.commit()
        await self.db.refresh(tender)

        return tender
    
    # ============== Chat Methods ==============
    
    async def chat(self, question: str) -> AsyncGenerator[str, None]:
        """
        Process a chat question about the tender document.
        
        Args:
            question: User question
            
        Yields:
            Streaming response tokens
        """
        if not state.is_ready():
            raise ValueError("Сначала загрузите тендерный документ")

        vs = state.get_vectorstore()
        docs = vs.similarity_search(question, k=4)

        context = "\n".join(
            doc.page_content if hasattr(doc, "page_content") else str(doc) for doc in docs
        )

        prompt = tender_prompt.format(context=context, question=question)

        async for chunk in self._stream_llm(prompt):
            yield chunk
    
    # ============== Analysis Methods ==============
    
    async def analyze(self) -> AsyncGenerator[str, None]:
        """
        Perform full analysis of the tender document.
        
        Yields:
            Streaming response tokens
        """
        if not state.is_ready():
            raise ValueError("Сначала загрузите тендерный документ")

        vs = state.get_vectorstore()
        docs = vs.similarity_search(ANALYZE_QUESTION, k=6)

        context = "\n".join(
            doc.page_content if hasattr(doc, "page_content") else str(doc) for doc in docs
        )

        prompt = tender_prompt.format(context=context, question=ANALYZE_QUESTION)

        async for chunk in self._stream_llm(prompt):
            yield chunk
    
    # ============== Risks Analysis Methods ==============
    
    async def analyze_risks(self) -> AsyncGenerator[str, None]:
        """
        Analyze risks in the tender document.
        
        Yields:
            Streaming response tokens
        """
        if not state.is_ready():
            raise ValueError("Сначала загрузите тендерный документ")

        vs = state.get_vectorstore()
        docs = vs.similarity_search(RISKS_QUESTION, k=6)

        context = "\n".join(
            doc.page_content if hasattr(doc, "page_content") else str(doc) for doc in docs
        )

        prompt = tender_prompt.format(context=context, question=RISKS_QUESTION)

        async for chunk in self._stream_llm(prompt):
            yield chunk
    
    # ============== Status Methods ==============
    
    def get_status(self) -> dict:
        """
        Get current status of the vector store.
        
        Returns:
            Dictionary with ready status, filename, and chunks count
        """
        if not state.is_ready():
            return {
                "ready": False,
                "filename": None,
                "chunks_count": None,
            }
        
        return {
            "ready": True,
            "filename": state.get_legacy_filename(),
            "chunks_count": state.get_legacy_chunks_count(),
        }
    
    # ============== Private Helper Methods ==============
    
    def _split_text(self, text: str) -> List[str]:
        """
        Split text into chunks.
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
        return splitter.split_text(text)
    
    def _create_vectorstore(self, chunks: List[str]) -> FAISS:
        """
        Create FAISS vector store from text chunks.
        
        Args:
            chunks: List of text chunks
            
        Returns:
            FAISS vector store
        """
        embeddings = OpenAIEmbeddings(model=settings.embeddings_model)
        db = FAISS.from_texts(chunks, embeddings)
        return db
    
    async def _stream_llm(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Stream LLM response.
        
        Args:
            prompt: Prompt to send to LLM
            
        Yields:
            Streaming response tokens
        """
        llm = ChatOpenAI(
            model=settings.llm_model,
            streaming=True
        )
        async for chunk in llm.astream(prompt):
            if chunk.content:
                yield f"data: {json.dumps({'token': chunk.content})}\n\n"
        yield "data: [DONE]\n\n"

