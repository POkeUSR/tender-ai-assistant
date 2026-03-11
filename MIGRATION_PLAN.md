# План миграции Tender AI Assistant на многопользовательский режим

## Содержание

1. [ние](#текуТекущее состоящее-состояние)
2. [Целевая архитектура](#целевая-архитектура)
3. [Этап 1: Рефакторинг](#этап-1-рефакторинг-текущего-кода)
4. [Этап 2: База данных](#этап-2-база-данных)
5. [Этап 3: Аутентификация](#этап-3-аутентификация)
6. [Этап 4: Изоляция данных](#этап-4-изоляция-данных-пользователей)
7. [Этап 5: Масштабирование](#этап-5-масштабирование)
8. [Новые файлы](#новые-файлы-для-создания)
9. [Изменяемые файлы](#изменяемые-файлы)

---

## Текущее состояние

```
ТЕКУЩАЯ АРХИТЕКТУРА:

Frontend (Vue 3)
       │
       ▼
┌─────────────────────────────────────────┐
│         FastAPI Backend                  │
│  ┌───────────────────────────────────┐  │
│  │     backend/state.py              │  │
│  │     vectorstore = None  ◄────────│──│── Все пользователи
│  │     current_filename = None       │  │    используют ОДИН документ
│  │     (ГЛОБАЛЬНАЯ ПЕРЕМЕННАЯ!)     │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│         FAISS Vector Store               │
│         (Один индекс для всех)           │
└─────────────────────────────────────────┘

ПРОБЛЕМЫ:
❌ Все пользователи видят один документ
❌ Нет аутентификации
❌ Нет авторизации
❌ Глобальные переменные не потокобезопасны
❌ Нет изоляции данных
```

---

## Целевая архитектура

```
ЦЕЛЕВАЯ АРХИТЕКТУРА:

Vue 3 SPA (Frontend с JWT токеном)
                │
                ▼
┌─────────────────────────────────────────┐
│           FastAPI Backend                 │
│  ┌──────────────┐  ┌──────────────┐     │
│  │   Auth API   │  │  Documents   │     │
│  │  /register   │  │  /upload     │     │
│  │  /login      │  │  /list       │     │
│  │  /refresh    │  │  /delete     │     │
│  └──────────────┘  └──────────────┘     │
│  ┌───────────────────────────────────┐  │
│  │   Authentication Middleware        │  │
│  │   - JWT верификация               │  │
│  │   - Извлечение user_id            │  │
│  └───────────────────────────────────┘  │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│     Database Layer (SQLite/PostgreSQL)  │
│     users ────── documents              │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│     Cache Layer (Redis/In-Memory)       │
│     vs:{user_id}:{doc_id}              │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│     Vector Stores (FAISS)               │
│     faiss_index/{user_id}/{doc_id}/     │
└─────────────────────────────────────────┘
```

---

## Этап 1: Рефакторинг текущего кода

### Задачи:
1. Создать `backend/api/base.py` — общие функции для RAG
2. Создать `backend/api/exceptions.py` — кастомные исключения
3. Добавить логирование
4. Рефакторить дублирующий код в chat.py, analyze.py, risks.py

### backend/api/base.py
```python
from typing import Optional
import state

async def similarity_search_with_context(
    question: str, 
    k: int = 4,
    user_id: Optional[str] = None,
    doc_id: Optional[str] = None
):
    """Унифицированная логика для similarity search."""
    if user_id and doc_id:
        vs = state.get_user_vectorstore(user_id, doc_id)
    else:
        vs = state.get_vectorstore()
    
    if vs is None:
        raise ValueError("Документ не загружен")
    
    docs = vs.similarity_search(question, k=k)
    context = "\n".join(
        doc.page_content if hasattr(doc, "page_content") else str(doc)
        for doc in docs
    )
    return context
```

---

## Этап 2: База данных

### Установка зависимостей:
```bash
pip install sqlalchemy sqlalchemy[sqlite] alembic
```

### backend/database.py
```python
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tender.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    documents = relationship("Document", back_populates="user")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    vectorstore_path = Column(String, nullable=False)
    chunks_count = Column(Integer, default=0)
    file_size = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="documents")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
```

---

## Этап 3: Аутентификация

### Установка зависимостей:
```bash
pip install python-jose passlib[bcrypt] pyjwt
```

### backend/auth.py
```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os

SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Неверный токен")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user
```

### backend/api/auth.py
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from backend.database import get_db, User
from backend.auth import verify_password, get_password_hash, create_access_token

router = APIRouter()

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    password_confirm: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/register")
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    if user_data.password != user_data.password_confirm:
        raise HTTPException(status_code=400, detail="Пароли не совпадают")
    
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
    
    user = User(email=user_data.email, hashed_password=get_password_hash(user_data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email}

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}
```

---

## Этап 4: Изоляция данных пользователей

### backend/state.py (переписать)
```python
import threading

class VectorStoreManager:
    """Потокобезопасный менеджер vectorstores."""
    
    def __init__(self):
        self._stores: dict[str, any] = {}
        self._lock = threading.RLock()
        self._legacy_store = None
    
    def set_legacy(self, vs, filename: str, n_chunks: int):
        with self._lock:
            self._legacy_store = (vs, filename, n_chunks)
    
    def get_legacy(self):
        with self._lock:
            return self._legacy_store
    
    def is_legacy_ready(self) -> bool:
        return self._legacy_store is not None
    
    def set_user_vectorstore(self, user_id: str, doc_id: str, vs):
        key = f"{user_id}:{doc_id}"
        with self._lock:
            self._stores[key] = vs
    
    def get_user_vectorstore(self, user_id: str, doc_id: str):
        key = f"{user_id}:{doc_id}"
        with self._lock:
            return self._stores.get(key)
    
    def delete_user_vectorstore(self, user_id: str, doc_id: str):
        key = f"{user_id}:{doc_id}"
        with self._lock:
            self._stores.pop(key, None)
    
    def clear_user_data(self, user_id: str):
        with self._lock:
            keys_to_delete = [k for k in self._stores.keys() if k.startswith(f"{user_id}:")]
            for key in keys_to_delete:
                del self._stores[key]

vectorstore_manager = VectorStoreManager()

# Legacy функции (для совместимости)
def set_vectorstore(vs, filename: str, n_chunks: int):
    vectorstore_manager.set_legacy(vs, filename, n_chunks)

def get_vectorstore():
    legacy = vectorstore_manager.get_legacy()
    return legacy[0] if legacy else None

def is_ready() -> bool:
    return vectorstore_manager.is_legacy_ready()

# Новые функции
def get_user_vectorstore(user_id: str, doc_id: str):
    return vectorstore_manager.get_user_vectorstore(user_id, doc_id)

def set_user_vectorstore(user_id: str, doc_id: str, vs):
    vectorstore_manager.set_user_vectorstore(user_id, doc_id, vs)
```

### backend/api/documents.py
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from backend.database import get_db, Document
from backend.auth import get_current_user
import shutil

router = APIRouter()

class DocumentResponse(BaseModel):
    id: int
    filename: str
    chunks_count: int
    created_at: datetime
    class Config:
        from_attributes = True

@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(Document).filter(Document.user_id == current_user.id).all()

@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == current_user.id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    if os.path.exists(doc.vectorstore_path):
        shutil.rmtree(doc.vectorstore_path)
    
    from backend import state
    state.vectorstore_manager.delete_user_vectorstore(str(current_user.id), str(doc_id))
    
    db.delete(doc)
    db.commit()
    return {"status": "ok"}
```

---

## Этап 5: Масштабирование

### Опционально:
- Redis для кэширования vectorstores
- Rate limiting (slowapi)
- Celery для асинхронной обработки

---

## Новые файлы (для создания)

| Файл | Описание |
|------|----------|
| `backend/database.py` | Модели User, Document, функции БД |
| `backend/auth.py` | JWT аутентификация, хеширование |
| `backend/api/base.py` | Общие функции для RAG |
| `backend/api/exceptions.py` | Кастомные исключения |
| `backend/api/auth.py` | Endpoints /register, /login |
| `backend/api/documents.py` | Endpoints /documents |

---

## Изменяемые файлы

| Файл | Изменения |
|------|-----------|
| `backend/state.py` | Потокобезопасный менеджер |
| `backend/main.py` | Подключение auth, инициализация БД |
| `backend/api/chat.py` | Защита Depends(get_current_user) |
| `backend/api/upload.py` | Сохранение в БД, user-specific paths |
| `backend/api/analyze.py` | Изоляция по пользователю |
| `backend/api/risks.py` | Изоляция по пользователю |
| `frontend/src/api/index.js` | Auth методы, заголовки |
| `backend/requirements.txt` | Добавить зависимости |

---

## Структура FAISS индексов после миграции

```
faiss_index/
├── user_1/
│   ├── doc_1/
│   │   ├── index.faiss
│   │   └── index.pkl
│   └── doc_2/
│       └── ...
├── user_2/
│   └── doc_1/
│       └── ...
└── user_N/
    └── doc_M/
        └── ...
```

---

## Резюме этапов

| Этап | Задачи | Время |
|------|--------|-------|
| 1. Рефакторинг | base.py, exceptions.py, логирование | 1-2 дня |
| 2. База данных | database.py, модели | 1 день |
| 3. Аутентификация | auth.py, /register, /login | 1-2 дня |
| 4. Изоляция данных | state.py, documents.py | 2-3 дня |
| 5. Масштабирование | Redis, rate limiting | 1-2 дня |

**Общее время: 6-10 рабочих дней**
