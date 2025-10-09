@echo off
REM Windows launcher for CLI

if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found!
    echo Please run setup.bat first
    exit /b 1
)

call venv\Scripts\activate.bat
python run_cli.py %*
