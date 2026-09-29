@echo off
title KrishiSmriti
cd /d "%~dp0"
set PYTHONUTF8=1

echo ============================================
echo   KrishiSmriti - starting up
echo ============================================

where python >nul 2>nul
if errorlevel 1 (
    echo [X] Python not found. Install Python 3.10+ from python.org
    echo     and tick "Add Python to PATH" during install.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 ( echo [X] Could not create venv & pause & exit /b 1 )
)

call ".venv\Scripts\activate.bat"

echo [2/3] Installing packages (first run takes a minute)...
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q
if errorlevel 1 ( echo [X] Package install failed. Check your internet. & pause & exit /b 1 )

if not exist ".env" copy ".env.example" ".env" >nul

echo.
echo  Works with NO API key:
echo    - Voice input : Chrome or Edge microphone (free)
echo    - Voice output: free Google voice (needs internet)
echo    - Answers     : from the farm memory + built-in pest guide
echo  Optional: add a free GROQ_API_KEY in the .env file for full AI
echo            answers, photo diagnosis and bill scanning.
echo.
echo [3/3] Opening http://localhost:8000  (keep this window open)
echo       Press Ctrl+C here to stop.
echo.
start "" /b cmd /c "timeout /t 5 >nul & start http://localhost:8000"
python -m uvicorn main:app --host 127.0.0.1 --port 8000

pause
