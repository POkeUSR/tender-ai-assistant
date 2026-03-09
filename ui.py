from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from rag.loader import load_pdf
from rag.chunker import split_text
from rag.vector_store import create_vectorstore, load_vectorstore
from rag.rag_chain import ask_llm
from rag.agent import analyze_tender as agent_analyze_tender

vectorstore = None


def upload_pdf(file):
    global vectorstore

    text = load_pdf(file.name)
    chunks = split_text(text)
    vectorstore = create_vectorstore(chunks)

    return "Документ загружен и проиндексирован."


def ask_question(question):
    global vectorstore

    try:
        if vectorstore is None:
            return "Сначала загрузите тендерный документ."

        answer = ask_llm(vectorstore, question)
        return answer

    except Exception as e:
        return f"Ошибка: {str(e)}"


def analyze_tender():
    global vectorstore

    if vectorstore is None:
        return "Сначала загрузите документ."

    try:
        return agent_analyze_tender(vectorstore)
    except Exception as e:
        return f"Ошибка: {str(e)}"


def analyze_risks():
    global vectorstore

    if vectorstore is None:
        return "Сначала загрузите документ."

    from analyze_risks import RISK_QUESTION
    try:
        return ask_llm(vectorstore, RISK_QUESTION)
    except Exception as e:
        return f"Ошибка: {str(e)}"


def load_saved():
    global vectorstore
    vs = load_vectorstore()
    if vs is not None:
        vectorstore = vs
        return "Загружен сохранённый индекс."
    return "Сохранённый индекс не найден. Загрузите PDF."


with gr.Blocks() as demo:

    gr.Markdown("# 🏛️ Tender AI Assistant")

    with gr.Row():
        file = gr.File(label="Загрузить тендерный PDF")
        upload_btn = gr.Button("Загрузить документ")
        load_btn = gr.Button("Загрузить сохранённый индекс")

    upload_output = gr.Textbox(label="Статус")

    upload_btn.click(upload_pdf, inputs=file, outputs=upload_output)
    load_btn.click(load_saved, inputs=None, outputs=upload_output)

    gr.Markdown("## 💬 Задать вопрос по тендеру")

    question = gr.Textbox(label="Вопрос")
    ask_btn = gr.Button("Спросить")
    answer = gr.Textbox(label="Ответ", lines=10)
    ask_btn.click(ask_question, inputs=question, outputs=answer)

    gr.Markdown("## 📋 Полный анализ тендера")
    analyze_btn = gr.Button("Анализировать тендер")
    analyze_output = gr.Textbox(label="Анализ", lines=20)
    analyze_btn.click(analyze_tender, inputs=None, outputs=analyze_output)

    gr.Markdown("## ⚠️ Анализ рисков")
    risks_btn = gr.Button("Анализ рисков")
    risks_output = gr.Textbox(label="Риски", lines=20)
    risks_btn.click(analyze_risks, inputs=None, outputs=risks_output)


demo.launch()
