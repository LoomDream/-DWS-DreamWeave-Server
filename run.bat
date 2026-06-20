@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 (
        python -m venv .venv
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo Failed to create virtual environment.
    exit /b 1
)

echo Installing dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 exit /b 1

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo Starting Dreamweave Server...
".venv\Scripts\python.exe" main.py
