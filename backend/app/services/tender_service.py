"""
Tender Service - Business Logic Layer.
Handles PDF processing, OpenAI/LangChain calls, and FAISS vector store operations.
"""

import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import AsyncGenerator, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
from backend.state import get_raw_text

# Import models
from app.models.models import Tender, Score, Analysis

# Import schemas
from app.schemas.tender import TenderScoring


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
        state.set_vectorstore(vs, combined_name, len(chunks), text)

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
    
    # ============== Full Analysis with Scoring ==============
    
    async def analyze_with_scoring(self, tender_id: int) -> dict:
        """
        Perform full analysis of tender with scoring and decision.
        
        Args:
            tender_id: ID of the tender to analyze
            
        Returns:
            Dictionary with analysis, risks, and scoring results
        """
        from app.services.ai_service import get_ai_service
        
        if not state.is_ready():
            raise ValueError("Сначала загрузите тендерный документ")
        
        tender = await self.db.get(Tender, tender_id)
        if not tender:
            raise ValueError("Tender not found")
        
        # Get text from state or tender
        text = get_raw_text() or tender.raw_text
        if not text:
            raise ValueError("No text available for analysis")
        
        # Initialize AI service
        ai_service = get_ai_service()
        
        # 1. Extract data
        logger.info("Step 1: Extracting tender data...")
        data = await ai_service.extract_data(text)
        
        # 2. Analyze risks
        logger.info("Step 2: Analyzing risks...")
        risks = await ai_service.analyze_risks(text)
        
        # 3. Calculate scoring components
        logger.info("Step 3: Calculating scoring components...")
        score_components = await ai_service.score_components(text)
        
        # 4. Calculate final decision
        logger.info("Step 4: Calculating final decision...")
        scoring = await ai_service.calculate_decision(score_components, risks)
        
        # 5. Save analysis to database
        logger.info("Step 5: Saving results to database...")
        
        # Save analysis
        analysis = Analysis(
            tender_id=tender_id,
            summary=f"Budget: {data.budget} {data.currency}, Deadline: {data.deadline}",
            risks=risks.model_dump(mode='json') if risks else None
        )
        self.db.add(analysis)
        
        # Save scoring
        score_record = Score(
            tender_id=tender_id,
            budget_score=scoring.budget_score,
            complexity_score=scoring.complexity_score,
            competition_score=scoring.competition_score,
            total_score=scoring.total_score,
            decision=scoring.decision.value,
            reasoning=scoring.reasoning
        )
        self.db.add(score_record)
        
        # Update tender status
        tender.status = "analyzed"
        
        await self.db.commit()
        await self.db.refresh(analysis)
        await self.db.refresh(score_record)
        
        logger.info(f"Analysis complete: decision={scoring.decision.value}, total={scoring.total_score}")
        
        return {
            "tender_id": tender_id,
            "data": data.model_dump() if data else None,
            "risks": risks.model_dump(mode='json') if risks else None,
            "scoring": scoring.model_dump() if scoring else None,
            "analysis_id": analysis.id,
            "score_id": score_record.id
        }
    
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

