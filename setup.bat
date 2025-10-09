@echo off
REM Setup script for Windows

echo ========================================
echo YouTube Playlist Downloader Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Checking Python installation...
python --version

REM Check if virtual environment exists
if exist "venv\" (
    echo [2/4] Virtual environment already exists
) else (
    echo [2/4] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

echo [3/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo [4/4] Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup complete!
echo ========================================
echo.
echo To use the application:
echo   1. Activate the virtual environment:
echo      venv\Scripts\activate.bat
echo.
echo   2. Run the GUI:
echo      python run_gui.py
echo.
echo   3. Or run the CLI:
echo      python run_cli.py --help
echo.
echo IMPORTANT: Don't forget to install FFmpeg!
echo   choco install ffmpeg
echo   Or download from: https://ffmpeg.org/download.html
echo.
pause
