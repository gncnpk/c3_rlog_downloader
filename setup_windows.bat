@echo off
echo Comma Route Log Downloader - Windows Setup
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo Python found!
python --version

REM Check if pip is available
pip --version >nul 2>&1
if errorlevel 1 (
    echo Error: pip is not available
    echo Please reinstall Python with pip included
    pause
    exit /b 1
)

echo Installing Python dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Setup completed successfully!
echo.
echo Optional: Install additional tools for better performance:
echo - Git for Windows (includes rsync): https://git-scm.com/download/win
echo - zstd for better compression: https://github.com/facebook/zstd/releases
echo.
echo You can now run: python download_rlog_files.py
echo.
pause
