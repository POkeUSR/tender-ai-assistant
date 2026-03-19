from dotenv import load_dotenv

load_dotenv()

from rag.loader import load_pdf
from rag.chunker import split_text
from rag.vector_store import create_vectorstore
from rag.rag_chain import ask_llm

text = load_pdf("data/tender.pdf")

chunks = split_text(text)

db = create_vectorstore(chunks)

while True:

    query = input("\nВведите вопрос по тендеру: ")

    answer = ask_llm(db, query)

    print("\nОтвет AI:\n")
    print(answer)
