@echo off
chcp 65001 > nul
echo [INFO] Dang don dep cac cong dang bi chiem dung...

REM Kill process on port 8000 (Backend)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo [INFO] Dang tat tien trinh PID %%a tren cong 8000
    taskkill /F /PID %%a > nul 2>&1
)

REM Kill process on port 3000 (Frontend)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do (
    echo [INFO] Dang tat tien trinh PID %%a tren cong 3000
    taskkill /F /PID %%a > nul 2>&1
)

timeout /t 2 /nobreak > nul

echo [INFO] Khoi dong Backend (FastAPI) tren cong 8000...
start "FreshChain Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --reload --port 8000"

echo [INFO] Khoi dong Frontend (Vite) tren cong 3000...
start "FreshChain Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo [SUCCESS] Da khoi dong ca Backend va Frontend!
echo [INFO] Backend: http://localhost:8000/docs
echo [INFO] Frontend: http://localhost:3000
pause
