"""
Общие функции для RAG операций.
Устраняет дублирование кода в chat.py, analyze.py, risks.py
"""
from typing import Optional, AsyncGenerator
import json
import logging
import state

logger = logging.getLogger(__name__)


async def get_vectorstore_for_request(
    user_id: Optional[str] = None,
    doc_id: Optional[str] = None
):
    """
    Получить vectorstore для запроса.
    
    Если user_id и doc_id переданы - используем пользовательский vectorstore.
    Иначе - используем глобальный (legacy режим для совместимости).
    """
    if user_id and doc_id:
        vs = state.get_user_vectorstore(user_id, doc_id)
        if vs is None:
            logger.warning(f"Vectorstore не найден для user={user_id}, doc={doc_id}")
            return None
        return vs
    else:
        # Legacy режим - глобальный vectorstore
        vs = state.get_vectorstore()
        if vs is None:
            logger.warning("Глобальный vectorstore не инициализирован")
        return vs


async def similarity_search_with_context(
    question: str,
    k: int = 4,
    user_id: Optional[str] = None,
    doc_id: Optional[str] = None
) -> str:
    """
    Унифицированная логика для similarity search.
    
    Args:
        question: Вопрос пользователя
        k: Количество документов для поиска
        user_id: ID пользователя (опционально)
        doc_id: ID документа (опционально)
    
    Returns:
        Контекст в виде строки
    """
    vs = await get_vectorstore_for_request(user_id, doc_id)
    
    if vs is None:
        raise ValueError("Документ не загружен. Сначала загрузите тендерный документ.")
    
    try:
        docs = vs.similarity_search(question, k=k)
    except Exception as e:
        logger.error(f"Ошибка при similarity_search: {e}")
        raise ValueError(f"Ошибка поиска по документу: {str(e)}")
    
    context = "\n".join(
        doc.page_content if hasattr(doc, "page_content") else str(doc)
        for doc in docs
    )
    
    logger.info(f"Найдено {len(docs)} релевантных фрагментов для вопроса: {question[:50]}...")
    
    return context


async def generate_streaming_response(
    prompt: str,
    model: str = "gpt-4o-mini"
) -> AsyncGenerator[str, None]:
    """
    Унифицированная генерация streaming ответа от LLM.
    
    Args:
        prompt: Промпт для LLM
        model: Модель LLM (по умолчанию gpt-4o-mini)
    
    Yields:
        SSE токены
    """
    from langchain_openai import ChatOpenAI
    
    llm = ChatOpenAI(model=model, streaming=True)
    
    try:
        async for chunk in llm.astream(prompt):
            if chunk.content:
                yield f"data: {json.dumps({'token': chunk.content})}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"Ошибка при генерации ответа: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


def check_document_ready(user_id: Optional[str] = None, doc_id: Optional[str] = None) -> tuple[bool, str]:
    """
    Проверить готовность документа для запроса.
    
    Returns:
        (is_ready, message)
    """
    if user_id and doc_id:
        vs = state.get_user_vectorstore(user_id, doc_id)
        if vs is None:
            return False, "Документ не найден или не проиндексирован"
        return True, ""
    else:
        if not state.is_ready():
            return False, "Сначала загрузите тендерный документ"
        return True, ""
