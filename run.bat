@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "VENV_PY=.venv\Scripts\python.exe"
set "PYTHON_CMD="
set "HOST=127.0.0.1"
set "PORT=7777"
set "TMP=%CD%\.tmp"
set "TEMP=%CD%\.tmp"
set "PIP_CACHE_DIR=%CD%\.pip-cache"
if not exist "%TMP%" mkdir "%TMP%"

if not defined DREAMWEAVE_SERVER_SECRET set "DREAMWEAVE_SERVER_SECRET=change-me-dreamweave-server-secret"
if not defined DREAMWEAVE_DEVELOPER_SECRET set "DREAMWEAVE_DEVELOPER_SECRET=change-me-dreamweave-developer-secret"
if not defined DREAMWEAVE_ADMIN_TOKEN set "DREAMWEAVE_ADMIN_TOKEN=change-me-dreamweave-admin-token"

call :find_python
if errorlevel 1 exit /b 1

if "%SKIP_INSTALL%"=="1" (
    echo SKIP_INSTALL=1, using system Python.
    set "VENV_PY=%PYTHON_CMD%"
    goto start_server
)

if not exist "%VENV_PY%" (
    echo Creating virtual environment...
    call :create_venv
    if errorlevel 1 exit /b 1
)

if not exist "%VENV_PY%" (
    echo Failed to create virtual environment.
    exit /b 1
)

echo Installing dependencies...
"%VENV_PY%" -m pip --version >nul 2>nul
if errorlevel 1 (
    echo Bootstrapping pip...
    "%VENV_PY%" -m ensurepip --upgrade
)

"%VENV_PY%" -m pip --version >nul 2>nul
if errorlevel 1 (
    echo pip is unavailable after bootstrap. Recreating virtual environment...
    call :recreate_venv
    if errorlevel 1 exit /b 1
)

"%VENV_PY%" -m pip --version >nul 2>nul
if errorlevel 1 (
    echo pip is still unavailable in the virtual environment.
    echo Free disk space or run with SKIP_INSTALL=1 if dependencies are already installed globally.
    exit /b 1
)

"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 exit /b 1

"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

:start_server
echo.
echo Starting Dreamweave Server
echo API:   http://%HOST%:%PORT%/docs
echo Admin: http://%HOST%:%PORT%/admin
echo Admin token: %DREAMWEAVE_ADMIN_TOKEN%
echo.

"%VENV_PY%" main.py

exit /b %errorlevel%

:find_python
where py >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
    exit /b 0
)

where python >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    exit /b 0
)

echo Python 3.11+ is required but was not found in PATH.
exit /b 1

:create_venv
%PYTHON_CMD% -m venv .venv
if errorlevel 1 (
    echo Failed to create virtual environment with: %PYTHON_CMD% -m venv .venv
    echo If disk space is limited, free space or run with SKIP_INSTALL=1 after installing requirements globally.
    exit /b 1
)
exit /b 0

:recreate_venv
if exist .venv rmdir /s /q .venv
if exist .venv (
    echo Failed to remove broken virtual environment.
    exit /b 1
)
call :create_venv
if errorlevel 1 exit /b 1
"%VENV_PY%" -m pip --version >nul 2>nul
if errorlevel 1 (
    echo pip is still unavailable in the recreated virtual environment.
    echo Free disk space or run with SKIP_INSTALL=1 if dependencies are already installed globally.
    exit /b 1
)
exit /b 0
