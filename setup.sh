#!/bin/bash

# Setup script for Linux/macOS

echo "========================================"
echo "YouTube Playlist Downloader Setup"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "[1/4] Checking Python installation..."
python3 --version

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "[2/4] Virtual environment already exists"
else
    echo "[2/4] Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment"
        exit 1
    fi
fi

echo "[3/4] Activating virtual environment..."
source venv/bin/activate

echo "[4/4] Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

echo ""
echo "========================================"
echo "Setup complete!"
echo "========================================"
echo ""
echo "To use the application:"
echo "  1. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Run the GUI:"
echo "     python run_gui.py"
echo ""
echo "  3. Or run the CLI:"
echo "     python run_cli.py --help"
echo ""
echo "IMPORTANT: Don't forget to install FFmpeg!"
echo "  Ubuntu/Debian: sudo apt install ffmpeg"
echo "  Fedora:        sudo dnf install ffmpeg"
echo "  macOS:         brew install ffmpeg"
echo ""
