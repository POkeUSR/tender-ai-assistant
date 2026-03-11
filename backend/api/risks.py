import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_openai import ChatOpenAI
from rag.prompt import tender_prompt
import state

router = APIRouter()

RISKS_QUESTION = """
Проанализируй тендерную документацию и выяви все возможные риски для участника тендера.

Структурируй ответ по следующим категориям:

1. **Риски дисквалификации заявки**
   - Отсутствие обязательных документов
   - Нарушение сроков подачи
   - Несоответствие формату заявки

2. **Финансовые риски**
   - Обеспечение заявки и исполнения контракта
   - Штрафы и пени
   - Условия оплаты

3. **Технические риски**
   - Сложность выполнения требований
   - Специфические квалификационные требования
   - Лицензии и сертификаты

4. **Правовые риски**
   - Спорные условия контракта
   - Ответственность сторон
   - Условия расторжения

5. **Операционные риски**
   - Сжатые сроки выполнения
   - Пропускные условия

Для каждого риска укажи: описание, уровень (высокий/средний/низкий), рекомендацию.
"""


@router.post("/risks")
async def risks():
    if not state.is_ready():
        raise HTTPException(
            status_code=400, detail="Сначала загрузите тендерный документ"
        )

    vs = state.get_vectorstore()
    docs = vs.similarity_search(RISKS_QUESTION, k=6)

    context = "\n".join(
        doc.page_content if hasattr(doc, "page_content") else str(doc) for doc in docs
    )

    prompt = tender_prompt.format(context=context, question=RISKS_QUESTION)

    async def generate():
        llm = ChatOpenAI(model="gpt-4o-mini", streaming=True)
        async for chunk in llm.astream(prompt):
            if chunk.content:
                yield f"data: {json.dumps({'token': chunk.content})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
