@echo off
REM ───────────────────────────────────────────────────────
REM  Startup script for the Recipes web app (Windows)
REM  Ensures Python 3 exists, creates venv, installs deps,
REM  initialises the DB, creates directories, and runs app.
REM ───────────────────────────────────────────────────────

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ===============================
echo    Recipes Startup (Windows)
echo ===============================
echo.

REM ─── Find Python ────────────────────────────────────────
set "PYTHON="

where python3 >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=*" %%v in ('python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2^>nul') do set "PYVER=%%v"
    for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (
        if %%a geq 3 if %%b geq 10 (
            set "PYTHON=python3"
        )
    )
)

if not defined PYTHON (
    where python >nul 2>&1
    if %errorlevel%==0 (
        for /f "tokens=*" %%v in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2^>nul') do set "PYVER=%%v"
        for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (
            if %%a geq 3 if %%b geq 10 (
                set "PYTHON=python"
            )
        )
    )
)

if not defined PYTHON (
    echo [!] Python 3.10+ not found. Attempting to install...

    where winget >nul 2>&1
    if %errorlevel%==0 (
        echo [*] Installing Python via winget...
        winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    ) else (
        where choco >nul 2>&1
        if %errorlevel%==0 (
            echo [*] Installing Python via Chocolatey...
            choco install python3 -y
        ) else (
            echo [X] No package manager found.
            echo     Install Python 3 from https://www.python.org/downloads/
            echo     Make sure to check "Add Python to PATH" during installation.
            pause
            exit /b 1
        )
    )

    REM Refresh PATH after install
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"

    where python >nul 2>&1
    if %errorlevel%==0 (
        set "PYTHON=python"
    ) else (
        echo [X] Python installation may have succeeded but is not in PATH.
        echo     Restart your terminal and run this script again.
        pause
        exit /b 1
    )
)

echo [OK] Found %PYTHON% (%PYVER%)

REM ─── Virtual environment ────────────────────────────────
if not exist "venv" (
    echo [*] Creating virtual environment...
    %PYTHON% -m venv venv
) else (
    echo [OK] Virtual environment already exists.
)

REM ─── Install dependencies ──────────────────────────────
echo [*] Installing / updating dependencies...
venv\Scripts\pip.exe install --quiet --upgrade pip
venv\Scripts\pip.exe install --quiet -r requirements.txt
echo [OK] Dependencies installed.

REM ─── Required directories ──────────────────────────────
if not exist "static\uploads" (
    mkdir "static\uploads"
    echo [OK] Created static\uploads
)
if not exist "static\videos" (
    mkdir "static\videos"
    echo [OK] Created static\videos
)
if not exist "instance" (
    mkdir "instance"
    echo [OK] Created instance
)

REM ─── Database ──────────────────────────────────────────
if not exist "instance\recipes.db" (
    echo [*] Initialising database...
    venv\Scripts\python.exe init_db.py
) else (
    echo [OK] Database already exists.
)

REM ─── Run ────────────────────────────────────────────────
echo.
echo [OK] Starting the app on http://localhost:5000 ...
echo.
venv\Scripts\python.exe app.py
