@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 start.py %*
) else (
    python start.py %*
)
if errorlevel 1 (
    echo See the startup guide in this folder. Install Python 3.12 and Codex CLI, then retry.
    pause
    exit /b 1
)

