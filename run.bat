@echo off
REM Launches Kinder Type (Windows). Runs the installer automatically on
REM first use if the virtual environment hasn't been set up yet.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo No .venv found -- running the installer first...
    python install.py
    if errorlevel 1 exit /b 1
)

".venv\Scripts\python.exe" game.py
