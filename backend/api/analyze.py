import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_openai import ChatOpenAI
from rag.prompt import tender_prompt
import state

# Import AI service from new structure (if available)
AI_SERVICE_AVAILABLE = False
get_ai_service = None

try:
    import sys
    import os
    # Add project root to path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    from app.services.ai_service import get_ai_service
    from app.schemas.tender import TenderScoring, TenderDecision
    AI_SERVICE_AVAILABLE = True
except ImportError as e:
    print(f"[ANALYZE] Could not import AI service: {e}")
    AI_SERVICE_AVAILABLE = False
    get_ai_service = None

router = APIRouter()

ANALYZE_QUESTION = """
Сделай полный анализ тендерной документации и выведи:

1. Краткое описание закупки
2. Ключевые сроки
3. Обязательные документы
4. Требования к участнику
5. Финансовые условия
6. Основные риски дисквалификации
7. Чек-лист подготовки заявки (пошагово)
8. Оценка сложности тендера: simple / medium / complex

Ответ структурируй.
"""


@router.post("/analyze")
async def analyze():
    if not state.is_ready():
        raise HTTPException(
            status_code=400, detail="Сначала загрузите тендерный документ"
        )

    vs = state.get_vectorstore()
    docs = vs.similarity_search(ANALYZE_QUESTION, k=6)

    context = "\n".join(
        doc.page_content if hasattr(doc, "page_content") else str(doc) for doc in docs
    )

    prompt = tender_prompt.format(context=context, question=ANALYZE_QUESTION)

    async def generate():
        llm = ChatOpenAI(model="gpt-4o-mini", streaming=True)
        async for chunk in llm.astream(prompt):
            if chunk.content:
                yield f"data: {json.dumps({'token': chunk.content})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ============== Scoring Endpoint ==============

class TenderScoringResponse:
    """Response model for scoring."""
    def __init__(self, budget_score, complexity_score, competition_score, total_score, decision, reasoning, has_high_risks):
        self.budget_score = budget_score
        self.complexity_score = complexity_score
        self.competition_score = competition_score
        self.total_score = total_score
        self.decision = decision
        self.reasoning = reasoning
        self.has_high_risks = has_high_risks


@router.post("/analyze-with-scoring")
async def analyze_with_scoring():
    """
    Analyze tender with scoring and decision.
    
    Calculates:
    - budget_score (0-40): Budget and payment terms evaluation
    - complexity_score (0-30): Technical feasibility (higher = easier)
    - competition_score (0-30): Expected competition level (higher = less competition)
    
    Decision rules:
    - REJECT: total_score < 50
    - REVIEW: total_score >= 50 AND has High risks
    - GO: total_score >= 50 AND no High risks
    """
    if not state.is_ready():
        raise HTTPException(
            status_code=400, detail="Сначала загрузите тендерный документ"
        )
    
    if not get_ai_service:
        raise HTTPException(
            status_code=500, detail="AI Service не доступен. Проверьте конфигурацию."
        )
    
    try:
        # Get raw text from state
        text = state.get_raw_text() if hasattr(state, 'get_raw_text') else ""
        if not text:
            # Try to get from vectorstore documents
            vs = state.get_vectorstore()
            if vs:
                docs = vs.similarity_search("текст документа", k=1)
                text = "\n".join([d.page_content for d in docs])
        
        if not text:
            raise HTTPException(status_code=400, detail="Текст документа не найден")
        
        # Initialize AI service
        ai_service = get_ai_service()
        
        # 1. Get text for scoring
        # Use first 4000 chars for scoring
        scoring_text = text[:4000]
        
        # 2. Analyze risks first
        risks = await ai_service.analyze_risks(text)
        
        # 3. Calculate scoring components
        score_components = await ai_service.score_components(scoring_text)
        
        # 4. Calculate final decision
        scoring = await ai_service.calculate_decision(score_components, risks)
        
        return {
            "budget_score": scoring.budget_score,
            "complexity_score": scoring.complexity_score,
            "competition_score": scoring.competition_score,
            "total_score": scoring.total_score,
            "decision": scoring.decision.value,
            "reasoning": scoring.reasoning,
            "has_high_risks": scoring.has_high_risks
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")
