import os
import shutil
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException

from rag.loader import load_files, SUPPORTED_EXTENSIONS
from rag.chunker import split_text
from rag.vector_store import create_vectorstore
import state

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    saved_paths = []
    filenames = []

    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Файл '{file.filename}': неподдерживаемый формат '{ext}'. "
                f"Поддерживаются: {', '.join(SUPPORTED_EXTENSIONS)}",
            )
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        saved_paths.append(file_path)
        filenames.append(file.filename)

    try:
        text = load_files(saved_paths)
        chunks = split_text(text)
        vs = create_vectorstore(chunks)
        combined_name = ", ".join(filenames)
        state.set_vectorstore(vs, combined_name, len(chunks), text)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Ошибка обработки файлов: {str(e)}"
        )

    return {
        "status": "ok",
        "filenames": filenames,
        "chunks_count": len(chunks),
    }
