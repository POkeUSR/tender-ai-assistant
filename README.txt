=========================================================
  TENDER AI ASSISTANT — Документация проекта
=========================================================


ОПИСАНИЕ
---------
Веб-приложение для анализа тендерной документации с помощью
искусственного интеллекта (GPT-4o-mini + RAG).

Позволяет:
  - Загружать PDF тендерной документации
  - Задавать вопросы по тендеру в чат-интерфейсе
  - Получать полный структурированный анализ (8 пунктов)
  - Получать матрицу рисков участия (5 категорий)

Ответы генерируются в реальном времени (стриминг).


ТЕХНОЛОГИИ
-----------
Backend (Python):
  - FastAPI           — REST API сервер
  - uvicorn           — ASGI сервер
  - LangChain         — RAG оркестрация
  - ChatOpenAI        — GPT-4o-mini (языковая модель)
  - OpenAIEmbeddings  — text-embedding-3-large
  - FAISS             — векторная база данных
  - PyMuPDF (fitz)    — извлечение текста из PDF
  - SSE               — стриминг ответов

Frontend (JavaScript):
  - Vue 3             — SPA фреймворк
  - Vue Router 4      — маршрутизация
  - Tailwind CSS      — стилизация
  - marked            — рендеринг Markdown
  - Vite              — сборщик


КАК РАБОТАЕТ (RAG PIPELINE)
-----------------------------
1. ЗАГРУЗКА PDF
   Пользователь загружает PDF через браузер.
   PyMuPDF извлекает текст постранично.

2. ЧАНКИНГ
   Текст разбивается на фрагменты по 1200 символов
   с перекрытием 200 символов.

3. ИНДЕКСАЦИЯ
   Каждый фрагмент преобразуется в вектор через
   text-embedding-3-large и сохраняется в FAISS.
   Индекс сохраняется на диск (faiss_index/).

4. ПОИСК (при вопросе)
   Вопрос пользователя тоже преобразуется в вектор.
   FAISS находит 4 наиболее похожих фрагмента (k=4).

5. ГЕНЕРАЦИЯ (SSE стриминг)
   Фрагменты + вопрос → промпт → GPT-4o-mini.
   Ответ передаётся токен за токеном через SSE.
   Браузер отображает текст по мере генерации.


СТРУКТУРА ПРОЕКТА
------------------
tender/
  backend/
    main.py              — FastAPI приложение + CORS
    state.py             — Глобальный vectorstore
    requirements.txt     — Python зависимости
    data/                — Папка для загружаемых PDF
    api/
      upload.py          — POST /api/upload
      chat.py            — POST /api/chat (SSE)
      analyze.py         — POST /api/analyze (SSE)
      risks.py           — POST /api/risks (SSE)
      status.py          — GET /api/status

  frontend/
    package.json
    vite.config.js       — Proxy /api -> :8000
    tailwind.config.js
    src/
      App.vue            — Layout + тёмный Sidebar
      router/index.js    — 4 страницы
      composables/
        useSSE.js        — SSE стриминг composable
      api/index.js       — API клиент
      style.css          — Tailwind + глобальные стили
      views/
        UploadView.vue   — Drag & drop загрузка PDF
        ChatView.vue     — Чат со streaming
        AnalyzeView.vue  — Полный анализ тендера
        RisksView.vue    — Анализ рисков

  rag/
    loader.py            — Загрузка PDF
    chunker.py           — Разбивка текста
    vector_store.py      — FAISS create/load/save
    rag_chain.py         — LLM chain
    prompt.py            — Промпт-шаблон
    agent.py             — Агент анализа

  .env                   — OpenAI API ключ (не в git!)
  .gitignore
  start_backend.bat      — Быстрый запуск backend
  start_frontend.bat     — Быстрый запуск frontend


ТРЕБОВАНИЯ
-----------
  - Python 3.10 или выше
  - Node.js 18 или выше
  - OpenAI API ключ (в файле .env)


УСТАНОВКА И ЗАПУСК
-------------------
Шаг 1. Установить Python зависимости:
  pip install -r backend/requirements.txt

Шаг 2. Запустить backend (первый терминал):
  cd backend
  python -m uvicorn main:app --reload --port 8000

  Или двойной клик: start_backend.bat

Шаг 3. Установить Node зависимости (один раз):
  cd frontend
  npm install

Шаг 4. Запустить frontend (второй терминал):
  cd frontend
  npm run dev

  Или двойной клик: start_frontend.bat

Шаг 5. Открыть в браузере:
  http://localhost:5173


ИСПОЛЬЗОВАНИЕ
--------------
1. Перейти на страницу "Загрузка" (Upload)
2. Перетащить PDF тендера или нажать для выбора
3. Нажать "Загрузить и проиндексировать"
4. После успеха можно:
   - Перейти в "Чат" — задавать вопросы по тендеру
   - Перейти в "Анализ" — получить 8-пунктовый анализ
   - Перейти в "Риски" — получить матрицу рисков (5 категорий)


API ENDPOINTS
--------------
GET  /api/status          — Статус загруженного документа
POST /api/upload          — Загрузить PDF (multipart/form-data)
POST /api/chat            — Вопрос-ответ (SSE стриминг)
POST /api/analyze         — Полный анализ тендера (SSE стриминг)
POST /api/risks           — Анализ рисков (SSE стриминг)


БЕЗОПАСНОСТЬ
-------------
  - .env файл с API ключом добавлен в .gitignore
  - API ключ не попадает в репозиторий
  - CORS настроен только для localhost:5173 и localhost:3000


=========================================================
