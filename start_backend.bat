@echo off
echo Starting Tender AI Backend...
cd /d "%~dp0"
set PYTHONPATH=backend
cd backend
pip install -r requirements.txt >nul 2>&1
python -m uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
