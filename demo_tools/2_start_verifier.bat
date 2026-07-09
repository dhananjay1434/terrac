@echo off
title dMRV Verifier Page  (port 8080)
REM ---- Serves the auditor "Verifier View" web page on http://localhost:8080
REM ---- Leave this window open during the demo.
cd /d "%~dp0verifier_view"

set PY=C:\ProgramData\miniconda3\python.exe
if not exist "%PY%" set PY=python

echo ============================================================
echo   Verifier View  on  http://localhost:8080
echo   open the URL that 4_pick_batch.bat prints
echo ============================================================
"%PY%" -m http.server 8080

echo.
echo Page server stopped.
pause
