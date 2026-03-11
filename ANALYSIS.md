# 📊 Анализ приложения Tender AI Assistant

## 1. Общее описание

Приложение представляет собой **веб-систему для анализа тендерной документации** с использованием RAG-архитектуры.

**Технологический стек:**
- **Backend**: FastAPI + uvicorn + LangChain + FAISS
- **Frontend**: Vue 3 + Vue Router + Tailwind CSS
- **LLM**: OpenAI GPT-4o-mini + Embeddings

### Структура проекта

```
c:/tender/
├── backend/
│   ├── main.py              — FastAPI приложение + CORS
│   ├── state.py             — Глобальное состояние (проблема!)
│   ├── requirements.txt     — Python зависимости
│   ├── data/                — Папка для загружаемых PDF
│   └── api/
│       ├── upload.py        — POST /api/upload
│       ├── chat.py          — POST /api/chat (SSE)
│       ├── analyze.py       — POST /api/analyze (SSE)
│       ├── risks.py         — POST /api/risks (SSE)
│       └── status.py        — GET /api/status
├── frontend/
│   ├── src/
│   │   ├── App.vue          — Layout + тёмный Sidebar
│   │   ├── router/index.js  — 4 страницы
│   │   ├── composables/useSSE.js — SSE стриминг
│   │   ├── api/index.js     — API клиент
│   │   └── views/
│   │       ├── UploadView.vue   — Drag & drop загрузка
│   │       ├── ChatView.vue     — Чат со streaming
│   │       ├── AnalyzeView.vue  — Полный анализ тендера
│   │       └── RisksView.vue    — Анализ рисков
│   └── package.json
├── rag/
│   ├── loader.py            — Загрузка PDF/DOCX/TXT
│   ├── chunker.py           — Разбивка текста (1200 символов)
│   ├── vector_store.py      — FAISS create/load/save
│   ├── rag_chain.py         — LLM chain
│   └── prompt.py            — Промпт-шаблон
└── plans/
    └── architecture.md     — План архитектуры
```

---

## 2. Стиль кода

### ✅ Сильные стороны

| Аспект | Оценка | Комментарий |
|--------|--------|-------------|
| Структура проекта | ✅ Хорошо | Чёткое разделение backend/frontend/rag |
| Использование FastAPI | ✅ Хорошо | Современные подходы, SSE streaming |
| Vue 3 Composition API | ✅ Хорошо | Правильное использование `<script setup>` |
| Разделение ответственности | ✅ Хорошо | API endpoints отделены от RAG логики |
| Prompt Engineering | ✅ Хорошо | Чёткие инструкции в prompt.py |
| Документация | ✅ Хорошо | README.txt и architecture.md |

### ⚠️ Проблемные области

| Аспект | Проблема | Файл |
|--------|----------|------|
| Глобальное состояние | Не потокобезопасные глобальные переменные | `backend/state.py` |
| Дублирование кода | Похожий код в chat.py, analyze.py, risks.py | `backend/api/` |
| Обработка ошибок | Минимальная, без retry/fallback логики | Все API |
| Конфигурация | Hardcoded значения (CORS, chunk_size) | Разные файлы |
| Тесты | Отсутствуют | — |

---

## 3. Критические проблемы

### 🚨 Главная проблема: Нет многопользовательского режима

```python
# backend/state.py - текущая реализация
vectorstore = None           # ОДИН vectorstore на ВСЕХ пользователей!
current_filename = None      # Имя файла общее
chunks_count = 0            # И счётчик чанков тоже общий
```

**Это означает:**
- ❌ Все пользователи работают с **одним и тем же документом**
- ❌ Нет изоляции данных между пользователями
- ❌ Нет аутентификации/авторизации
- ❌ Нет возможности загрузить несколько документов

### 🚨 Глобальное состояние не потокобезопасно

```python
def set_vectorstore(vs, filename, n_chunks):
    global vectorstore, current_filename, chunks_count
    vectorstore = vs  # Гонка данных при одновременных запросах!
```

При одновременной загрузке документов двумя пользователями возможна гонка данных.

---

## 4. Детальный анализ компонентов

### Backend API

| Endpoint | Файл | Проблемы |
|----------|------|----------|
| POST /api/upload | `backend/api/upload.py` | Глобальная перезапись vectorstore |
| POST /api/chat | `backend/api/chat.py` | Дублирование логики similarity_search |
| POST /api/analyze | `backend/api/analyze.py` | Дублирование логики similarity_search |
| POST /api/risks | `backend/api/risks.py` | Дублирование логики similarity_search |
| GET /api/status | `backend/api/status.py` | ОК |

### RAG Pipeline

| Компонент | Файл | Оценка |
|-----------|------|--------|
| PDF Loader | `rag/loader.py` | ✅ Хорошо, поддерживает PDF/DOCX/DOC/TXT |
| Text Chunker | `rag/chunker.py` | ✅ Хорошо, 1200 символов + 200 перекрытие |
| Vector Store | `rag/vector_store.py` | ⚠️ Нет управления несколькими индексами |
| RAG Chain | `rag/rag_chain.py` | ✅ Простая и понятная реализация |
| Prompt | `rag/prompt.py` | ✅ Хорошие инструкции для LLM |

### Frontend

| Компонент | Файл | Оценка |
|-----------|------|--------|
| UploadView | `frontend/src/views/UploadView.vue` | ✅ Хороший UX |
| ChatView | `frontend/src/views/ChatView.vue` | ✅ Streaming работает |
| AnalyzeView | `frontend/src/views/AnalyzeView.vue` | ✅ |
| RisksView | `frontend/src/views/RisksView.vue` | ✅ |
| SSE Composable | `frontend/src/composables/useSSE.js` | ⚠️ Дублируется в ChatView |

