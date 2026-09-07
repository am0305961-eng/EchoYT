@echo off
chcp 65001 >nul
title EchoYT - Console Mode
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [!] Python was not found. Install it from https://www.python.org/downloads/
    echo     Tick "Add Python to PATH" during install.
    pause
    exit /b 1
)

echo Keeping console open so you can see errors.
echo If you see a traceback, screenshot it and share it.
echo.
python "%~dp0EchoYT WIN.py"
echo.
echo EchoYT closed. Press any key to exit.
pause >nul