#!/bin/bash
# Linux/macOS launcher for CLI

if [ ! -f "venv/bin/activate" ]; then
    echo "Virtual environment not found!"
    echo "Please run ./setup.sh first"
    exit 1
fi

source venv/bin/activate
python run_cli.py "$@"