---

## 5. Рекомендации по рефакторингу

### Приоритет 1: Изоляция пользовательских данных

**Целевая архитектура:**
```
User_1 → VectorStore_1 → FAISS_1 (faiss_index_user1/)
User_2 → VectorStore_2 → FAISS_2 (faiss_index_user2/)
User_N → VectorStore_N → FAISS_N (faiss_index_userN/)
```

**Необходимые изменения:**

1. **Добавить аутентификацию:**
   - JWT токены
   - Хеширование паролей (bcrypt)
   
2. **Добавить базу данных:**
   - PostgreSQL или SQLite
   - Таблицы: users, documents, sessions

3. **Изменить state.py:**
```python
# Вместо глобальных переменных
class AppState:
    def __init__(self):
        self.user_vectorstores: dict[str, FAISS] = {}
        
app_state = AppState()
```

4. **API endpoints:**
   - `POST /api/auth/register` — регистрация
   - `POST /api/auth/login` — вход
   - `GET /api/documents` — список документов
   - `DELETE /api/documents/{id}` — удалить

### Приоритет 2: Устранить дублирование кода

Создать общую функцию:

```python
# backend/api/base.py
async def similarity_search_with_context(question: str, k: int = 4):
    """Унифицированная логика для chat, analyze, risks"""
    vs = state.get_vectorstore()
    docs = vs.similarity_search(question, k=k)
    context = "\n".join(doc.page_content for doc in docs)
    return context
```

### Приоритет 3: Обработка ошибок

```python
# Добавить retry логику
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def call_llm_with_retry(prompt: str):
    # ...
```

### Приоритет 4: Rate Limiting

```python
from fastapi_limiter import FastAPILimiter

@app.on_event("startup")
async def startup():
    await FastAPILimiter.init()
    
@limiter.limit("10/minute")
async def chat(request: Request):
    # ...
```

---

## 6. Архитектура для многопользовательского режима

```
┌─────────────────────────────────────────────────────────────┐
│                        Клиент                                │
│   Vue 3 SPA + JWT Token                                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                     API Gateway                              │
│   FastAPI + CORS + Rate Limiting                           │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   Authentication Layer                       │
│   JWT / OAuth 2.0                                           │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    Business Logic                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   Upload    │  │    Chat    │  │  Analyze   │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
│  ┌──────▼────────────────▼────────────────▼──────┐           │
│  │           RAG Pipeline Manager               │           │
│  └────────────────────┬─────────────────────────┘           │
└───────────────────────┼─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│              Data Layer (PostgreSQL)                       │
│   users, documents, sessions                                │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│              Cache Layer (Redis)                            │
│   Кэш vectorstores                                          │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│           Vector Stores (FAISS)                             │
│   faiss_index_{user_id}_{doc_id}/                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Сравнение: Текущее vs Целевое

| Компонент | Текущее | Целевое |
|-----------|---------|---------|
| Аутентификация | ❌ Нет | ✅ JWT / OAuth |
| Авторизация | ❌ Нет | ✅ По user_id |
| Хранение документов | Локальная папка | S3 / MinIO |
| Хранение метаданных | ❌ Нет | PostgreSQL |
| Кэш vectorstores | ❌ Нет | Redis / LRU |
| Rate Limiting | ❌ Нет | ✅ fastapi-limiter |
| Обработка ошибок | Базовая | Retry + Fallback |
| Тесты | ❌ Нет | pytest |

---

## 8. План миграции

### Фаза 1: Рефакторинг текущего кода
- [ ] Вынести общую логику similarity_search
- [ ] Добавить логирование
- [ ] Добавить базовую обработку ошибок

### Фаза 2: Аутентификация
- [ ] Добавить SQLite БД
- [ ] Реализовать JWT auth
- [ ] Добавить /api/auth endpoints

### Фаза 3: Изоляция данных
- [ ] Переписать state.py
- [ ] Привязать vectorstore к user_id + doc_id
- [ ] API для управления документами

### Фаза 4: Масштабирование
- [ ] Добавить Redis кэш
- [ ] Добавить rate limiting
- [ ] Запустить в Docker

---

## 9. Безопасность

### Текущие проблемы
- ❌ Нет аутентификации
- ❌ Нет авторизации
- ❌ CORS настроен для localhost и одного IP
- ✅ API ключ в .env (правильно)

### Рекомендации
1. Хранить JWT secret в переменных окружения
2. Добавить HTTPS в production
3. Валидировать размер загружаемых файлов
4. Очищать временные файлы

---

## 10. Резюме

| Аспект | Статус | Приоритет |
|--------|--------|-----------|
| MVP работоспособен | ✅ Да | — |
| Код читаем | ✅ Да | — |
| Многопользовательский режим | ❌ Нет | 🔴 Высокий |
| Масштабируемость | ❌ Нет | 🔴 Высокий |
| Обработка ошибок | ⚠️ Слабо | 🟡 Средний |
| Тесты | ❌ Нет | 🟡 Средний |
| Безопасность | ❌ Нет | 🔴 Высокий |

### Вердикт

Приложение **отлично подходит для MVP/однопользовательского режима**. Код чистый, читаемый, следование современным практикам.

**Для многопользовательского режима необходима существенная переработка архитектуры:**
1. Добавление аутентификации и авторизации
2. Внедрение базы данных для метаданных
3. Система кэширования vectorstores
4. Обработка ошибок с retry логикой

Ориентировочное время миграции: **2-3 недели** для команды из 1-2 разработчиков.

---

*Дата анализа: 2026-03-11*
*Автор: AI Code Review*
