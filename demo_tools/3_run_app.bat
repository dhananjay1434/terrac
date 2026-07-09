@echo off
title dMRV App  (Flutter debug on phone)
REM ---- Builds & runs the app on the phone in demo mode (mock sensors, no hardware).
REM ---- EDIT THESE TWO if they change tomorrow:
REM      LANIP  = this laptop's Wi-Fi IPv4  (run: ipconfig  then read the Wi-Fi IPv4)
REM      DEVICE = phone id                  (run: flutter devices)  -- currently SM S721B
set LANIP=192.168.1.19
set DEVICE=RZCY511HZBE
set TOKEN=demo-eu-3
set FLUTTER=C:\Users\bit\development\flutter\bin\flutter.bat

cd /d "%~dp0.."
echo ============================================================
echo   Running app on %DEVICE%  using backend http://%LANIP%:8000
echo   (phone must be on the SAME Wi-Fi as this laptop)
echo ============================================================
"%FLUTTER%" run -d %DEVICE% --dart-define=DMRV_API_BASE_URL=http://%LANIP%:8000 --dart-define=ENROLLMENT_TOKEN=%TOKEN% --dart-define=DMRV_DEMO_MODE=true

echo.
echo App stopped.
pause
