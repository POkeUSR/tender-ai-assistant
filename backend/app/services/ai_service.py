"""
AI Service - OpenAI integration for tender analysis.
Provides methods for data extraction, risk analysis, scoring, and proposal generation.
Uses langchain-openai with structured output for guaranteed JSON responses.
"""

import logging
from typing import Optional

from langchain_openai import ChatOpenAI

from app.core.config import get_settings
from app.schemas.tender import (
    TenderDataExtraction,
    TenderRisks,
    TenderScore,
    TenderScoreComponents,
    TenderScoring,
    TenderProposal,
    TenderDecision,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIService:
    """
    Service class for AI-powered tender analysis.
    Uses OpenAI with structured output for guaranteed JSON responses.
    """
    
    def __init__(self):
        """Initialize AI service with langchain OpenAI client."""
        self._setup_openai()
    
    def _setup_openai(self):
        """Setup langchain OpenAI client with structured output support."""
        try:
            settings = get_settings()
            
            # Initialize langchain ChatOpenAI
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=settings.openai_api_key,
                temperature=0.1,
                streaming=False,
            )
            
            # Create structured output chains
            self._setup_structured_chains()
            
            logger.info("AI: LangChain ChatOpenAI клиент инициализирован")
            logger.info("AI: Модель: gpt-4o-mini")
            
        except Exception as e:
            logger.error(f"AI: Ошибка инициализации OpenAI: {e}")
            self.llm = None
            self._extract_chain = None
            self._risks_chain = None
            self._score_chain = None
            self._proposal_chain = None
    
    def _setup_structured_chains(self):
        """Setup structured output chains using .with_structured_output()"""
        try:
            # Chain for data extraction
            self._extract_chain = self.llm.with_structured_output(TenderDataExtraction)
            
            # Chain for risk analysis
            self._risks_chain = self.llm.with_structured_output(TenderRisks)
            
            # Chain for scoring
            self._score_chain = self.llm.with_structured_output(TenderScore)
            
            # Chain for proposal generation
            self._proposal_chain = self.llm.with_structured_output(TenderProposal)
            
            logger.info("AI: Structured output цепи инициализированы")
            
        except Exception as e:
            logger.error(f"AI: Ошибка создания structured output цепей: {e}")
            self._extract_chain = None
            self._risks_chain = None
            self._score_chain = None
            self._proposal_chain = None
    
    async def extract_data(self, text: str) -> TenderDataExtraction:
        """
        Extract structured data from tender document.
        
        Args:
            text: Raw tender document text
            
        Returns:
            TenderDataExtraction with extracted information
        """
        logger.info("AI: Начинаю извлечение данных из тендера...")
        
        if not self._extract_chain:
            logger.warning("AI: Цепь извлечения не инициализирована")
            return TenderDataExtraction(
                title="",
                budget=0.0,
                currency="RUB",
                deadline="",
                requirements=[],
                delivery_place=""
            )
        
        prompt = f"""
Ты эксперт по государственным закупкам. Извлеки структурированные данные из тендерного документа.

Извлеки следующие поля:
- title: Название закупки или тендера
- budget: Бюджет в числовом формате (только число, без валюты)
- currency: Валюта бюджета (RUB, USD, EUR и т.д.)
- deadline: Срок подачи заявки в читаемом формате
- requirements: Список ключевых требований к участникам
- delivery_place: Место поставки товара/оказания услуг

Тендерный документ:
{text[:4000]}

Внимательно проанализируй документ и извлеки все данные.
"""
        
        try:
            result = await self._extract_chain.ainvoke(prompt)
            logger.info(f"AI: Данные извлечены - title: {result.title}, budget: {result.budget}")
            return result
            
        except Exception as e:
            logger.error(f"AI: Ошибка при извлечении данных: {e}")
            return TenderDataExtraction(
                title="",
                budget=0.0,
                currency="RUB",
                deadline="",
                requirements=[],
                delivery_place=""
            )
    
    async def analyze_risks(self, text: str) -> TenderRisks:
        """
        Analyze risks in tender document.
        
        Args:
            text: Raw tender document text
            
        Returns:
            TenderRisks with identified risks
        """
        logger.info("AI: Начинаю анализ рисков тендера...")
        
        if not self._risks_chain:
            logger.warning("AI: Цепь анализа рисков не инициализирована")
            return TenderRisks(
                risks=[],
                overall_risk_score=0
            )
        
        prompt = f"""
Ты эксперт по государственным закупкам. Проанализируй риски в тендерном документе.

Для каждого риска определи:
- category: Категория риска (Финансовый, Технический, Правовой, Операционный, Риск дисквалификации)
- description: Подробное описание риска
- level: Уровень риска (High, Medium или Low)
- mitigation: Рекомендации по снижению или митигации риска

Также рассчитай общую оценку риска (overall_risk_score) от 0 до 100:
- 0-30: Низкий общий риск
- 31-60: Средний общий риск
- 61-100: Высокий общий риск

Тендерный документ:
{text[:4000]}

Внимательно проанализируй все риски.
"""
        
        try:
            result = await self._risks_chain.ainvoke(prompt)
            logger.info(f"AI: Анализ рисков завершен - найдено рисков: {len(result.risks)}, score: {result.overall_risk_score}")
            return result
            
        except Exception as e:
            logger.error(f"AI: Ошибка при анализе рисков: {e}")
            return TenderRisks(
                risks=[],
                overall_risk_score=0
            )
    
    async def score_components(self, text: str) -> TenderScoreComponents:
        """
        Calculate scoring components for tender using 3-component scoring.
        
        Args:
            text: Raw tender document text
            
        Returns:
            TenderScoreComponents with budget, complexity, competition scores
        """
        logger.info("AI: Начинаю расчет компонентов оценки тендера...")
        
        # Create a temporary chain for score components if not available
        score_comp_chain = self.llm.with_structured_output(TenderScoreComponents)
        
        prompt = f"""
Ты эксперт по государственным закупкам. Оцени привлекательность тендера по трем компонентам.

Тендерный документ:
{text[:4000]}

Оцени по следующей системе:

1. BUDGET SCORE (0-40 баллов):
- Оцени условия оплаты и бюджет
- 40: Отличные условия (аванс 50%+, своевременная оплата)
- 30: Хорошие условия (аванс 30%, стандартные сроки)
- 20: Средние условия (минимальный аванс, длительные сроки оплаты)
- 10: Плохие условия (без аванса, очень длительные сроки)
- 0: Критические условия

2. COMPLEXITY SCORE (0-30 баллов):
- Оцени техническую сложность выполнения
- 30: Простой тендер, минимальные требования
- 20: Средняя сложность, стандартные требования
- 10: Высокая сложность, специфические требования
- 0: Очень сложный тендер

3. COMPETITION SCORE (0-30 баллов):
- Оцени ожидаемый уровень конкуренции
- 30: Нишевой тендер, мало конкурентов
- 20: Средняя конкуренция
- 10: Высокая конкуренция
- 0: Очень конкурентный тендер

Верни структурированный ответ с тремя оценками и кратким обоснованием.
"""
        
        try:
            result = await score_comp_chain.ainvoke(prompt)
            logger.info(f"AI: Компоненты оценки рассчитаны - budget: {result.budget_score}, complexity: {result.complexity_score}, competition: {result.competition_score}")
            return result
            
        except Exception as e:
            logger.error(f"AI: Ошибка при расчете компонентов оценки: {e}")
            return TenderScoreComponents(
                budget_score=0,
                complexity_score=0,
                competition_score=0,
                reasoning="Ошибка расчета оценки"
            )
    
    async def calculate_decision(
        self,
        score_components: TenderScoreComponents,
        risks: TenderRisks
    ) -> TenderScoring:
        """
        Calculate final decision based on scores and risk analysis.
        
        Decision Rules:
        - REJECT: If total_score < 50
        - REVIEW: If total_score >= 50 BUT has at least one "High" risk
        - GO: If total_score >= 50 and no "High" risks
        
        Args:
            score_components: Three component scores from AI
            risks: Risk analysis results
            
        Returns:
            TenderScoring with final decision
        """
        logger.info("AI: Рассчитываю финальное решение...")
        
        # Calculate total score (sum of all components)
        total_score = (
            score_components.budget_score +
            score_components.complexity_score +
            score_components.competition_score
        )
        
        # Check for high risks
        has_high_risks = any(risk.level.value == "High" for risk in risks.risks)
        
        # Apply decision rules
        if total_score < 50:
            decision = TenderDecision.REJECT
            reasoning = f"Низкая итоговая оценка ({total_score}/100). Тендер не рекомендуется к участию."
        elif has_high_risks:
            decision = TenderDecision.REVIEW
            high_risk_count = sum(1 for r in risks.risks if r.level.value == "High")
            reasoning = f"Высокие риски обнаружены ({high_risk_count} шт.). Требуется дополнительная проверка перед принятием решения."
        else:
            decision = TenderDecision.GO
            reasoning = f"Итоговая оценка {total_score}/100. Риски в пределах нормы. Рекомендуется участвовать."
        
        logger.info(f"AI: Решение принято - total: {total_score}, decision: {decision}, high_risks: {has_high_risks}")
        
        return TenderScoring(
            budget_score=score_components.budget_score,
            complexity_score=score_components.complexity_score,
            competition_score=score_components.competition_score,
            total_score=total_score,
            decision=decision,
            reasoning=reasoning,
            has_high_risks=has_high_risks
        )
    
    async def score(self, data: TenderDataExtraction, risks: TenderRisks) -> TenderScore:
        """
        Calculate suitability score for tender.
        
        Args:
            data: Extracted tender data
            risks: Risk analysis results
            
        Returns:
            TenderScore with score and decision
        """
        logger.info("AI: Начинаю расчет оценки тендера...")
        
        if not self._score_chain:
            logger.warning("AI: Цепь оценки не инициализирована")
            return TenderScore(
                score=0,
                pros=[],
                cons=[],
                decision=TenderDecision.REJECT
            )
        
        prompt = f"""
Ты эксперт по государственным закупкам. Оцени привлекательность тендера для участия.

Данные тендера:
- Название: {data.title}
- Бюджет: {data.budget} {data.currency}
- Срок подачи: {data.deadline}
- Место поставки: {data.delivery_place}
- Требования: {', '.join(data.requirements)}

Риски:
- Общая оценка риска: {risks.overall_risk_score}/100
- Количество рисков: {len(risks.risks)}

Оцени по шкале 0-100:
- 0-30: Не рекомендуется участвовать
- 31-60: Средняя привлекательность
- 61-100: Высокая привлекательность

Определи:
- score: Оценка от 0 до 100
- pros: Список преимуществ участия в тендере
- cons: Список недостатков или сложностей
- decision: GO (рекомендуется участвовать), REVIEW (проверить риски) или REJECT (отклонить)

Учитывай бюджет, сроки, требования и риски.
"""
        
        try:
            result = await self._score_chain.ainvoke(prompt)
            logger.info(f"AI: Оценка рассчитана - score: {result.score}, decision: {result.decision}")
            return result
            
        except Exception as e:
            logger.error(f"AI: Ошибка при расчете оценки: {e}")
            return TenderScore(
                score=0,
                pros=[],
                cons=[],
                decision=TenderDecision.REJECT
            )
    
    async def generate_proposal(self, data: TenderDataExtraction) -> TenderProposal:
        """
        Generate proposal text for tender.
        
        Args:
            data: Extracted tender data
            
        Returns:
            TenderProposal with generated text
        """
        logger.info("AI: Начинаю генерацию предложения...")
        
        if not self._proposal_chain:
            logger.warning("AI: Цепь генерации предложения не инициализирована")
            return TenderProposal(
                proposal_text="",
                missing_info=[]
            )
        
        prompt = f"""
Ты эксперт по государственным закупкам. Сгенерируй текст заявки на участие в тендере.

Данные тендера:
- Название: {data.title}
- Бюджет: {data.budget} {data.currency}
- Срок подачи: {data.deadline}
- Место поставки: {data.delivery_place}
- Требования к участнику: {', '.join(data.requirements)}

Структура заявки:
1. Введение (название компании, опыт работы)
2. Подтверждение соответствия требованиям
3. Предложение по исполнению контракта
4. Преимущества участия

Сгенерируй текст заявки на русском языке.

Также определи missing_info - список информации, которую нужно добавить в заявку (чего не хватает в данных о тендере).
"""
        
        try:
            result = await self._proposal_chain.ainvoke(prompt)
            logger.info(f"AI: Предложение сгенерировано, длина: {len(result.proposal_text)} символов")
            return result
            
        except Exception as e:
            logger.error(f"AI: Ошибка при генерации предложения: {e}")
            return TenderProposal(
                proposal_text="",
                missing_info=[]
            )


# Create singleton instance
ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Get or create AIService singleton instance."""
    global ai_service
    if ai_service is None:
        ai_service = AIService()
    return ai_service
