@echo off
title dMRV Backend  (port 8000)
REM ---- Starts the FastAPI backend with the CORS origin the verifier page needs.
REM ---- Leave this window open during the whole demo.
cd /d "%~dp0..\backend"

REM Free port 8000 if a previous run is still holding it (a leftover backend
REM locks the SQLite DB and makes startup migrations fail). Safe if nothing's there.
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1

REM Use the conda Python that has the backend deps; fall back to PATH python.
set PY=C:\ProgramData\miniconda3\python.exe
if not exist "%PY%" set PY=python

set DATABASE_URL=sqlite+aiosqlite:///./dmrv.db

REM Secrets load from the gitignored demo_secrets.bat (copy demo_secrets.example.bat).
if exist "%~dp0demo_secrets.bat" call "%~dp0demo_secrets.bat"
if "%DMRV_ADMIN_SECRET%"=="" (
  echo ERROR: demo_tools\demo_secrets.bat missing or empty.
  echo Copy demo_secrets.example.bat to demo_secrets.bat and set real values.
  pause
  exit /b 1
)

set DMRV_ALLOWED_ORIGIN=http://localhost:8080

echo ============================================================
echo   dMRV backend  on  http://0.0.0.0:8000
echo   CORS allowed  for %DMRV_ALLOWED_ORIGIN%
echo   health check: http://localhost:8000/api/health
echo ============================================================
"%PY%" -m uvicorn server:app --host 0.0.0.0 --port 8000

echo.
echo Backend stopped.
pause
