import os
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

# Store FAISS index in project root regardless of cwd
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAISS_INDEX_PATH = os.path.join(_PROJECT_ROOT, "faiss_index")


def get_embeddings():
    return OpenAIEmbeddings(model="text-embedding-3-large")


def create_vectorstore(chunks, save_path: str = FAISS_INDEX_PATH):
    embeddings = get_embeddings()
    db = FAISS.from_texts(chunks, embeddings)
    db.save_local(save_path)
    return db


def load_vectorstore(load_path: str = FAISS_INDEX_PATH):
    if not os.path.exists(load_path):
        return None
    embeddings = get_embeddings()
    return FAISS.load_local(load_path, embeddings, allow_dangerous_deserialization=True)
