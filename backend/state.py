"""Global application state — shared vectorstore across all routes."""

from typing import Optional

vectorstore = None
current_filename: Optional[str] = None
chunks_count: int = 0


def set_vectorstore(vs, filename: str, n_chunks: int):
    global vectorstore, current_filename, chunks_count
    vectorstore = vs
    current_filename = filename
    chunks_count = n_chunks


def get_vectorstore():
    return vectorstore


def is_ready() -> bool:
    return vectorstore is not None


def get_user_vectorstore(user_id: str, doc_id: str):
    """
    Получить vectorstore для конкретного пользователя и документа.
    
    TODO: Реализовать хранение vectorstore для каждого пользователя/документа.
    Пока возвращает None (используется глобальный vectorstore).
    """
    # Для будущей реализации мульти-пользовательского режима
    # Здесь будет логика для получения user-specific vectorstore
    return None
