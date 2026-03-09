@echo off
echo Starting Tender AI Backend...
cd /d "%~dp0"
pip install -r backend/requirements.txt >nul 2>&1
cd backend
python -m uvicorn main:app --reload --port 8000
