#!/bin/bash
# Simple wrapper script to run the rlog downloader with virtual environment
# This file is automatically created if you use the setup_unix.sh script

cd "$(dirname "$0")"

if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
    python download_rlog_files.py "$@"
    deactivate
else
    # Fallback to system Python
    python download_rlog_files.py "$@"
fi
