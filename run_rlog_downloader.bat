@echo off
REM Simple wrapper script to run the rlog downloader with virtual environment
REM This file is automatically created if you use the setup_windows.bat script

cd /d "%~dp0"

if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
    python download_rlog_files.py %*
    call venv\Scripts\deactivate.bat
) else (
    REM Fallback to system Python
    python download_rlog_files.py %*
)

pause
