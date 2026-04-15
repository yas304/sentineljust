@echo off
title Sentinel Core - AI Contract Intelligence
color 0B

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║                                                          ║
echo  ║   ███████╗███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗     ║
echo  ║   ██╔════╝██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║     ║
echo  ║   ███████╗█████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║     ║
echo  ║   ╚════██║██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║     ║
echo  ║   ███████║███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗║
echo  ║   ╚══════╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝║
echo  ║                                                          ║
echo  ║            AI Contract Intelligence Platform             ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0backend"

:: Check if virtual environment exists
if not exist "venv" (
    echo  [*] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo  [ERROR] Failed to create virtual environment. Make sure Python 3.12+ is installed.
        pause
        exit /b 1
    )
)

:: Activate virtual environment
echo  [*] Activating virtual environment...
call venv\Scripts\activate.bat

:: Check if dependencies are installed
if not exist "venv\Lib\site-packages\fastapi" (
    echo  [*] Installing dependencies (first run)...
    pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo  [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    
    echo  [*] Downloading spaCy model...
    python -m spacy download en_core_web_sm --quiet
)

:: Create required directories
if not exist "uploads" mkdir uploads
if not exist "cache" mkdir cache

echo.
echo  ╭──────────────────────────────────────────────────────────╮
echo  │  Server starting at: http://localhost:8000              │
echo  │  Press Ctrl+C to stop the server                        │
echo  ╰──────────────────────────────────────────────────────────╯
echo.

:: Auto-open browser after 2 seconds
start /b cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8000"

:: Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
