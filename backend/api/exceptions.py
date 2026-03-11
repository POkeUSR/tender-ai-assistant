"""
Кастомные исключения для приложения.
"""

from fastapi import HTTPException, status


class AppException(Exception):
    """Базовое исключение приложения."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class DocumentNotFoundError(AppException):
    """Документ не найден."""

    def __init__(self, doc_id: str = None):
        message = (
            f"Документ не найден" if doc_id is None else f"Документ {doc_id} не найден"
        )
        super().__init__(message, 404)


class DocumentNotReadyError(AppException):
    """Документ не готов к использованию."""

    def __init__(self, doc_id: str = None):
        message = (
            "Документ еще обрабатывается"
            if doc_id is None
            else f"Документ {doc_id} еще обрабатывается"
        )
        super().__init__(message, 400)


class UnauthorizedError(AppException):
    """Требуется авторизация."""

    def __init__(self, message: str = "Требуется авторизация"):
        super().__init__(message, 401)


class ForbiddenError(AppException):
    """Доступ запрещен."""

    def __init__(self, message: str = "Доступ запрещен"):
        super().__init__(message, 403)


class RateLimitError(AppException):
    """Превышен лимит запросов."""

    def __init__(self, message: str = "Превышен лимит запросов. Попробуйте позже."):
        super().__init__(message, 429)


class ValidationError(AppException):
    """Ошибка валидации."""

    def __init__(self, message: str):
        super().__init__(message, 400)


class ProcessingError(AppException):
    """Ошибка обработки документа."""

    def __init__(self, message: str = "Ошибка при обработке документа"):
        super().__init__(message, 500)


class LLMError(AppException):
    """Ошибка при работе с LLM."""

    def __init__(self, message: str = "Ошибка при генерации ответа"):
        super().__init__(message, 502)


def http_exception_from_app(exc: AppException) -> HTTPException:
    """Конвертировать AppException в HTTPException."""
    return HTTPException(status_code=exc.status_code, detail=exc.message)


# Словарь для маппинга исключений
EXCEPTION_HANDLERS = {
    DocumentNotFoundError: http_exception_from_app,
    DocumentNotReadyError: http_exception_from_app,
    UnauthorizedError: http_exception_from_app,
    ForbiddenError: http_exception_from_app,
    RateLimitError: http_exception_from_app,
    ValidationError: http_exception_from_app,
    ProcessingError: http_exception_from_app,
    LLMError: http_exception_from_app,
}
