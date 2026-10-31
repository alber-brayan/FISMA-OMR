@echo off
cd /d "%~dp0"
"%~dp0.venv\Scripts\python.exe" -X utf8 "%~dp0iniciar_fisma.py"
if errorlevel 1 pause
