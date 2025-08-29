@echo off
echo RClone Google Drive Upload Setup for Windows
echo ============================================
echo.

echo Checking if rclone is installed...
rclone version >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ rclone is already installed
    rclone version | findstr "rclone"
) else (
    echo ❌ rclone not found. Installing via winget...
    winget install Rclone.Rclone
    if %errorlevel% == 0 (
        echo ✅ rclone installed successfully
    ) else (
        echo ❌ winget installation failed. Please install manually:
        echo    1. Download from: https://rclone.org/downloads/
        echo    2. Or use chocolatey: choco install rclone
        echo    3. Add rclone to your PATH
        pause
        exit /b 1
    )
)

echo.
echo Checking rclone configuration...
rclone listremotes | findstr "gdrive:" >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ Google Drive remote 'gdrive' is already configured
) else (
    echo ❌ Google Drive remote not configured
    echo.
    echo To configure rclone for Google Drive:
    echo 1. Run: rclone config
    echo 2. Choose 'n' for new remote
    echo 3. Name it 'gdrive'
    echo 4. Choose 'drive' for Google Drive
    echo 5. Follow the authentication prompts
    echo.
    echo Would you like to configure it now? (y/n)
    set /p configure="Enter choice: "
    if /i "%configure%"=="y" (
        rclone config
    )
)

echo.
echo Setup complete!
echo.
echo To upload your rlogs:
echo   python upload_to_google_drive_rclone.py
echo.
echo Features:
echo - Automatically splits device folders to stay under 2GB
echo - Skips files already uploaded
echo - Uses parallel transfers for speed
echo - Shows progress and statistics
echo.
pause
