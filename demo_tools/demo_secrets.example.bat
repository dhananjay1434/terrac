@echo off
REM ============================================================
REM  TEMPLATE for demo_tools\demo_secrets.bat (which is GITIGNORED).
REM  Copy this file to demo_secrets.bat and fill in real values:
REM      copy demo_secrets.example.bat demo_secrets.bat
REM  Generate a fresh secret with:
REM      python -c "import secrets;print(secrets.token_hex(32))"
REM  NEVER commit demo_secrets.bat or paste real secrets into this template.
REM ============================================================
set DMRV_HMAC_SECRET=CHANGE_ME_64_HEX_CHARS
set DMRV_ADMIN_SECRET=CHANGE_ME_64_HEX_CHARS
