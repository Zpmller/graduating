@echo off

:: ====================
echo Mining Hot-Work Safety Monitoring System
echo ====================
echo.

:: SRS Media Server
echo [1/4] Begin SRS Server...
docker compose up -d 2>nul
if %errorlevel% equ 0 (
    echo SRS ready.
) else (
    echo [Warning] Docker unavailable.
)

:: Backend System
echo [2/4] Begin Backend System...
start "Backend" cmd /k "cd /d %~dp0backend_system && call %~dp0backend_system\.venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: AI Edge System  
echo [3/4] Begin AI Edge System...
start "Edge" cmd /k "cd /d %~dp0ai_edge_system && call %~dp0ai_edge_system\.venv\Scripts\activate.bat && python main.py"

:: Frontend Dashboard
echo [4/4] Begin Frontend Dashboard...
start "Frontend" cmd /k "cd /d %~dp0frontend_dashboard && npm run dev"

echo ====================
echo All systems started
echo ====================
echo - SRS: http://localhost:1985
echo - Backend: http://localhost:8000  
echo - Frontend: http://localhost:5173
echo ====================
pause