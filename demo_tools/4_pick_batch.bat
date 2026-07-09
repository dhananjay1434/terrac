@echo off
title dMRV - Pick Batch for the Verifier View
REM ---- Lists batches on the backend and prints a ready-to-open Verifier URL
REM ---- for the most-complete one. Copy that URL into your browser.
cd /d "%~dp0.."

set PY=C:\ProgramData\miniconda3\python.exe
if not exist "%PY%" set PY=python

"%PY%" demo_tools\pick_batch.py

echo.
echo ------------------------------------------------------------
echo   Copy the URL printed above and paste it into your browser.
echo   (Backend [1] and Verifier page [2] must be running first.)
echo ------------------------------------------------------------
pause
