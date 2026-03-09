@echo off
echo Starting Tender AI Frontend...
cd /d "%~dp0frontend"
call npm install
call npm run dev
