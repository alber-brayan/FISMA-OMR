@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto install
where py >nul 2>&1
if errorlevel 1 (
    python -m venv .venv
) else (
    py -3 -m venv .venv
)
if errorlevel 1 goto fail
:install
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto fail
if not exist "settings_config.json" copy "settings_config.example.json" "settings_config.json" >nul
echo.
echo Preparacion completa. Ejecute IniciarFISMA.bat.
pause
exit /b 0
:fail
echo.
echo No se completo la preparacion. Revise Python, la conexion y el mensaje anterior.
pause
exit /b 1
