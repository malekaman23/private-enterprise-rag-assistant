@echo off
REM start-app.cmd
REM Ek hi command se backend (FastAPI) aur frontend (React) dono chalata hai.
REM Har ek apni alag window mein khulega, taaki dono ke logs alag-alag dikhein.

echo Starting Personal AI Assistant...
echo.

REM Backend - naye window mein
start "Backend (FastAPI)" cmd /k "call venv312clean\Scripts\activate && uvicorn api:app --reload --port 8000"

REM 3 second wait karo taaki backend pehle start ho jaye
timeout /t 3 /nobreak >nul

REM Frontend - naye window mein
start "Frontend (React)" cmd /k "cd frontend && npm run dev"

echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Dono terminal windows khul gayi hain. Unhe band mat karna jab tak app use karni ho.