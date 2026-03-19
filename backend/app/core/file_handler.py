"""
File handler for loading and processing document files.
Supports PDF, DOCX, DOC, and TXT formats.
"""

import os
import platform
import subprocess
from typing import List

import fitz  # PyMuPDF


# ============== Loaders ==============

def load_pdf(path: str) -> str:
    """Load text from PDF file."""
    doc = fitz.open(path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text


def load_docx(path: str) -> str:
    """Load text from DOCX file."""
    try:
        from docx import Document
    except ImportError:
        raise ImportError("Установите python-docx: pip install python-docx")
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def load_txt(path: str) -> str:
    """Load text from TXT file."""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def load_doc_legacy(path: str) -> str:
    """Load text from DOC file using antiword or Windows COM."""
    # Try antiword (Linux/Mac)
    try:
        result = subprocess.run(
            ["antiword", path], capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return result.stdout
    except FileNotFoundError:
        pass

    # Try win32com (Windows + MS Word)
    if platform.system() == "Windows":
        try:
            import win32com.client
            import pythoncom

            pythoncom.CoInitialize()
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            doc = word.Documents.Open(os.path.abspath(path))
            text = doc.Content.Text
            doc.Close(False)
            word.Quit()
            return text
        except Exception:
            pass

    raise ValueError(
        f"Не удалось прочитать файл .doc: '{os.path.basename(path)}'.\n"
        "Пожалуйста, конвертируйте файл в формат .docx (Файл → Сохранить как → .docx в MS Word) "
        "или в .pdf/.txt и загрузите снова."
    )


# ============== Loader Registry ==============

LOADERS = {
    ".pdf": load_pdf,
    ".docx": load_docx,
    ".doc": load_doc_legacy,
    ".txt": load_txt,
}

SUPPORTED_EXTENSIONS = list(LOADERS.keys())


# ============== Main Functions ==============

def load_file(path: str) -> str:
    """
    Load text from a single file.
    
    Args:
        path: Path to the file
        
    Returns:
        Extracted text from the file
        
    Raises:
        ValueError: If file format is not supported
    """
    ext = os.path.splitext(path)[1].lower()
    loader = LOADERS.get(ext)
    if loader is None:
        raise ValueError(
            f"Неподдерживаемый формат файла: {ext}. Поддерживаются: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    return loader(path)


def load_files(paths: List[str]) -> str:
    """
    Load text from multiple files and combine.
    
    Args:
        paths: List of file paths
        
    Returns:
        Combined text from all files
    """
    all_text = []
    for path in paths:
        text = load_file(path)
        all_text.append(text)
    return "\n\n".join(all_text)
