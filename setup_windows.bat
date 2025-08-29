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
    echo Warning: Standard pip install failed. Trying with virtual environment...
    
    REM Create virtual environment
    python -m venv venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment
        echo Make sure you have Python installed with venv support
        pause
        exit /b 1
    )
    
    REM Activate virtual environment and install dependencies
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    
    if errorlevel 1 (
        echo Error: Failed to install dependencies in virtual environment
        pause
        exit /b 1
    )
    
    REM Create wrapper script
    echo @echo off > run_rlog_downloader.bat
    echo REM Simple wrapper script to run the rlog downloader with virtual environment >> run_rlog_downloader.bat
    echo cd /d "%%~dp0" >> run_rlog_downloader.bat
    echo if exist venv\Scripts\activate.bat ^( >> run_rlog_downloader.bat
    echo     call venv\Scripts\activate.bat >> run_rlog_downloader.bat
    echo     python download_rlog_files.py %%* >> run_rlog_downloader.bat
    echo     call venv\Scripts\deactivate.bat >> run_rlog_downloader.bat
    echo ^) else ^( >> run_rlog_downloader.bat
    echo     python download_rlog_files.py %%* >> run_rlog_downloader.bat
    echo ^) >> run_rlog_downloader.bat
    
    echo.
    echo ^✓ Dependencies installed successfully in virtual environment!
    echo   Created wrapper script 'run_rlog_downloader.bat'
    echo   To run the script:
    echo     run_rlog_downloader.bat
    echo   Or manually:
    echo     venv\Scripts\activate.bat
    echo     python download_rlog_files.py
    echo     venv\Scripts\deactivate.bat
) else (
    echo.
    echo ^✓ Dependencies installed successfully!
)

echo.
echo Setup completed successfully!
if exist venv\Scripts\activate.bat (
    echo Virtual environment created. To run the script:
    echo   run_rlog_downloader.bat  ^(uses wrapper script^)
    echo Or manually:
    echo   venv\Scripts\activate.bat ^&^& python download_rlog_files.py ^&^& venv\Scripts\deactivate.bat
) else (
    echo You can now run: python download_rlog_files.py
)
echo.
echo Optional: Install additional tools for better performance:
echo - Git for Windows (includes rsync): https://git-scm.com/download/win
echo - zstd for better compression: https://github.com/facebook/zstd/releases
echo.
echo You can now run: python download_rlog_files.py
echo.
pause
