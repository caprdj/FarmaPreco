@echo off
title FarmaPreco - Monitor Pessoal
echo ====================================================
echo      INICIANDO FARMAPRECO (VERSAO PESSOAL)
echo ====================================================
echo.

cd /d "%~dp0"

echo [1/2] Iniciando Servidor Local FarmaPreco...
start "FarmaPreco Server" /B .venv\Scripts\python.exe -m uvicorn portal:app --host 0.0.0.0 --port 8000

timeout /t 2 /nobreak >nul

echo [2/2] Abrindo navegador...
start http://localhost:8000

echo.
echo ====================================================
echo  FarmaPreco aberto em http://localhost:8000
echo ====================================================
echo.

if exist "C:\Program Files (x86)\cloudflared\cloudflared.exe" (
    echo Iniciando tunel HTTPS para acesso no celular (opcional)...
    "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://127.0.0.1:8000
) else (
    echo Pressione qualquer tecla para encerrar.
    pause
)
