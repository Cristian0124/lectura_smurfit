@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=%~dp0.runtime\python\python.exe"
if not exist "%PYTHON%" goto preparar
"%PYTHON%" -c "import flask" >nul 2>&1
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
start "Lectura de entorno - servidor" cmd /k ""%PYTHON%" app.py"
timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:5000
endlocal
