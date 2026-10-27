@echo off
echo Dang don dep cac cong 8000 va 3000...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":3000" ^| find "LISTENING"') do taskkill /f /pid %%a >nul 2>&1

echo Dang khoi dong Backend...
start "Backend Server" cmd /k "cd backend && python -m uvicorn app.main:app --reload --port 8000"

echo Dang khoi dong Frontend...
start "Frontend Server" cmd /k "cd frontend && npm run dev"

echo Da khoi dong xong! Ban co the tat cua so nay.
timeout /t 3
