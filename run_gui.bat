@echo off
REM Windows launcher for GUI

if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python run_gui.py
