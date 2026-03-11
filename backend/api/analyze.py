import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_openai import ChatOpenAI
from rag.prompt import tender_prompt
import state

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
