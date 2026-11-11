@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

rem Prefer the active virtual environment (for example, the repository .venv).
if defined VIRTUAL_ENV (
    set "PYTHON=%VIRTUAL_ENV%\Scripts\python.exe"
    if exist "!PYTHON!" (
        "!PYTHON!" -c "from flask import Flask" >nul 2>&1
        if not errorlevel 1 goto iniciar
    )
)

rem Use the repository virtual environment when this script is started directly.
set "PYTHON=%~dp0..\.venv\Scripts\python.exe"
if exist "!PYTHON!" (
    "!PYTHON!" -c "from flask import Flask" >nul 2>&1
    if not errorlevel 1 goto iniciar
)

rem Last resort: prepare the bundled local Python environment.
set "PYTHON=%~dp0.runtime\python\python.exe"
if not exist "%PYTHON%" goto preparar
"!PYTHON!" -c "from flask import Flask" >nul 2>&1
if errorlevel 1 goto preparar
goto iniciar

:preparar
echo Preparando Python y Flask. Esto solo se hace la primera vez...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0preparar.ps1"
if errorlevel 1 (
    echo No se pudo preparar el entorno. Revisa la conexion a Internet y vuelve a intentarlo.
    pause
    exit /b 1
)

:iniciar
start "Radar de entorno - servidor" cmd /k ""%PYTHON%" app.py"
if defined FIRECRAWL_API_KEY (
    powershell -NoProfile -Command "Start-Process -FilePath '%PYTHON%' -ArgumentList 'worker_local.py' -WorkingDirectory '%~dp0' -WindowStyle Hidden -RedirectStandardOutput (Join-Path $env:TEMP 'radar-cafetero-worker.out.log') -RedirectStandardError (Join-Path $env:TEMP 'radar-cafetero-worker.err.log')"
) else (
    echo FIRECRAWL_API_KEY no esta configurada; el worker local no iniciara.
)
timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:5000
endlocal
