@echo off
title FarmaPreco - Servidor & Tunel
echo ====================================================
echo      INICIANDO FARMAPRECO (PORTAL & TUNEL HTTPS)
echo ====================================================
echo.

cd /d "%~dp0"

echo [1/2] Iniciando Servidor FastAPI...
start "FarmaPreco Server" /B .venv\Scripts\python.exe -m uvicorn portal:app --host 0.0.0.0 --port 8000

timeout /t 3 /nobreak >nul

echo [2/2] Iniciando Tunel Cloudflare HTTPS...
echo.
"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://127.0.0.1:8000

pause
