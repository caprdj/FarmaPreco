@echo off
title FarmaPreco - Comparador de Medicamentos
echo ========================================================
echo   Iniciando o FarmaPreco - Comparador de Farmacias
echo ========================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [AVISO] Criando ambiente virtual Python...
    python -m venv .venv
    echo [AVISO] Instalando dependencias...
    .venv\Scripts\pip install -r requirements.txt
)

echo Abrindo o portal no seu navegador em http://localhost:8000 ...
start http://localhost:8000

echo.
echo ========================================================
echo   SERVIDOR ONLINE:
echo   - No Computador: http://localhost:8000
echo   - No Celular (mesmo Wi-Fi): http://192.168.15.9:8000
echo ========================================================
echo.
echo Servidor em execucao. Para encerrar, basta fechar esta janela.
echo.

.venv\Scripts\python.exe -m uvicorn portal:app --host 0.0.0.0 --port 8000 --reload
pause
