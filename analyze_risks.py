from dotenv import load_dotenv
load_dotenv()

from rag.loader import load_pdf
from rag.chunker import split_text
from rag.vector_store import create_vectorstore
from rag.rag_chain import ask_llm

RISK_QUESTION = """
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

Для каждого риска укажи: описание риска, уровень (высокий/средний/низкий), рекомендацию.
"""


def analyze_risks(pdf_path: str = "data/tender.pdf") -> str:
    text = load_pdf(pdf_path)
    chunks = split_text(text)
    vectorstore = create_vectorstore(chunks)
    return ask_llm(vectorstore, RISK_QUESTION)


if __name__ == "__main__":
    import sys
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "data/tender.pdf"
    print(f"Анализ рисков для: {pdf_path}\n")
    result = analyze_risks(pdf_path)
    print(result)
