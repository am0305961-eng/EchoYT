@echo off
chcp 65001 >nul
setlocal

title EchoYT - Setup & Launcher
cd /d "%~dp0"

echo.
echo ==========================================
echo        EchoYT  YouTube ^> Drive Music
echo ==========================================
echo.

REM ---------------- Check Python ----------------
where python >nul 2>nul
if errorlevel 1 (
    echo [!] Python was not found!
    echo.
    echo You need Python installed to run EchoYT.
    echo.
    echo   1. Download Python from:  https://www.python.org/downloads/
    echo   2. During install, TICK the box:  "Add Python to PATH"
    echo   3. Close this window and double-click the launcher again.
    echo.
    pause
    exit /b 1
)

REM ---------------- Install Python libraries (first run) ----------------
echo [1/2] Checking required libraries...  (this only downloads on first run)
python -m pip install --disable-pip-version-check -q -U requests google-auth google-auth-oauthlib google-api-python-client yt-dlp
if errorlevel 1 (
    echo [!] Failed to install libraries. Check your internet connection.
    pause
    exit /b 1
)

REM ---------------- Launch the app (no console) ----------------
echo [2/2] Starting EchoYT...
echo.

where pythonw >nul 2>nul
if errorlevel 1 (
    python "%~dp0EchoYT WIN.py"
) else (
    start "" pythonw "%~dp0EchoYT WIN.py"
)

endlocal