"""
Pydantic schemas for Tender API.
Contains all request and response models.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# ============== Enum Definitions ==============

class RiskLevel(str, Enum):
    """Risk level enumeration for structured output."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class TenderDecision(str, Enum):
    """Tender decision enumeration."""
    GO = "GO"
    NO_GO = "NO GO"


# ============== OpenAI Structured Output Schemas ==============

class TenderDataExtraction(BaseModel):
    """Schema for extracting structured data from tender documents.
    Used for OpenAI Structured Output to parse tender information."""
    
    title: str = Field(
        ...,
        description="Название тендера или закупки"
    )
    budget: float = Field(
        ...,
        description="Бюджет тендера в числовом формате (например, 1000000.00)"
    )
    currency: str = Field(
        ...,
        description="Валюта бюджета (RUB, USD, EUR и т.д.)"
    )
    deadline: str = Field(
        ...,
        description="Срок подачи заявки или deadline в читаемом формате"
    )
    requirements: List[str] = Field(
        ...,
        description="Список основных требований к участнику тендера"
    )
    delivery_place: str = Field(
        ...,
        description="Место поставки товара/оказания услуг"
    )


class RiskItem(BaseModel):
    """Schema for individual risk item.
    Used for OpenAI Structured Output to format risk analysis."""
    
    category: str = Field(
        ...,
        description="Категория риска (например: Финансовый, Технический, Правовой, Операционный)"
    )
    description: str = Field(
        ...,
        description="Подробное описание риска"
    )
    level: RiskLevel = Field(
        ...,
        description="Уровень риска: High (высокий), Medium (средний), Low (низкий)"
    )
    mitigation: str = Field(
        ...,
        description="Рекомендации по митигации или снижению риска"
    )


class TenderRisks(BaseModel):
    """Schema for complete risk analysis result.
    Used for OpenAI Structured Output to return full risk assessment."""
    
    risks: List[RiskItem] = Field(
        ...,
        description="Список всех выявленных рисков"
    )
    overall_risk_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Общая оценка риска от 0 до 100 (0 - минимальный риск, 100 - максимальный)"
    )


class TenderScore(BaseModel):
    """Schema for tender scoring result.
    Used for OpenAI Structured Output to evaluate tender viability."""
    
    score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Общая оценка тендера от 0 до 100"
    )
    pros: List[str] = Field(
        ...,
        description="Список преимуществ участия в тендере"
    )
    cons: List[str] = Field(
        ...,
        description="Список недостатков или сложностей"
    )
    decision: TenderDecision = Field(
        ...,
        description="Решение: GO (рекомендуется участвовать) или NO GO (не рекомендуется)"
    )


class TenderProposal(BaseModel):
    """Schema for tender proposal generation.
    Used for OpenAI Structured Output to generate proposal text."""
    
    proposal_text: str = Field(
        ...,
        description="Сгенерированный текст предложения/заявки"
    )
    missing_info: List[str] = Field(
        ...,
        description="Список информации, которую необходимо добавить в предложение"
    )


# ============== Tender Document Schemas ==============

class UploadResponse(BaseModel):
    """Response schema for file upload."""
    status: str = "ok"
    filenames: List[str]
    chunks_count: int


class StatusResponse(BaseModel):
    """Response schema for status check."""
    ready: bool
    filename: Optional[str] = None
    chunks_count: Optional[int] = None


# ============== Chat Schemas ==============

class ChatRequest(BaseModel):
    """Request schema for chat endpoint."""
    question: str


# ============== Analysis Schemas ==============

# Analysis question constant (moved from api/analyze.py)
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


# ============== Risks Schemas ==============

# Risks question constant (moved from api/risks.py)
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


# ============== Document Management Schemas ==============

class DocumentResponse(BaseModel):
    """Schema for document response."""
    id: int
    filename: str
    original_filename: str
    chunks_count: int
    file_size: Optional[int] = None
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


class ClearCacheResponse(BaseModel):
    """Schema for clear cache response."""
    status: str = "ok"
    message: str


# ============== Auth Schemas ==============

class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    password_confirm: str = Field(..., description="Password confirmation")


class UserResponse(BaseModel):
    """Schema for user response."""
    id: int
    email: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str


class MessageResponse(BaseModel):
    """Schema for simple message response."""
    message: str
