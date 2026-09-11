@echo off
setlocal

REM Garante que o script execute a partir da pasta do projeto
cd /d "%~dp0"

REM Escolhe interpretador Python (prioriza venv local)
set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
) else (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_EXE=python"
)

if not defined PYTHON_EXE (
    echo.
    echo Python nao encontrado. Instale o Python e tente novamente.
    pause
    exit /b 1
)

REM Valida dependencias antes de abrir backend/browser
"%PYTHON_EXE%" -c "import flask, yt_dlp, curl_cffi" >nul 2>nul
if errorlevel 1 (
    echo.
    echo Dependencias ausentes no ambiente Python.
    echo Execute este comando na pasta do projeto:
    echo "%PYTHON_EXE%" -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo.
echo Iniciando backend Flask...
start "YT/DL Backend" /D "%~dp0" "%PYTHON_EXE%" "app.py"

echo Aguardando 3 segundos...
ping 127.0.0.1 -n 4 >nul

echo Abrindo no navegador...
start "" "http://127.0.0.1:5000"

echo.
echo Projeto iniciado. Feche a janela "YT/DL Backend" para encerrar o servidor.
endlocal
